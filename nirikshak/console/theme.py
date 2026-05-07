"""Nirikshak UI theme — CSS injection and styled components."""

import streamlit as st

# ── Color palette ─────────────────────────────────────────────────────

NAVY = "#1B4F72"
DARK = "#2C3E50"
SUCCESS = "#27AE60"
DANGER = "#E74C3C"
WARNING = "#F39C12"
INFO = "#2980B9"
SURFACE = "#F8F9FA"
MUTED = "#95A5A6"
WHITE = "#FFFFFF"

VERDICT_COLORS = {
    "eligible": SUCCESS,
    "not_eligible": DANGER,
    "needs_review": WARNING,
}

CRITERION_COLORS = {
    "financial_threshold": "#2980B9",
    "experience_count": "#E67E22",
    "statutory_registration": "#8E44AD",
    "quality_certification": "#27AE60",
    "document_checklist": "#2C3E50",
    "policy_compliance": "#16A085",
}


def inject_global_css():
    """Inject global CSS for the entire app. Call once per page."""
    st.markdown("""
    <style>
    /* ═══════════════════════════════════════════════════════════════════
       HIDE STREAMLIT CHROME
       ═══════════════════════════════════════════════════════════════════ */
    header[data-testid="stHeader"] {display: none !important;}
    [data-testid="stToolbar"] {display: none !important;}
    [data-testid="stDeployButton"] {display: none !important;}
    .stDeployButton {display: none !important;}
    button[kind="header"] {display: none !important;}
    [data-testid="baseButton-header"] {display: none !important;}
    #MainMenu {display: none !important;}
    footer {display: none !important;}
    [data-testid="stSidebarCollapseButton"] {display: none !important;}
    [data-testid="stSidebarNav"] {display: none !important;}

    /* ═══════════════════════════════════════════════════════════════════
       HIDE RAW MATERIAL ICONS TEXT
       ═══════════════════════════════════════════════════════════════════ */
    [data-testid="stIconMaterial"] {
        font-size: 0 !important;
        overflow: hidden !important;
    }
    [data-testid="stIconMaterial"]::after {
        content: "" !important;
    }

    /* ═══════════════════════════════════════════════════════════════════
       TYPOGRAPHY
       ═══════════════════════════════════════════════════════════════════ */
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }

    /* ═══════════════════════════════════════════════════════════════════
       SIDEBAR — Navy gradient, white text
       ═══════════════════════════════════════════════════════════════════ */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1A3A5C 0%, #0D2B45 100%) !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stSidebarContent"] {
        background: transparent !important;
    }

    /* Sidebar — all text and links white */
    section[data-testid="stSidebar"],
    section[data-testid="stSidebar"] *:not(input):not(select):not(textarea):not([data-baseweb="input"] *):not([data-baseweb="select"] *) {
    }
    section[data-testid="stSidebar"] a,
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] span,
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3,
    section[data-testid="stSidebar"] .stMarkdown,
    section[data-testid="stSidebar"] .stMarkdown p,
    section[data-testid="stSidebar"] .stMarkdown span,
    section[data-testid="stSidebar"] [data-testid="stCaption"],
    section[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"] {
        color: rgba(255, 255, 255, 0.85) !important;
    }
    section[data-testid="stSidebar"] a:hover {
        color: white !important;
        background: rgba(255, 255, 255, 0.08) !important;
    }

    /* Sidebar — buttons */
    section[data-testid="stSidebar"] button {
        color: rgba(255, 255, 255, 0.85) !important;
        border-color: rgba(255, 255, 255, 0.2) !important;
    }
    section[data-testid="stSidebar"] button:hover {
        color: white !important;
        border-color: rgba(255, 255, 255, 0.5) !important;
        background: rgba(255, 255, 255, 0.08) !important;
    }

    /* Sidebar — inputs: DARK TEXT on WHITE background */
    section[data-testid="stSidebar"] input,
    section[data-testid="stSidebar"] textarea,
    section[data-testid="stSidebar"] [data-baseweb="input"],
    section[data-testid="stSidebar"] [data-baseweb="input"] input,
    section[data-testid="stSidebar"] [data-baseweb="select"],
    section[data-testid="stSidebar"] [data-baseweb="select"] *,
    section[data-testid="stSidebar"] [role="combobox"] {
        color: #2C3E50 !important;
        background-color: white !important;
        -webkit-text-fill-color: #2C3E50 !important;
    }
    section[data-testid="stSidebar"] input::placeholder,
    section[data-testid="stSidebar"] textarea::placeholder {
        color: #95A5A6 !important;
        -webkit-text-fill-color: #95A5A6 !important;
    }

    /* Sidebar — separators */
    section[data-testid="stSidebar"] hr {
        border-color: rgba(255, 255, 255, 0.12) !important;
    }

    /* Sidebar — page link active state */
    section[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"][aria-current="page"] {
        background: rgba(255, 255, 255, 0.12) !important;
        color: white !important;
        font-weight: 600 !important;
    }

    /* ═══════════════════════════════════════════════════════════════════
       MAIN CONTENT — Clean light theme
       ═══════════════════════════════════════════════════════════════════ */
    .block-container {
        padding-top: 1rem !important;
        max-width: 1200px;
    }

    /* ═══════════════════════════════════════════════════════════════════
       METRIC CARDS
       ═══════════════════════════════════════════════════════════════════ */
    [data-testid="stMetric"] {
        background: white;
        border-radius: 12px;
        padding: 16px 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        border-left: 4px solid #2980B9;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.85rem !important;
        color: #7f8c8d !important;
        font-weight: 500 !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    [data-testid="stMetricValue"] {
        font-size: 2rem !important;
        font-weight: 700 !important;
        color: #2C3E50 !important;
    }

    /* ═══════════════════════════════════════════════════════════════════
       BUTTONS
       ═══════════════════════════════════════════════════════════════════ */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #1B4F72 0%, #2980B9 100%) !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.5rem 1.5rem !important;
        font-weight: 600 !important;
        color: white !important;
    }
    .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #154360 0%, #1B6FA8 100%) !important;
    }

    /* ═══════════════════════════════════════════════════════════════════
       EXPANDERS
       ═══════════════════════════════════════════════════════════════════ */
    .streamlit-expanderHeader {
        font-weight: 600 !important;
        font-size: 1rem !important;
    }

    /* ═══════════════════════════════════════════════════════════════════
       DATAFRAMES / TABLES
       ═══════════════════════════════════════════════════════════════════ */
    .stDataFrame {
        border-radius: 8px;
        overflow: hidden;
    }

    /* ═══════════════════════════════════════════════════════════════════
       DATE INPUT — hide accessibility text, keep label
       ═══════════════════════════════════════════════════════════════════ */
    [data-testid="stDateInput"] small {
        display: none;
    }
    </style>
    """, unsafe_allow_html=True)


