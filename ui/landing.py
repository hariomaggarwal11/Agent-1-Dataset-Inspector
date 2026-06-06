"""Landing page with file upload and sidebar controls."""

import os
import tempfile
from pathlib import Path

import streamlit as st

from core.format_router import route_file


def render_landing():
    """Render the landing / upload page."""
    # Sidebar
    with st.sidebar:
        st.title("\U0001f9e0 NeuroInspect")
        st.caption("Agent 1 \u00b7 Dataset Inspector")
        st.divider()

        uploaded_file = st.file_uploader(
            "Upload Dataset File",
            type=[
                # EEG
                "mat", "edf", "bdf", "gdf", "set", "fdt",
                "vhdr", "vmrk", "eeg", "fif", "cnt", "mff",
                "h5", "hdf5", "xdf",
                # ECG
                "dat", "hea", "atr", "qrs", "scp", "dcm",
                "xml", "csv", "npy", "npz", "json",
            ],
            help="Upload a single file. For multi-file formats (e.g., .dat+.hea), "
                 "upload the header file (.hea) and ensure .dat is in the same temp path."
        )

        st.divider()

        modality = st.radio(
            "Signal Modality",
            options=["\U0001f916 Auto-Detect", "\U0001f9e0 EEG", "\U0001fac0 ECG"],
            index=0,
        )

        st.divider()

        depth = st.selectbox(
            "Analysis Depth",
            options=["Quick Scan (< 10 s)", "Full Report (~1 min)", "Research Mode (~3 min)"],
            index=1,
        )

        researcher_name = st.text_input(
            "Your Name (for report)",
            placeholder="e.g., Hariom Sharma",
        )
        if researcher_name:
            st.session_state["researcher_name"] = researcher_name

        st.divider()
        run_btn = st.button("\U0001f52c Inspect Dataset", type="primary", use_container_width=True)

        st.divider()
        st.caption("NeuroInspect v1.0 \u00b7 Powered by MNE-Python + WFDB")
        st.caption("Part of the BioMed Research Agent Suite")

    # Main panel
    st.markdown("## \U0001f9e0 NeuroInspect")
    st.markdown("#### Agent 1: Dataset Inspector")
    st.markdown("---")

    if uploaded_file is None:
        # Show welcome / instructions
        st.markdown("""
        ### Drop your EEG or ECG dataset file here, or use the sidebar to upload.

        **Supported Formats:**

        | Modality | Extensions |
        |----------|-----------|
        | **EEG** | `.mat` `.edf` `.edf+` `.bdf` `.gdf` `.set` `.fdt` `.vhdr` `.fif` `.cnt` `.xdf` `.h5` |
        | **ECG** | `.dat` `.hea` `.atr` `.edf` `.scp` `.dcm` `.xml` `.mat` `.csv` `.h5` `.npy` `.npz` |

        **Analysis Modes:**
        - **Quick Scan**: Metadata + channel info only (~5 seconds)
        - **Full Report**: All inspection steps (~30-60 seconds)
        - **Research Mode**: Full Report + artifact maps + band PSD + correlation matrix + export
        """)

        st.info("\U0001f4a1 **Tip:** For multi-file formats (e.g., WFDB .dat+.hea), upload the header file.")
    else:
        # File is uploaded
        st.success(f"\u2705 File uploaded: **{uploaded_file.name}** ({uploaded_file.size / 1024 / 1024:.1f} MB)")

        if run_btn:
            _run_inspection(uploaded_file, modality, depth)


def _run_inspection(uploaded_file, modality_selection, depth_selection):
    """Run the inspection pipeline."""
    # Parse modality
    if "Auto-Detect" in modality_selection:
        force_modality = "auto"
    elif "EEG" in modality_selection:
        force_modality = "EEG"
    else:
        force_modality = "ECG"

    # Parse depth
    if "Quick" in depth_selection:
        depth = "quick"
    elif "Research" in depth_selection:
        depth = "research"
    else:
        depth = "full"

    # Save to temp file
    suffix = Path(uploaded_file.name).suffix
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = tmp.name

    try:
        with st.status("\U0001f50d Inspecting your dataset...", expanded=True) as status:
            st.write("\U0001f4c2 Detecting file format...")
            route = route_file(tmp_path, force_modality)

            if route["modality"] is None:
                st.error(f"Could not determine file type: {route['note']}")
                status.update(label="\u274c Inspection failed", state="error")
                return

            if route["confidence"] < 0.6:
                st.warning(f"\u26a0\ufe0f Low confidence detection: {route['note']}")

            st.write(f"Detected: **{route['modality']}** ({route['note']})")

            if route["modality"] == "EEG":
                st.write("\U0001f4d6 Loading EEG data...")
                from core.eeg.report_builder import build_eeg_report
                report = build_eeg_report(tmp_path, route["format"], depth)
            else:
                st.write("\U0001f4d6 Loading ECG data...")
                from core.ecg.report_builder import build_ecg_report
                report = build_ecg_report(tmp_path, route["format"], depth)

            if not report.get("success", False):
                st.error(f"\u274c Error: {report.get('message', 'Unknown error')}")
                suggestion = report.get("suggestion", "")
                if suggestion:
                    st.info(f"\U0001f4a1 Suggestion: {suggestion}")
                status.update(label="\u274c Inspection failed", state="error")
                return

            st.write("\u2705 Inspection complete!")
            status.update(label="\u2705 Inspection complete!", state="complete")

        # Store results in session state
        st.session_state["inspection_result"] = report
        st.session_state["current_file"] = uploaded_file.name
        st.session_state["modality"] = route["modality"]
        st.rerun()

    finally:
        # Clean up temp file
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
