"""Render current accounts independently of the application workspace state."""

from collections.abc import Callable
from pathlib import Path

import streamlit as st

_ASSETS = Path(__file__).parent


def render_results(
    data: dict, *, key: str = "results",
    on_select_firm: Callable[[str], None] | None = None,
):
    """Render report data and deliver validated firm selections to the caller."""
    allowed = {firm["entity_id"] for firm in data["reporting"]["firms"]}
    selected = data.get("selected_firm")
    if selected not in allowed:
        selected = data["reporting"]["firms"][0]["entity_id"]
        data = {**data, "selected_firm": selected}

    # A restored workspace can choose a firm without a component click.
    if st.session_state.get(key, {}).get("selected_firm") != selected:
        st.session_state[key] = {"selected_firm": selected}

    def selected_firm_changed():
        value = st.session_state.get(key, {}).get("selected_firm")
        if value in allowed and on_select_firm is not None:
            on_select_firm(value)

    component = st.components.v2.component(
        "tiny_economy_results",
        html='<div class="results-root"></div>',
        css=(_ASSETS / "styles.css").read_text(encoding="utf-8"),
        js=(_ASSETS / "component.js").read_text(encoding="utf-8"),
    )
    return component(
        data=data, default={"selected_firm": selected},
        key=key, height="content", width="stretch",
        on_selected_firm_change=selected_firm_changed,
    )
