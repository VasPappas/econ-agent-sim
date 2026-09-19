"""Warm, accessible styling for the single phone-friendly workspace."""

import streamlit as st


def apply_workspace_style():
    st.markdown(
        """
<style>
.stApp { background: #faf8f1; color: #173f3b; }
.block-container { max-width: 790px; padding-top: 1.5rem; padding-bottom: 3rem; }
h1, h2, h3 { color: #173f3b; font-weight: 500 !important; letter-spacing: -.025em; }
h1 { font-size: clamp(1.8rem, 5vw, 2.5rem) !important; }
[data-testid="stCaptionContainer"] { color: #53645e; line-height: 1.5; }
[data-testid="stNumberInput"] input { font-variant-numeric: tabular-nums; }
[data-testid="stExpander"] details { border-color: #dedfd6; border-radius: 16px; }
[data-testid="stExpander"] summary { min-height: 48px; }
[data-testid="stButton"] button { min-height: 44px; border-radius: 12px; }
[data-testid="stButton"] button[kind="primary"] {
    background: #174e44; border-color: #174e44; color: white;
}
.st-key-te_mobile_nav [data-testid="stButtonGroup"] { width: 100%; flex-wrap: nowrap; }
.st-key-te_mobile_nav button {
    min-height: 44px; flex: 1; white-space: nowrap; border-radius: 12px;
}
.st-key-te_mobile_nav button[aria-checked="true"],
.st-key-te_scope_picker button[aria-checked="true"] {
    background: #174e44 !important; color: white !important;
    border-color: #174e44 !important;
}
.st-key-te_period_controls [data-testid="stHorizontalBlock"] {
    flex-direction: row !important; flex-wrap: nowrap !important; gap: .5rem;
}
.st-key-te_period_controls [data-testid="stColumn"] { min-width: 0; }
.st-key-te_starting_totals {
    border: 1px solid #dce4d7; background: #edf3ea;
    border-radius: 14px; padding: .8rem 1rem;
}
button:focus-visible, input:focus-visible, summary:focus-visible {
    outline: 2px solid #347d78; outline-offset: 3px;
}
@media(max-width: 480px) {
    .block-container { padding: 1rem .9rem 2rem; }
    input, textarea, select { font-size: 16px !important; }
    .st-key-te_mobile_nav button { padding: .4rem; }
    .st-key-te_mobile_nav button p { font-size: .875rem; }
}
</style>
""", unsafe_allow_html=True,
    )
