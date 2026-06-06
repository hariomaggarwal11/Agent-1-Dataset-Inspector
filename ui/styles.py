"""Custom CSS styles for NeuroInspect dark scientific theme."""


def get_custom_css():
    """Return the custom CSS for the NeuroInspect theme."""
    return """
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Inter:wght@300;400;500;600&display=swap');

:root {
    --bg-primary:    #0a0e1a;
    --bg-surface:    #111827;
    --bg-elevated:   #1a2235;
    --accent-eeg:    #00d4ff;
    --accent-ecg:    #ff4d6d;
    --accent-ok:     #22c55e;
    --accent-warn:   #f59e0b;
    --accent-fail:   #ef4444;
    --text-primary:  #f1f5f9;
    --text-muted:    #64748b;
    --border:        #1e2d45;
    --font-display:  'JetBrains Mono', 'Courier New', monospace;
    --font-body:     'Inter', system-ui, sans-serif;
}

/* Hide Streamlit branding */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

/* Main app styling */
.stApp {
    background-color: var(--bg-primary);
    font-family: var(--font-body);
}

/* Sidebar */
[data-testid="stSidebar"] {
    background-color: var(--bg-surface);
    border-right: 1px solid var(--border);
    width: 280px;
}

[data-testid="stSidebar"] .stMarkdown {
    color: var(--text-primary);
}

/* Headers */
h1, h2, h3, h4, h5, h6 {
    font-family: var(--font-display) !important;
    color: var(--text-primary) !important;
}

/* Metrics */
[data-testid="stMetric"] {
    background-color: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 16px;
}

[data-testid="stMetricValue"] {
    font-family: var(--font-display);
    color: var(--accent-eeg);
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    background-color: var(--bg-surface);
    border-radius: 8px;
    padding: 4px;
}

.stTabs [data-baseweb="tab"] {
    border-radius: 6px;
    color: var(--text-muted);
    font-family: var(--font-body);
    font-weight: 500;
}

.stTabs [aria-selected="true"] {
    background-color: var(--bg-elevated) !important;
    color: var(--accent-eeg) !important;
}

/* DataFrames */
[data-testid="stDataFrame"] {
    border: 1px solid var(--border);
    border-radius: 8px;
}

/* Buttons */
.stButton > button {
    background-color: var(--bg-elevated);
    color: var(--text-primary);
    border: 1px solid var(--border);
    border-radius: 6px;
    font-family: var(--font-body);
    font-weight: 500;
    transition: all 0.2s;
}

.stButton > button:hover {
    background-color: var(--accent-eeg);
    color: var(--bg-primary);
    border-color: var(--accent-eeg);
}

.stButton > button[kind="primary"] {
    background-color: var(--accent-eeg);
    color: var(--bg-primary);
    font-weight: 600;
}

/* File uploader */
[data-testid="stFileUploader"] {
    border: 2px dashed var(--border);
    border-radius: 12px;
    padding: 20px;
}

/* Expanders */
.streamlit-expanderHeader {
    background-color: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: 6px;
    color: var(--text-primary);
}

/* Info/Warning/Error boxes */
.stAlert {
    border-radius: 8px;
}

/* Radio buttons and selectbox */
.stRadio > label, .stSelectbox > label {
    color: var(--text-primary) !important;
    font-family: var(--font-body);
}

/* Custom card class */
.neuro-card {
    background-color: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 20px;
    margin: 10px 0;
}

/* Status badges */
.badge-pass {
    background-color: rgba(34, 197, 94, 0.1);
    color: var(--accent-ok);
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.85em;
    font-weight: 600;
}

.badge-warn {
    background-color: rgba(245, 158, 11, 0.1);
    color: var(--accent-warn);
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.85em;
    font-weight: 600;
}

.badge-fail {
    background-color: rgba(239, 68, 68, 0.1);
    color: var(--accent-fail);
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.85em;
    font-weight: 600;
}
</style>
"""
