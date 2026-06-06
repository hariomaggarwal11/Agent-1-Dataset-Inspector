"""EEG Inspection Dashboard - 8-tab results view."""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

from config import EEG_BANDS
from ui.components import (
    render_metric_card, render_quality_gauge, render_artifact_table,
    render_summary_card, render_status_badge,
)
from core.shared.exporter import export_pdf, export_docx, export_json


def render_eeg_dashboard(report):
    """Render the full EEG inspection dashboard."""
    st.title("\U0001f9e0 EEG Inspection Results")

    # Summary card
    metadata = report.get("metadata", {})
    filename = st.session_state.get("current_file", "Unknown")
    format_name = metadata.get("File Format", "Unknown")
    file_size = metadata.get("File Size", "Unknown")
    load_time = metadata.get("Load Time", "0 s")

    render_summary_card(filename, format_name, "pass", load_time, file_size)

    # Tabs
    tabs = st.tabs([
        "\U0001f4cb Overview",
        "\U0001f4e1 Channels",
        "\u23f1 Events",
        "\U0001f30a Frequency",
        "\U0001f50d Artifacts",
        "\U0001f5fa Topography",
        "\U0001f4ca Quality Score",
        "\U0001f4c4 Export",
    ])

    with tabs[0]:
        _render_overview(report)
    with tabs[1]:
        _render_channels(report)
    with tabs[2]:
        _render_events(report)
    with tabs[3]:
        _render_frequency(report)
    with tabs[4]:
        _render_artifacts(report)
    with tabs[5]:
        _render_topography(report)
    with tabs[6]:
        _render_quality(report)
    with tabs[7]:
        _render_export(report)


def _render_overview(report):
    """Tab 1: Overview with metrics and metadata."""
    metadata = report.get("metadata", {})

    # Metric row
    cols = st.columns(4)
    with cols[0]:
        fs = metadata.get("Sampling Frequency", "N/A")
        status = "pass" if "Hz" in str(fs) else None
        render_metric_card("Sampling Frequency", fs, status)
    with cols[1]:
        render_metric_card("Duration", metadata.get("Duration", "N/A"))
    with cols[2]:
        render_metric_card("Channels", metadata.get("Number of Channels", "N/A"))
    with cols[3]:
        known = report.get("known_dataset")
        if known:
            render_metric_card("Dataset", known["name"], "pass")
        else:
            render_metric_card("Dataset", "Unknown")

    st.markdown("---")

    # Metadata table
    st.subheader("Dataset Metadata")
    meta_df = pd.DataFrame(list(metadata.items()), columns=["Field", "Value"])
    st.dataframe(meta_df, use_container_width=True, hide_index=True)

    # Known dataset info
    known = report.get("known_dataset")
    if known:
        st.info(f"""
        \U0001f9ea **Known Dataset Detected: {known['name']}**
        - Device: {known.get('device', 'N/A')}
        - Channels: {known.get('channels', 'N/A')}
        - Sampling Rate: {known.get('fs', 'N/A')} Hz
        - Recommended Preprocessing: {known.get('preprocessing', 'N/A')}
        """)


def _render_channels(report):
    """Tab 2: Channel information and montage."""
    channel_info = report.get("channel_info")
    if channel_info is None:
        st.warning("Channel information not available.")
        return

    st.subheader("\U0001f4e1 Channel Information")
    st.dataframe(channel_info, use_container_width=True, hide_index=True)

    # Reference scheme
    ref = report.get("metadata", {}).get("Reference Scheme", "Unknown")
    st.markdown(f"""
    ---
    \U0001f517 **Reference Scheme Detected:** {ref}
    """)

    with st.expander("\u2139\ufe0f What does this mean for your analysis?"):
        st.markdown("""
        The reference scheme determines how EEG voltages are measured:
        - **Common Average Reference (CAR):** Each channel referenced to the mean of all channels
        - **Mastoid Reference:** Referenced to M1/M2 or A1/A2 electrodes behind the ears
        - **Linked Reference:** Referenced to a dedicated REF electrode

        Re-referencing may be needed depending on your analysis goals.
        """)


