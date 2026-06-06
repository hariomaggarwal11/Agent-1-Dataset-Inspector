"""ECG Inspection Dashboard - 8-tab results view."""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ui.components import (
    render_metric_card, render_quality_gauge, render_artifact_table,
    render_summary_card,
)
from core.shared.exporter import export_pdf, export_docx, export_json


def render_ecg_dashboard(report):
    """Render the full ECG inspection dashboard."""
    st.title("\U0001fac0 ECG Inspection Results")

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
        "\U0001fac0 Leads",
        "\U0001f4cc Annotations",
        "\U0001f493 Signal Quality",
        "\U0001f50d Artifacts",
        "\U0001f4c8 R-Peak Stats",
        "\U0001f4ca Quality Score",
        "\U0001f4c4 Export",
    ])

    with tabs[0]:
        _render_overview(report)
    with tabs[1]:
        _render_leads(report)
    with tabs[2]:
        _render_annotations(report)
    with tabs[3]:
        _render_signal_quality(report)
    with tabs[4]:
        _render_artifacts(report)
    with tabs[5]:
        _render_rpeaks(report)
    with tabs[6]:
        _render_quality(report)
    with tabs[7]:
        _render_export(report)


def _render_overview(report):
    """Tab 1: Overview."""
    metadata = report.get("metadata", {})

    cols = st.columns(4)
    with cols[0]:
        fs = metadata.get("Sampling Frequency", "N/A")
        status = "pass" if "Hz" in str(fs) else None
        render_metric_card("Sampling Frequency", fs, status)
    with cols[1]:
        leads = metadata.get("Number of Leads", "N/A")
        status = "pass" if "12" in str(leads) or "Standard" in str(leads) else None
        render_metric_card("Leads", leads, status)
    with cols[2]:
        render_metric_card("Duration", metadata.get("Duration", "N/A"))
    with cols[3]:
        known = report.get("known_dataset")
        if known:
            render_metric_card("Dataset", known["name"], "pass")
        else:
            render_metric_card("Dataset", "Unknown")

    st.markdown("---")

    st.subheader("Dataset Metadata")
    meta_df = pd.DataFrame([(k, str(v)) for k, v in metadata.items()], columns=["Field", "Value"])
    st.dataframe(meta_df, width="stretch", hide_index=True)

    known = report.get("known_dataset")
    if known:
        st.info(f"""
        \U0001f9ea **Known Dataset Detected: {known['name']}**
        - {known.get('description', '')}
        - Leads: {known.get('n_leads', 'N/A')}
        - Sampling Rate: {known.get('fs', 'N/A')} Hz
        """)


def _render_leads(report):
    """Tab 2: Lead information and signal preview."""
    lead_info = report.get("lead_info")
    if lead_info is None:
        st.warning("Lead information not available.")
        return

    st.subheader("\U0001fac0 Lead Information")
    st.dataframe(lead_info, width="stretch", hide_index=True)

    # Multi-lead signal preview
    ecg_data = report.get("ecg_data")
    if ecg_data is not None:
        st.markdown("### Signal Preview (first 10 seconds)")
        signals = ecg_data["signals"]
        fs = ecg_data["fs"]
        lead_names = ecg_data["lead_names"]
        duration = min(10.0, ecg_data["duration_s"])
        n_samples = int(duration * fs)

        fig = go.Figure()
        n_leads = min(len(lead_names), 12)

        for i in range(n_leads):
            sig = signals[i][:n_samples]
            times = np.arange(len(sig)) / fs
            offset = -i * np.std(sig) * 4
            fig.add_trace(go.Scatter(
                x=times, y=sig + offset,
                mode="lines", name=lead_names[i],
                line=dict(width=0.8),
            ))

        fig.update_layout(
            title="Multi-Lead ECG Preview",
            xaxis_title="Time (s)",
            yaxis_title="Amplitude (mV, offset)",
            height=400 + n_leads * 30,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(17,24,39,1)",
            font=dict(color="#f1f5f9"),
        )
        st.plotly_chart(fig, width="stretch")


