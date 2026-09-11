"""Phone-first, read-only Economy 0.8 financial statements."""

from pathlib import Path

import streamlit as st

_ASSETS = Path(__file__).parent


def render_firm_results(data):
    component = st.components.v2.component(
        "firm_wage_results",
        html='<div class="results-root"></div>',
        css=(_ASSETS / "styles.css").read_text(encoding="utf-8"),
        js=(_ASSETS / "component.js").read_text(encoding="utf-8"),
    )
    return component(
        data=data,
        key="economy08_results",
        height="content",
        width="stretch",
    )
