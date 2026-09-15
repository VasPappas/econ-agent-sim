"""Compact accounts and consumption targets for two firms and their owners."""

from pathlib import Path

import streamlit as st

_ASSETS = Path(__file__).parent
_KEY = "tg_results_component"


def _remember_selected_firm():
    selected = st.session_state.get(_KEY, {}).get("selected_firm")
    submitted = st.session_state.get("tg_submitted")
    allowed = {firm.id for firm in submitted[1]} if submitted else set()
    if selected in allowed:
        st.session_state.tg_selected_firm = selected


def render_target_results(data):
    # An opened experiment may select a different firm without a component
    # click. Keep the widget value aligned so the next tap is a real change.
    selected = data["selected_firm"]
    if st.session_state.get(_KEY, {}).get("selected_firm") != selected:
        st.session_state[_KEY] = {"selected_firm": selected}
    component = st.components.v2.component(
        "target_results",
        html='<div class="results-root"></div>',
        css=(_ASSETS / "styles.css").read_text(encoding="utf-8"),
        js=(_ASSETS / "component.js").read_text(encoding="utf-8"),
    )
    return component(
        data=data, default={"selected_firm": selected},
        key=_KEY, height="content", width="stretch",
        on_selected_firm_change=_remember_selected_firm,
    )