def _render_annotations(report):
    """Tab 3: Beat annotations."""
    ann = report.get("annotations", {})

    if not ann.get("has_annotations"):
        st.warning("No annotations found in this recording.")
        st.info("\U0001f4a1 Annotations are typically in a companion file (.atr, .qrs)")
        return

    st.subheader("\U0001f4cc Beat Annotations")

    # Beat summary
    beat_summary = ann.get("beat_summary")
    if beat_summary is not None:
        st.markdown("### Beat Type Summary")
        st.dataframe(beat_summary, width="stretch", hide_index=True)
        st.caption(f"Total annotations: {ann.get('total_annotations', 0)}")

    # Annotation table (first 100)
    annotation_df = ann.get("annotation_df")
    if annotation_df is not None:
        with st.expander("Detailed Annotation Table (first 100)"):
            st.dataframe(annotation_df.head(100), width="stretch", hide_index=True)


def _render_signal_quality(report):
    """Tab 4: Per-lead signal quality."""
    quality_df = report.get("signal_quality")

    if quality_df is None:
        st.warning("Signal quality analysis not available.")
        return

    st.subheader("\U0001f493 Per-Lead Signal Quality")
    st.dataframe(quality_df, width="stretch", hide_index=True)

    with st.expander("\u2139\ufe0f Quality Index Interpretation"):
        st.markdown("""
        | Range | Interpretation | Meaning |
        |-------|---------------|---------|
        | 0.8 - 1.0 | \U0001f7e2 Excellent | Clean signal, suitable for analysis |
        | 0.6 - 0.8 | \U0001f7e1 Acceptable | Minor noise, may need filtering |
        | < 0.6 | \U0001f534 Poor | Significant noise, preprocessing required |
        """)


def _render_artifacts(report):
    """Tab 5: Artifact detection."""
    artifacts = report.get("artifacts", {})

    if not artifacts:
        st.warning("Artifact analysis not available.")
        return

    st.subheader("\U0001f50d ECG Artifact Scan Results")
    render_artifact_table(artifacts)


def _render_rpeaks(report):
    """Tab 6: R-peak statistics and HRV."""
    rpeaks = report.get("rpeaks", {})

    if not rpeaks:
        st.warning("R-peak analysis not available.")
        return

    st.subheader("\U0001f4c8 R-Peak & Heart Rate Analysis")

    hr_stats = rpeaks.get("hr_stats", {})
    lead_used = rpeaks.get("lead_used", "Unknown")

    st.caption(f"Analysis performed on: {lead_used}")

    # HR metrics
    cols = st.columns(4)
    with cols[0]:
        mean_hr = hr_stats.get("mean_hr", 0)
        classification = hr_stats.get("classification", "")
        status = "pass" if classification == "Normal Sinus Rhythm" else "warn"
        render_metric_card("Mean HR", f"{mean_hr} BPM", status)
    with cols[1]:
        render_metric_card("Classification", classification)
    with cols[2]:
        render_metric_card("Min HR", f"{hr_stats.get('min_hr', 0)} BPM")
    with cols[3]:
        render_metric_card("Max HR", f"{hr_stats.get('max_hr', 0)} BPM")

    # HRV metrics
    hrv = rpeaks.get("hrv_metrics", {})
    if hrv:
        st.markdown("---")
        st.markdown("### HRV Metrics")
        hrv_df = pd.DataFrame([
            {"Metric": k, "Value": v,
             "Normal Range": _get_hrv_normal(k)}
            for k, v in hrv.items()
        ])
        st.dataframe(hrv_df, width="stretch", hide_index=True)

    # RR Interval plot
    rr = rpeaks.get("rr_intervals")
    if rr is not None and len(rr) > 1:
        st.markdown("---")
        st.markdown("### RR Interval Tachogram")

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            y=rr, mode="lines+markers",
            marker=dict(size=3),
            line=dict(width=1, color="#00d4ff"),
        ))
        fig.update_layout(
            xaxis_title="Beat Number",
            yaxis_title="RR Interval (ms)",
            height=300,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(17,24,39,1)",
            font=dict(color="#f1f5f9"),
        )
        st.plotly_chart(fig, width="stretch")

        # Poincare plot
        if len(rr) > 2:
            st.markdown("### Poincar\u00e9 Plot")
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(
                x=rr[:-1], y=rr[1:],
                mode="markers",
                marker=dict(size=4, color="#ff4d6d", opacity=0.6),
            ))
            fig2.add_trace(go.Scatter(
                x=[min(rr), max(rr)], y=[min(rr), max(rr)],
                mode="lines", line=dict(dash="dash", color="#64748b"),
                showlegend=False,
            ))
            fig2.update_layout(
                xaxis_title="RR[n] (ms)",
                yaxis_title="RR[n+1] (ms)",
                height=350,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(17,24,39,1)",
                font=dict(color="#f1f5f9"),
            )
            st.plotly_chart(fig2, width="stretch")