def verdict_pill(state: str, size: str = "normal") -> str:
    """Return HTML for a colored verdict pill badge."""
    color = VERDICT_COLORS.get(state, MUTED)
    labels = {"eligible": "Eligible", "not_eligible": "Not Eligible", "needs_review": "Needs Review"}
    label = labels.get(state, state)
    icons = {"eligible": "&#10003;", "not_eligible": "&#10007;", "needs_review": "&#9888;"}
    icon = icons.get(state, "")

    if size == "large":
        return (
            f'<span style="background:{color}; color:white; padding:8px 20px; '
            f'border-radius:20px; font-weight:700; font-size:1.1rem; '
            f'display:inline-block; letter-spacing:0.5px;">'
            f'{icon} {label}</span>'
        )
    return (
        f'<span style="background:{color}; color:white; padding:3px 12px; '
        f'border-radius:12px; font-weight:600; font-size:0.8rem; '
        f'display:inline-block;">'
        f'{icon} {label}</span>'
    )


def criterion_badge(ctype: str) -> str:
    """Return HTML for a criterion type badge."""
    color = CRITERION_COLORS.get(ctype, MUTED)
    labels = {
        "financial_threshold": "Financial",
        "experience_count": "Experience",
        "statutory_registration": "Registration",
        "quality_certification": "Certification",
        "document_checklist": "Document",
        "policy_compliance": "Compliance",
    }
    label = labels.get(ctype, ctype)
    return (
        f'<span style="background:{color}15; color:{color}; padding:2px 10px; '
        f'border-radius:6px; font-weight:600; font-size:0.75rem; '
        f'border:1px solid {color}40;">{label}</span>'
    )


def status_card(title: str, value: str, color: str = INFO, icon: str = "") -> str:
    """Return HTML for a styled status card."""
    return f"""
    <div style="background:white; border-radius:12px; padding:20px; margin:8px 0;
                box-shadow:0 1px 3px rgba(0,0,0,0.08); border-left:4px solid {color};">
        <div style="color:{MUTED}; font-size:0.8rem; text-transform:uppercase;
                    letter-spacing:0.5px; margin-bottom:4px;">{icon} {title}</div>
        <div style="color:{DARK}; font-size:1.8rem; font-weight:700;">{value}</div>
    </div>
    """


def info_banner(text: str, color: str = INFO) -> str:
    """Return HTML for a styled info banner."""
    return f"""
    <div style="background:{color}10; border-left:4px solid {color}; padding:12px 16px;
                border-radius:0 8px 8px 0; margin:12px 0;">
        <span style="color:{color}; font-weight:500;">{text}</span>
    </div>
    """


def section_header(title: str, subtitle: str = "") -> str:
    """Return HTML for a styled section header."""
    sub = f'<div style="color:{MUTED}; font-size:0.9rem; margin-top:2px;">{subtitle}</div>' if subtitle else ""
    return f"""
    <div style="margin:24px 0 16px 0;">
        <div style="color:{DARK}; font-size:1.4rem; font-weight:700;">{title}</div>
        {sub}
    </div>
    """


def confidence_bar(value: float) -> str:
    """Return HTML for a styled confidence bar."""
    pct = min(value * 100, 100)
    color = SUCCESS if pct >= 85 else (WARNING if pct >= 50 else DANGER)
    return f"""
    <div style="background:#ecf0f1; border-radius:6px; height:8px; width:100%; margin:4px 0;">
        <div style="background:{color}; border-radius:6px; height:8px; width:{pct}%;"></div>
    </div>
    <span style="color:{MUTED}; font-size:0.75rem;">{pct:.0f}%</span>
    """


def pipeline_step(steps: list[dict]) -> str:
    """Return HTML for a pipeline visualization. Each step: {name, active, done}."""
    html = '<div style="display:flex; align-items:center; gap:0; margin:20px 0;">'
    for i, step in enumerate(steps):
        if step.get("done"):
            bg, fg = SUCCESS, WHITE
        elif step.get("active"):
            bg, fg = INFO, WHITE
        else:
            bg, fg = "#ecf0f1", MUTED

        html += f"""
        <div style="background:{bg}; color:{fg}; padding:10px 16px; font-weight:600;
                    font-size:0.8rem; text-align:center; flex:1;
                    {'border-radius:8px 0 0 8px;' if i == 0 else ''}
                    {'border-radius:0 8px 8px 0;' if i == len(steps)-1 else ''}">
            {step['name']}
        </div>
        """
        if i < len(steps) - 1:
            html += f'<div style="color:{bg}; font-size:1.2rem;">&#9654;</div>'
    html += '</div>'
    return html
