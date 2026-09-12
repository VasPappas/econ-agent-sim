"""Read-only capital, cash and income statements for Economy 0.9."""

from pathlib import Path

import streamlit as st

_ASSETS = Path(__file__).parent


def render_investment_results(data):
    component = st.components.v2.component(
        "investment_growth_results",
        html='<div class="results-root"></div>',
        css=(_ASSETS / "styles.css").read_text(encoding="utf-8"),
        js=(_ASSETS / "component.js").read_text(encoding="utf-8"),
    )
    return component(
        data=data, key="economy09_results", height="content", width="stretch",
    )