def _get_hrv_normal(metric_name):
    """Get normal range for HRV metric."""
    ranges = {
        "SDNN (ms)": "> 50 ms",
        "RMSSD (ms)": "20-80 ms",
        "pNN50 (%)": "> 5%",
        "Mean RR (ms)": "600-1000 ms",
    }
    return ranges.get(metric_name, "N/A")


def _render_quality(report):
    """Tab 7: Quality score."""
    quality = report.get("quality_score")

    if quality is None:
        st.warning("Quality score not available.")
        return

    st.subheader("\U0001f4ca Data Quality Score")

    fig = render_quality_gauge(quality["score"])
    st.plotly_chart(fig, width="stretch")

    st.markdown("### Score Breakdown")
    for item, pts in quality["breakdown"]:
        st.markdown(f"- {item} **({pts})**")


def _render_export(report):
    """Tab 8: Export options."""
    st.subheader("\U0001f4c4 Export Report")

    researcher = st.session_state.get("researcher_name", "")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("### \U0001f4c4 PDF Report")
        if st.button("\U0001f4e5 Generate PDF", key="ecg_pdf_btn"):
            with st.spinner("Generating PDF..."):
                try:
                    pdf_bytes = export_pdf(report, researcher)
                    st.download_button(
                        label="\u2b07\ufe0f Download PDF",
                        data=pdf_bytes,
                        file_name="neuroinspect_ecg_report.pdf",
                        mime="application/pdf",
                        key="ecg_pdf_download",
                    )
                except Exception as e:
                    st.error(f"PDF generation failed: {e}")

    with col2:
        st.markdown("### \U0001f4dd DOCX Report")
        if st.button("\U0001f4e5 Generate DOCX", key="ecg_docx_btn"):
            with st.spinner("Generating DOCX..."):
                try:
                    docx_bytes = export_docx(report, researcher)
                    st.download_button(
                        label="\u2b07\ufe0f Download DOCX",
                        data=docx_bytes,
                        file_name="neuroinspect_ecg_report.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        key="ecg_docx_download",
                    )
                except Exception as e:
                    st.error(f"DOCX generation failed: {e}")

    with col3:
        st.markdown("### \U0001f527 JSON Export")
        if st.button("\U0001f4e5 Generate JSON", key="ecg_json_btn"):
            with st.spinner("Generating JSON..."):
                try:
                    json_bytes = export_json(report)
                    st.download_button(
                        label="\u2b07\ufe0f Download JSON",
                        data=json_bytes,
                        file_name="neuroinspect_ecg_report.json",
                        mime="application/json",
                        key="ecg_json_download",
                    )
                except Exception as e:
                    st.error(f"JSON generation failed: {e}")
