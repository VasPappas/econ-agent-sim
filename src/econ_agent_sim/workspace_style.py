"""Shared phone-first visual language for the Tiny Economy workspace."""

import streamlit as st


def apply_workspace_style():
    """Keep native widget accessibility while making controls fit a small phone."""
    palette = ("#347d78", "#ad7044", "#7772a3", "#657c49", "#a45c76", "#537992")
    household_badges = "\n".join(
        f'.st-key-te_open_household_{i} summary p::before '
        f'{{ content: "{i + 1}"; background: {palette[i % len(palette)]}; }}'
        for i in range(20)
    )
    st.markdown(
        """
<style>
.stApp {
    --economy-ink: #173f3b;
    --economy-primary: #174e44;
    --economy-muted: #53645e;
    --economy-paper: #faf8f1;
    background: var(--economy-paper);
    color: var(--economy-ink);
}
.block-container { max-width: 760px; padding-top: 1.5rem; padding-bottom: 2rem; }
h1, h2, h3 { color: var(--economy-ink); font-weight: 500 !important; letter-spacing: -.035em; }
h1 { font-size: clamp(1.8rem, 5vw, 2.5rem) !important; }
[data-testid="stCaptionContainer"] {
    color: var(--economy-muted); font-size: .85rem; line-height: 1.5;
}
[data-testid="stWidgetLabel"] p { font-size: .875rem; font-weight: 500; }
[data-testid="stNumberInput"] input { font-variant-numeric: tabular-nums; }
[data-testid="stExpander"] details { border-color: #dedfd6; border-radius: 16px; }
[data-testid="stExpander"] summary { min-height: 48px; }
[data-testid="stExpander"] summary p { font-weight: 500; }
[data-testid="stExpander"] { background: var(--economy-paper); border-radius: 16px; }
[data-testid="stButton"] button { min-height: 44px; border-radius: 12px; }
[data-testid="stButton"] button[kind="primary"] {
    background: var(--economy-primary); border-color: var(--economy-primary); color: white;
}
[data-testid="stChatMessage"] { background: #e6eee5; color: var(--economy-ink); border-radius: 16px; }
.st-key-te_mobile_nav [data-testid="stButtonGroup"] { width: 100%; flex-wrap: nowrap; }
.st-key-te_mobile_nav button {
    min-height: 44px; padding: .4rem .45rem; border-radius: 12px;
    flex: 1; white-space: nowrap;
}
.st-key-te_mobile_nav button p { font-size: .875rem; }
.st-key-te_mobile_nav button[aria-checked="true"],
.st-key-te_report_scope button[aria-checked="true"] {
    background: var(--economy-primary) !important; color: white !important;
    border-color: var(--economy-primary) !important;
}
.st-key-te_report_scope button { min-height: 44px; }
.st-key-te_period_controls [data-testid="stHorizontalBlock"],
.st-key-te_experiment_actions [data-testid="stHorizontalBlock"],
.st-key-te_baseline_actions [data-testid="stHorizontalBlock"],
[class*="st-key-te_compact_"] [data-testid="stHorizontalBlock"] {
    flex-direction: row !important; flex-wrap: nowrap !important; gap: .5rem;
}
.st-key-te_period_controls [data-testid="stColumn"],
.st-key-te_experiment_actions [data-testid="stColumn"],
.st-key-te_baseline_actions [data-testid="stColumn"],
[class*="st-key-te_compact_"] [data-testid="stColumn"] { min-width: 0; }
.st-key-te_experiment_actions button,
.st-key-te_baseline_actions button { min-height: 44px; padding: .4rem; }
.st-key-te_experiment_actions button p,
.st-key-te_baseline_actions button p { font-size: .8rem; }
[class*="st-key-te_compact_"] { margin-bottom: -.35rem; }
[class*="st-key-te_compact_"] [data-testid="stMarkdownContainer"] p {
    font-size: .875rem; line-height: 1.3; margin: 0;
}
[class*="st-key-te_compact_"] [data-testid="stNumberInput"] button {
    min-width: 44px; min-height: 44px; width: 44px;
}
[class*="st-key-te_compact_"] [data-testid="stNumberInput"] input {
    min-width: 0; padding-left: .5rem; padding-right: .2rem;
}
[class*="st-key-te_open_household_"] summary p {
    display: flex; align-items: center; gap: 10px;
}
[class*="st-key-te_open_household_"] summary p::before {
    display: inline-grid; place-items: center; width: 28px; height: 28px;
    border-radius: 50%; color: white; font-size: 12px; font-weight: 600; flex-shrink: 0;
}
[class*="st-key-te_open_firm_"] details { background: #fffdf5; border-color: #e6d8ad; }
.st-key-te_starting_totals {
    border: 1px solid #dce4d7; background: #edf3ea;
    border-radius: 14px; padding: .8rem 1rem;
}
.st-key-te_starting_totals p { margin: 0; }
button:focus-visible, input:focus-visible, summary:focus-visible {
    outline: 2px solid #347d78; outline-offset: 3px;
}
@media(max-width: 480px) {
    .block-container { padding: 1rem 1rem 2rem; }
    input, textarea, select { font-size: 16px !important; }
}
@media(max-width: 360px) {
    .st-key-te_mobile_nav button { padding-inline: .3rem; }
    .st-key-te_mobile_nav button p { font-size: .8rem; }
    .st-key-te_experiment_actions button p,
    .st-key-te_baseline_actions button p { font-size: .75rem; }
}
</style>
""" + f"<style>{household_badges}</style>", unsafe_allow_html=True,
    )
