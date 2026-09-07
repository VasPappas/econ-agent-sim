"""Shared visual language for the home, experiment, evidence, and companion."""

import streamlit as st


def apply_workspace_style():
    st.markdown(
        """
<style>
.stApp { background: #faf8f1; color: #173f3b; }
.block-container { max-width: 760px; padding-top: 1.5rem; padding-bottom: 2rem; }
h1, h2, h3 { color: #173f3b; font-weight: 500 !important; letter-spacing: -.035em; }
h1 { font-size: clamp(1.8rem, 5vw, 2.5rem) !important; }
[data-testid="stCaptionContainer"] { color: #526761; }
[data-testid="stButton"] button { min-height: 48px; border-radius: 12px; }
[data-testid="stButton"] button[kind="primary"] { background: #174e44; border-color: #174e44; color: white; }
[data-testid="stExpander"] { background: #faf8f1; border-radius: 14px; }
[data-testid="stChatMessage"] { background: #e6eee5; color: #173f3b; border-radius: 16px; }
.st-key-economy04_mobile_nav [data-testid="stButtonGroup"] { width: 100%; }
.st-key-economy04_mobile_nav button { min-height: 48px; flex: 1; border-radius: 12px; }
.st-key-economy04_mobile_nav button[aria-pressed="true"] { background: #174e44 !important; color: white !important; border-color: #174e44 !important; }
@media(max-width: 480px) {
 .block-container { padding: 1rem .85rem 2rem; }
 input, textarea, select { font-size: 16px !important; }
}
</style>
""", unsafe_allow_html=True,
    )
