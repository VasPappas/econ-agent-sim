"""Shared visual language for the home, experiment, evidence, and companion."""

import streamlit as st


def apply_workspace_style():
    palette = ("#347d78", "#ad7044", "#7772a3", "#657c49", "#a45c76", "#537992")
    agent_styles = "\n".join(
        f'.st-key-agent_card_{i} summary p::before {{ content: "{i + 1}"; background: {palette[i % len(palette)]}; }}'
        for i in range(20)
    )
    st.markdown(
        """
<style>
.stApp { background: #faf8f1; color: #173f3b; }
.block-container { max-width: 760px; padding-top: 1.5rem; padding-bottom: 2rem; }
h1, h2, h3 { color: #173f3b; font-weight: 500 !important; letter-spacing: -.035em; }
h1 { font-size: clamp(1.8rem, 5vw, 2.5rem) !important; }
[data-testid="stCaptionContainer"] { color: #65756f; font-size: .85rem; line-height: 1.6; }
[data-testid="stWidgetLabel"] p { font-size: .875rem; font-weight: 500; }
[data-testid="stNumberInput"] input { font-variant-numeric: tabular-nums; }
[data-testid="stExpander"] details { border-color: #e6e6dc; border-radius: 18px; }
[data-testid="stExpander"] summary p { font-weight: 500; }
[class*="st-key-agent_card_"] { margin-bottom: .5rem; }
[class*="st-key-agent_card_"] summary p { display: flex; align-items: center; gap: 10px; }
[class*="st-key-agent_card_"] summary p::before { display: inline-grid; place-items: center; width: 28px; height: 28px; border-radius: 50%; color: white; font-size: 12px; font-weight: 600; flex-shrink: 0; }
[data-testid="stButton"] button { min-height: 48px; border-radius: 12px; }
[data-testid="stButton"] button[kind="primary"] { background: #174e44; border-color: #174e44; color: white; }
[data-testid="stExpander"] { background: #faf8f1; border-radius: 14px; }
[data-testid="stChatMessage"] { background: #e6eee5; color: #173f3b; border-radius: 16px; }
.st-key-economy04_mobile_nav [data-testid="stButtonGroup"] { width: 100%; }
.st-key-economy04_mobile_nav [data-testid="stHorizontalBlock"] { flex-direction: row !important; flex-wrap: nowrap !important; gap: .5rem; }
.st-key-economy04_mobile_nav [data-testid="stColumn"] { min-width: 0; }
.st-key-economy04_mobile_nav button { min-height: 48px; flex: 1; border-radius: 12px; }
.st-key-economy04_mobile_nav button[aria-checked="true"] { background: #174e44 !important; color: white !important; border-color: #174e44 !important; }
.st-key-economy_home_start a { background: #174e44; color: white; min-height: 52px; padding: 14px 18px; border-radius: 14px; justify-content: center; }
.st-key-economy_home_start a p { color: white; font-size: 16px; }
@media(max-width: 480px) {
 .block-container { padding: 1.25rem 1rem 2.5rem; }
 input, textarea, select { font-size: 16px !important; }
}
</style>
""" + f"<style>{agent_styles}</style>", unsafe_allow_html=True,
    )
