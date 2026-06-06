"""Landing page with file upload and sidebar controls."""

import os
import tempfile
import shutil
from pathlib import Path

import streamlit as st

from core.format_router import route_file

# Primary file extensions for multi-file formats.
# These are the files that contain metadata/headers and should be
# passed to the format router. Companion files are found automatically
# when co-located in the same directory.
_PRIMARY_EXTENSIONS = {
    # WFDB: .hea is the header (primary), .dat/.atr/.qrs/.ari are companions
    ".hea",
    # BrainVision: .vhdr is the header (primary), .eeg and .vmrk are companions
    ".vhdr",
    # EEGLAB: .set is the dataset (primary), .fdt is the companion data file
    ".set",
}

# Companion-only extensions (never primary on their own)
_COMPANION_EXTENSIONS = {
    ".dat", ".atr", ".qrs", ".ari",  # WFDB companions
    ".vmrk",                          # BrainVision marker file
    ".fdt",                           # EEGLAB float data
}


def _find_primary_file(file_paths):
    """Determine the primary file from a list of uploaded file paths.

    Priority:
    1. Files with a known primary extension (.hea, .vhdr, .set)
    2. If no primary extension found, pick the first non-companion file
    3. Fall back to the first file in the list

    Parameters
    ----------
    file_paths : list of str
        List of file paths saved to the temp directory.

    Returns
    -------
    str
        Path to the primary file to pass to the format router.
    """
    # Look for a known primary extension first
    for fp in file_paths:
        ext = Path(fp).suffix.lower()
        if ext in _PRIMARY_EXTENSIONS:
            return fp

    # No primary extension found; pick first non-companion file
    for fp in file_paths:
        ext = Path(fp).suffix.lower()
        if ext not in _COMPANION_EXTENSIONS:
            return fp

    # Fallback: return the first file
    return file_paths[0]


def render_landing():
    """Render the landing / upload page."""
    # Sidebar
    with st.sidebar:
        st.title("\U0001f9e0 NeuroInspect")
        st.caption("Agent 1 \u00b7 Dataset Inspector")
        st.divider()

        uploaded_files = st.file_uploader(
            "Upload Dataset Files",
            type=[
                # EEG
                "mat", "edf", "bdf", "gdf", "set", "fdt",
                "vhdr", "vmrk", "eeg", "fif", "cnt", "mff",
                "h5", "hdf5", "xdf",
                # ECG
                "dat", "hea", "atr", "qrs", "scp", "dcm",
                "xml", "csv", "npy", "npz", "json",
            ],
            accept_multiple_files=True,
            help="Upload all related files together. For multi-file formats "
                 "(e.g., WFDB .hea + .dat + .atr), upload all companion files "
                 "at once so they are co-located for reading."
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

    if not uploaded_files:
        # Show welcome / instructions
        st.markdown("""
        ### Drop your EEG or ECG dataset files here, or use the sidebar to upload.

        **Supported Formats:**

        | Modality | Extensions |
        |----------|-----------|
        | **EEG** | `.mat` `.edf` `.edf+` `.bdf` `.gdf` `.set` `.fdt` `.vhdr` `.fif` `.cnt` `.xdf` `.h5` |
        | **ECG** | `.dat` `.hea` `.atr` `.edf` `.scp` `.dcm` `.xml` `.mat` `.csv` `.h5` `.npy` `.npz` |

        **Multi-File Formats (upload all related files together):**

        | Format | Primary File | Companion Files |
        |--------|-------------|-----------------|
        | **WFDB** | `.hea` (header) | `.dat` `.atr` `.qrs` `.ari` |
        | **BrainVision** | `.vhdr` (header) | `.eeg` `.vmrk` |
        | **EEGLAB** | `.set` (dataset) | `.fdt` (float data) |

        **Analysis Modes:**
        - **Quick Scan**: Metadata + channel info only (~5 seconds)
        - **Full Report**: All inspection steps (~30-60 seconds)
        - **Research Mode**: Full Report + artifact maps + band PSD + correlation matrix + export
        """)

        st.info(
            "\U0001f4a1 **Tip:** For multi-file formats (e.g., WFDB .dat + .hea + .atr), "
            "select all related files at once. The inspector will automatically detect "
            "the primary file and locate companion files in the same directory."
        )
    else:
        # Files are uploaded - show all uploaded files
        total_size = sum(f.size for f in uploaded_files)
        st.success(
            f"\u2705 **{len(uploaded_files)} file(s) uploaded** "
            f"({total_size / 1024 / 1024:.2f} MB total)"
        )

        # Show file list
        with st.expander(f"\U0001f4c1 Uploaded Files ({len(uploaded_files)})", expanded=True):
            for f in uploaded_files:
                ext = Path(f.name).suffix.lower()
                if ext in _PRIMARY_EXTENSIONS:
                    st.markdown(f"- **{f.name}** ({f.size / 1024:.1f} KB) \u2014 *primary*")
                elif ext in _COMPANION_EXTENSIONS:
                    st.markdown(f"- {f.name} ({f.size / 1024:.1f} KB) \u2014 *companion*")
                else:
                    st.markdown(f"- **{f.name}** ({f.size / 1024:.1f} KB)")

        if run_btn:
            _run_inspection(uploaded_files, modality, depth)


def _run_inspection(uploaded_files, modality_selection, depth_selection):
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

    # Save ALL uploaded files to the SAME temp directory so companion
    # files (e.g., .dat, .hea, .atr) are co-located and can be found
    # by the readers automatically.
    tmp_dir = tempfile.mkdtemp(prefix="neuroinspect_")
    saved_paths = []

    try:
        for uploaded_file in uploaded_files:
            file_path = os.path.join(tmp_dir, uploaded_file.name)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getvalue())
            saved_paths.append(file_path)

        # Determine the primary file to pass to the router
        primary_path = _find_primary_file(saved_paths)

        with st.status("\U0001f50d Inspecting your dataset...", expanded=True) as status:
            st.write(f"\U0001f4c2 Detecting file format (primary: {Path(primary_path).name})...")
            route = route_file(primary_path, force_modality)

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
                report = build_eeg_report(primary_path, route["format"], depth)
            else:
                st.write("\U0001f4d6 Loading ECG data...")
                from core.ecg.report_builder import build_ecg_report
                report = build_ecg_report(primary_path, route["format"], depth)

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
        st.session_state["current_file"] = Path(primary_path).name
        st.session_state["modality"] = route["modality"]
        st.rerun()

    finally:
        # Clean up the entire temp directory
        try:
            shutil.rmtree(tmp_dir)
        except OSError:
            pass
