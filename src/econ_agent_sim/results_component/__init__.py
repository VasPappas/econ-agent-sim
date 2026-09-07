"""Locally bundled, read-only result statement; no CDN or build step."""

from pathlib import Path

import streamlit as st

from econ_agent_sim.economy_0_4 import run_economy_0_4

_ASSETS = Path(__file__).parent


@st.cache_data(show_spinner=False, max_entries=32)
def cached_economy(config):
    """Navigation does not need to solve an unchanged market again."""
    return run_economy_0_4(config)


def render_results(data):
    component = st.components.v2.component(
        "monetary_results",
        html='<div class="results-root"></div>',
        css=(_ASSETS / "styles.css").read_text(encoding="utf-8"),
        js=(_ASSETS / "component.js").read_text(encoding="utf-8"),
    )
    return component(
        data=data,
        key="economy04_results",
        height="content",
        width="stretch",
    )