def _render_events(report):
    """Tab 3: Events and annotations."""
    events = report.get("events", {})

    if not events.get("has_events"):
        st.warning("No events or annotations found in this recording.")
        st.info("\U0001f4a1 If this is a continuous recording without markers, events may be in a separate file.")
        return

    st.subheader("\u23f1 Events Summary")

    summary_df = events.get("summary_df")
    if summary_df is not None:
        st.dataframe(summary_df, use_container_width=True, hide_index=True)

        # Timeline visualization
        events_array = events.get("events_array")
        event_id = events.get("event_id")
        if events_array is not None and event_id is not None:
            raw = report.get("raw")
            fs = raw.info["sfreq"] if raw else 1
            times = events_array[:, 0] / fs

            fig = go.Figure()
            id_to_label = {v: k for k, v in event_id.items()}
            for eid in event_id.values():
                mask = events_array[:, 2] == eid
                label = id_to_label.get(eid, str(eid))
                fig.add_trace(go.Scatter(
                    x=times[mask], y=[label] * mask.sum(),
                    mode="markers", name=label,
                    marker=dict(size=8),
                ))

            fig.update_layout(
                title="Event Timeline",
                xaxis_title="Time (s)",
                yaxis_title="Event Type",
                height=300,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(17,24,39,1)",
                font=dict(color="#f1f5f9"),
            )
            st.plotly_chart(fig, use_container_width=True)


