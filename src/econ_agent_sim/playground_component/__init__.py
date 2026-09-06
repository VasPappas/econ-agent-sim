"""Small, locally bundled Streamlit component; no CDN or Node build required."""

from pathlib import Path

import streamlit as st

from econ_agent_sim.economy_0_4 import run_economy_0_4

_ASSETS = Path(__file__).parent


@st.cache_data(show_spinner=False, max_entries=32)
def cached_economy(config):
    """Navigation and replay do not need to solve every market again."""
    return run_economy_0_4(config)


def render_playground(data):
    # Register once per page run in the active runtime, not at Python import time.
    # AppTest creates fresh runtimes while retaining imported Python modules.
    component = st.components.v2.component(
        "monetary_playground",
        html='<div class="playground-root"></div>',
        css=(_ASSETS / "styles.css").read_text(encoding="utf-8"),
        js=(_ASSETS / "component.js").read_text(encoding="utf-8"),
    )
    return component(
        data=data,
        key="economy04_playground",
        on_action_change=lambda: None,
        height="content",
        width="stretch",
    )
