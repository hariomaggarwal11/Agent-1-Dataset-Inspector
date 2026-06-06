"""Reusable UI components for NeuroInspect."""

import streamlit as st
import plotly.graph_objects as go


def render_metric_card(label, value, status=None):
    """Render a metric with optional status badge."""
    status_emoji = ""
    if status == "pass":
        status_emoji = " \U0001f7e2"
    elif status == "warn":
        status_emoji = " \U0001f7e1"
    elif status == "fail":
        status_emoji = " \U0001f534"

    st.metric(label=label, value=f"{value}{status_emoji}")


def render_status_badge(status, text=None):
    """Return HTML for a status badge."""
    if status == "pass":
        emoji = "\U0001f7e2"
        label = text or "PASS"
    elif status == "warn":
        emoji = "\U0001f7e1"
        label = text or "WARN"
    elif status == "fail":
        emoji = "\U0001f534"
        label = text or "FAIL"
    else:
        emoji = "\u26aa"
        label = text or "UNKNOWN"

    return f"{emoji} {label}"


def render_quality_gauge(score, max_score=100):
    """Render a circular gauge chart for quality score."""
    if score >= 71:
        color = "#22c55e"
    elif score >= 41:
        color = "#f59e0b"
    else:
        color = "#ef4444"

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        domain={"x": [0, 1], "y": [0, 1]},
        title={"text": "Data Quality Score", "font": {"size": 16, "color": "#f1f5f9"}},
        number={"suffix": f"/{max_score}", "font": {"color": "#f1f5f9", "size": 40}},
        gauge={
            "axis": {"range": [0, max_score], "tickcolor": "#64748b"},
            "bar": {"color": color},
            "bgcolor": "#1a2235",
            "borderwidth": 2,
            "bordercolor": "#1e2d45",
            "steps": [
                {"range": [0, 40], "color": "rgba(239, 68, 68, 0.1)"},
                {"range": [40, 70], "color": "rgba(245, 158, 11, 0.1)"},
                {"range": [70, 100], "color": "rgba(34, 197, 94, 0.1)"},
            ],
        }
    ))

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=250,
        margin=dict(t=40, b=0, l=30, r=30),
    )

    return fig


def render_artifact_table(artifacts):
    """Render artifact detection results as a formatted table."""
    if not artifacts:
        st.info("No artifact analysis available.")
        return

    st.markdown("### Artifact Scan Results")

    for check_name, result in artifacts.items():
        if not isinstance(result, dict):
            continue

        status = result.get("status", "unknown")
        detail = result.get("detail", "")

        badge = render_status_badge(status)
        display_name = check_name.replace("_", " ").title()

        col1, col2, col3 = st.columns([3, 2, 5])
        with col1:
            st.write(display_name)
        with col2:
            st.write(badge)
        with col3:
            st.write(detail)


def render_summary_card(filename, format_name, status, load_time, file_size):
    """Render the file summary card at top of dashboard."""
    status_badge = render_status_badge(status, "READABLE" if status == "pass" else "ERROR")

    st.markdown(f"""
    <div class="neuro-card">
        <strong>{filename}</strong> &nbsp;|&nbsp; {format_name} &nbsp;|&nbsp; {status_badge}<br>
        <small>Loaded in {load_time} &nbsp;|&nbsp; Size: {file_size}</small>
    </div>
    """, unsafe_allow_html=True)
