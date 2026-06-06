"""NeuroInspect - Biomedical Signal Analysis Tool.

Main Streamlit application entry point.
"""

import streamlit as st


def _is_streamlit_running():
    """Check if code is running under Streamlit runtime."""
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        return get_script_run_ctx() is not None
    except Exception:
        return False


def main():
    """Main application entry point."""
    # Page configuration
    st.set_page_config(
        layout="wide",
        page_title="NeuroInspect",
        page_icon="\U0001f9e0",
        initial_sidebar_state="expanded",
    )

    # Inject custom CSS
    from ui.styles import get_custom_css
    st.markdown(get_custom_css(), unsafe_allow_html=True)

    # Initialize session state
    if "inspection_result" not in st.session_state:
        st.session_state["inspection_result"] = None
    if "current_file" not in st.session_state:
        st.session_state["current_file"] = None
    if "modality" not in st.session_state:
        st.session_state["modality"] = None
    if "researcher_name" not in st.session_state:
        st.session_state["researcher_name"] = ""

    # Route to appropriate view
    inspection = st.session_state.get("inspection_result")

    if inspection is not None:
        modality = inspection.get("modality", "")

        # Sidebar: back button
        with st.sidebar:
            if st.button("\u2190 New Inspection", use_container_width=True):
                st.session_state["inspection_result"] = None
                st.session_state["current_file"] = None
                st.session_state["modality"] = None
                st.rerun()

        # Render dashboard based on modality
        if modality == "EEG":
            from ui.eeg_dashboard import render_eeg_dashboard
            render_eeg_dashboard(inspection)
        elif modality == "ECG":
            from ui.ecg_dashboard import render_ecg_dashboard
            render_ecg_dashboard(inspection)
        else:
            st.error("Unknown modality. Please start a new inspection.")
    else:
        # Landing page
        from ui.landing import render_landing
        render_landing()


# Run the app only under Streamlit runtime
if _is_streamlit_running():
    main()