def _render_frequency(report):
    """Tab 4: Frequency / spectral analysis."""
    spectral = report.get("spectral")

    if spectral is None:
        st.warning("Spectral analysis not available. Run Full Report or Research Mode.")
        return

    st.subheader("\U0001f30a Power Spectral Density")

    psds = spectral["psds"]
    freqs = spectral["freqs"]
    raw = report.get("raw")
    ch_names = raw.info["ch_names"] if raw else [f"Ch{i}" for i in range(len(psds))]

    # PSD plot
    fig = go.Figure()
    for i, ch_name in enumerate(ch_names[:16]):  # Limit to 16 channels for readability
        fig.add_trace(go.Scatter(
            x=freqs, y=psds[i],
            mode="lines", name=ch_name,
            visible="legendonly" if i > 5 else True,
        ))

    # Band boundary lines
    for band_name, (flo, fhi) in EEG_BANDS.items():
        fig.add_vline(x=flo, line_dash="dash", line_color="#64748b", opacity=0.5)
        fig.add_annotation(x=(flo + fhi) / 2, y=1, yref="paper",
                          text=band_name, showarrow=False, font=dict(size=10, color="#64748b"))

    fig.update_layout(
        title="Power Spectral Density (Welch)",
        xaxis_title="Frequency (Hz)",
        yaxis_title="Power (\u00b5V\u00b2/Hz)",
        yaxis_type="log",
        height=400,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(17,24,39,1)",
        font=dict(color="#f1f5f9"),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Band power table
    st.subheader("Relative Band Power (%)")
    band_powers = spectral["band_powers"]
    if band_powers is not None and len(band_powers) > 0:
        band_powers.index = ch_names[:len(band_powers)]
        band_powers.index.name = "Channel"
        st.dataframe(band_powers.style.background_gradient(cmap="YlOrRd", axis=1),
                     use_container_width=True)

    # FAA
    faa = report.get("faa", {})
    if faa.get("available"):
        st.markdown("---")
        st.subheader("Frontal Alpha Asymmetry (FAA)")
        faa_val = faa["faa_value"]
        interp = faa["interpretation"]
        st.markdown(f"**FAA = {faa_val:+.4f}** \u2192 {interp}")
        with st.expander("\u2139\ufe0f What is FAA?"):
            st.markdown("""
            Frontal Alpha Asymmetry (FAA) = ln(Right Alpha Power) - ln(Left Alpha Power)
            - **Positive FAA** \u2192 Approach motivation / higher valence
            - **Negative FAA** \u2192 Withdrawal motivation / lower valence

            FAA is a validated biomarker for emotional valence and MDD screening.
            """)


def _render_artifacts(report):
    """Tab 5: Artifact detection results."""
    artifacts = report.get("artifacts", {})

    if not artifacts:
        st.warning("Artifact analysis not available. Run Full Report or Research Mode.")
        return

    st.subheader("\U0001f50d Artifact Scan Results")
    render_artifact_table(artifacts)

    # Raw signal preview (placeholder)
    raw = report.get("raw")
    if raw is not None:
        with st.expander("Raw Signal Preview (first 5 seconds)"):
            try:
                duration = min(5.0, raw.times[-1])
                data = raw.get_data(tmax=duration)
                times = raw.times[raw.times <= duration]
                ch_names = raw.info["ch_names"]

                fig = go.Figure()
                n_ch = min(len(ch_names), 8)
                for i in range(n_ch):
                    offset = i * np.std(data[:n_ch]) * 3
                    fig.add_trace(go.Scatter(
                        x=times, y=data[i] + offset,
                        mode="lines", name=ch_names[i],
                        line=dict(width=0.8),
                    ))

                fig.update_layout(
                    title="Raw EEG Signal (stacked channels)",
                    xaxis_title="Time (s)",
                    yaxis_title="Amplitude (offset)",
                    height=400,
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(17,24,39,1)",
                    font=dict(color="#f1f5f9"),
                    showlegend=True,
                )
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.warning(f"Could not render signal preview: {e}")


def _render_topography(report):
    """Tab 6: Topographic maps."""
    channel_info = report.get("channel_info")

    if channel_info is None or not channel_info["Has Location"].any():
        st.warning("Topographic visualization requires channel location data. "
                   "No electrode positions found in this file.")
        st.info("\U0001f4a1 You can set a standard montage using MNE: "
                "`raw.set_montage('standard_1020')`")
        return

    st.subheader("\U0001f5fa Topographic Analysis")

    # Channel correlation matrix
    raw = report.get("raw")
    if raw is not None:
        st.markdown("### Channel Correlation Matrix")
        try:
            data = raw.get_data()
            if data.shape[1] > 10000:
                data = data[:, :10000]
            corr = np.corrcoef(data)
            ch_names = raw.info["ch_names"]

            fig = go.Figure(data=go.Heatmap(
                z=corr, x=ch_names, y=ch_names,
                colorscale="RdBu_r", zmin=-1, zmax=1,
            ))
            fig.update_layout(
                title="Channel Correlation Matrix",
                height=500,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(17,24,39,1)",
                font=dict(color="#f1f5f9"),
            )
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.warning(f"Could not compute correlation: {e}")


def _render_quality(report):
    """Tab 7: Quality score."""
    quality = report.get("quality_score")

    if quality is None:
        st.warning("Quality score not available. Run Full Report or Research Mode.")
        return

    st.subheader("\U0001f4ca Data Quality Score")

    # Gauge
    fig = render_quality_gauge(quality["score"])
    st.plotly_chart(fig, use_container_width=True)

    # Breakdown
    st.markdown("### Score Breakdown")
    for item, pts in quality["breakdown"]:
        st.markdown(f"- {item} **({pts})**")

    # Recommendations
    st.markdown("### \U0001f4a1 Recommendations")
    artifacts = report.get("artifacts", {})

    if artifacts.get("line_noise", {}).get("status") == "fail":
        st.warning("""
        **Line noise detected**
        - Recommended fix: Apply notch filter at 50/60 Hz before analysis.
        - MNE code: `raw.notch_filter(freqs=[50, 60], filter_length='auto')`
        """)

    if artifacts.get("flat_channels", {}).get("status") == "fail":
        channels = artifacts["flat_channels"].get("channels", [])
        st.warning(f"""
        **Flat channels detected**: {', '.join(channels)}
        - Recommended fix: Mark as bad and interpolate.
        - MNE code: `raw.info['bads'] = {channels}; raw.interpolate_bads()`
        """)

    if artifacts.get("noisy_channels", {}).get("status") == "warn":
        st.warning("""
        **Noisy channels detected**
        - Recommended fix: Inspect visually and consider ICA or interpolation.
        """)


def _render_export(report):
    """Tab 8: Export options."""
    st.subheader("\U0001f4c4 Export Report")

    researcher = st.session_state.get("researcher_name", "")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("### \U0001f4c4 PDF Report")
        st.caption("Publication-quality report with all metrics and plots")
        if st.button("\U0001f4e5 Generate PDF", key="pdf_btn"):
            with st.spinner("Generating PDF..."):
                try:
                    pdf_bytes = export_pdf(report, researcher)
                    st.download_button(
                        label="\u2b07\ufe0f Download PDF",
                        data=pdf_bytes,
                        file_name="neuroinspect_eeg_report.pdf",
                        mime="application/pdf",
                        key="pdf_download",
                    )
                except Exception as e:
                    st.error(f"PDF generation failed: {e}")

    with col2:
        st.markdown("### \U0001f4dd DOCX Report")
        st.caption("Editable Word format (A4, Times New Roman 12pt)")
        if st.button("\U0001f4e5 Generate DOCX", key="docx_btn"):
            with st.spinner("Generating DOCX..."):
                try:
                    docx_bytes = export_docx(report, researcher)
                    st.download_button(
                        label="\u2b07\ufe0f Download DOCX",
                        data=docx_bytes,
                        file_name="neuroinspect_eeg_report.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        key="docx_download",
                    )
                except Exception as e:
                    st.error(f"DOCX generation failed: {e}")

    with col3:
        st.markdown("### \U0001f527 JSON Export")
        st.caption("Machine-readable format for Agent 2 pipeline")
        if st.button("\U0001f4e5 Generate JSON", key="json_btn"):
            with st.spinner("Generating JSON..."):
                try:
                    json_bytes = export_json(report)
                    st.download_button(
                        label="\u2b07\ufe0f Download JSON",
                        data=json_bytes,
                        file_name="neuroinspect_eeg_report.json",
                        mime="application/json",
                        key="json_download",
                    )
                except Exception as e:
                    st.error(f"JSON generation failed: {e}")
