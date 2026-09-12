"""Portable experiments and baseline controls for the investment workspace."""

import re
from dataclasses import asdict

import streamlit as st

from econ_agent_sim.economy_0_9 import Firm, Household
from econ_agent_sim.investment_experiments import (
    MAX_NAME_LENGTH,
    Experiment,
    ExperimentError,
    dump_experiment,
    load_experiment,
)


def initialize_experiments():
    st.session_state.setdefault("ig_experiment_name", "My experiment")
    st.session_state.setdefault("ig_baseline", None)


def remember_experiment_name():
    name = st.session_state.ig_name_input.strip() or "My experiment"
    st.session_state.ig_experiment_name = name
    st.session_state.pop("ig_copy_name", None)


def current_experiment():
    """Snapshot the editable setup separately from the completed run."""
    history = tuple(st.session_state.ig_history)
    return Experiment(
        name=st.session_state.ig_experiment_name,
        draft_households=tuple(
            Household(**item) for item in st.session_state.ig_households
        ),
        draft_firm=Firm(**st.session_state.ig_firm),
        periods=history,
        selected_period=min(st.session_state.ig_period_focus, len(history))
        if history else 1,
        report_scope=st.session_state.ig_saved_scope,
    )


def save_baseline():
    history = tuple(st.session_state.ig_history)
    if not history:
        return
    st.session_state.ig_baseline = Experiment(
        name=st.session_state.ig_experiment_name,
        draft_households=history[0].households,
        draft_firm=history[0].firm,
        periods=history,
        selected_period=st.session_state.ig_period_focus,
        report_scope=st.session_state.ig_saved_scope,
    )
    st.session_state.ig_notice = (
        "Baseline kept. Its results stay fixed while you try another setup."
    )


def _replace_draft(households, firm):
    # Old number inputs otherwise overwrite the imported draft on the next edit.
    for key in list(st.session_state):
        if key.startswith(("ig_household_", "ig_firm_", "ig_open_household_")):
            del st.session_state[key]
    st.session_state.ig_households = [asdict(item) for item in households]
    st.session_state.ig_firm = asdict(firm)
    st.session_state.ig_count = len(households)
    st.session_state.ig_expanded = {
        key: value for key, value in st.session_state.ig_expanded.items()
        if not key.startswith("household_")
    }


def edit_baseline_copy():
    baseline = st.session_state.ig_baseline
    if baseline is None:
        return
    _replace_draft(baseline.periods[0].households, baseline.periods[0].firm)
    st.session_state.ig_copy_name = f"{baseline.name[:60]} · variation"
    st.session_state.ig_view = "Set up"
    st.session_state.ig_error = None
    st.session_state.ig_notice = (
        "Baseline settings copied to setup. Change a setting, then start a new "
        "simulation. Your baseline stays available for comparison."
    )


def clear_baseline():
    st.session_state.ig_baseline = None
    st.session_state.pop("ig_copy_name", None)


def restore_experiment(data):
    """Validate the whole file before replacing any workspace state."""
    bundle = load_experiment(data)
    current = bundle.current
    history = list(current.periods)
    _replace_draft(current.draft_households, current.draft_firm)
    st.session_state.update({
        "ig_experiment_name": current.name,
        "ig_name_input": current.name,
        "ig_history": history,
        "ig_submitted": (history[0].households, history[0].firm)
        if history else None,
        "ig_baseline": bundle.baseline,
        "ig_selected": current.selected_period,
        "ig_period_focus": current.selected_period,
        "ig_report_scope": current.report_scope,
        "ig_saved_scope": current.report_scope,
        "ig_generation": st.session_state.ig_generation + 1,
        "ig_view": "Results" if history else "Set up",
        "ig_error": None,
        "ig_notice": "Experiment reopened. Your setup and results are restored.",
    })
    st.session_state.pop("ig_copy_name", None)
    st.session_state.pop("ig_export_cache", None)
    st.session_state.pop("ig_next_view", None)


def open_uploaded_experiment():
    uploaded = st.session_state.get("ig_import_file")
    if uploaded is None:
        return
    try:
        restore_experiment(uploaded.getvalue())
    except ExperimentError as error:
        st.session_state.ig_error = f"Could not open this experiment: {error}"


def render_experiment_controls(expander):
    """Keep occasional file actions in one compact, persistent disclosure."""
    with expander("Experiments · save and compare", "experiments"):
        st.session_state.setdefault(
            "ig_name_input", st.session_state.ig_experiment_name
        )
        st.text_input(
            "Experiment name", key="ig_name_input", max_chars=MAX_NAME_LENGTH,
            on_change=remember_experiment_name,
        )
        baseline = st.session_state.ig_baseline
        try:
            current = current_experiment()
            signature = (current, baseline)
            cached = st.session_state.get("ig_export_cache")
            if cached is None or cached[0] != signature:
                cached = (signature, dump_experiment(current, baseline=baseline))
                st.session_state.ig_export_cache = cached
            export = cached[1]
        except (ExperimentError, ValueError):
            export = None
        with st.container(key="ig_experiment_actions"):
            download_column, baseline_column = st.columns(2, gap="small")
            with download_column:
                filename = re.sub(
                    r"[^a-z0-9]+", "-", st.session_state.ig_experiment_name.lower()
                ).strip("-") or "experiment"
                st.download_button(
                    "Download", data=export or b"", file_name=f"{filename}.json",
                    mime="application/json", disabled=export is None,
                    width="stretch", on_click="ignore",
                    help="Save this setup, every completed period and the baseline.",
                )
            with baseline_column:
                st.button(
                    "Save as baseline", on_click=save_baseline,
                    disabled=not st.session_state.ig_history, width="stretch",
                    help="Keep the completed run fixed for comparison."
                    if baseline is None else "Replace the baseline with this run.",
                )
        if baseline is not None:
            st.caption(
                f"Baseline · {baseline.name} · {len(baseline.periods)} periods"
            )
            with st.container(key="ig_baseline_actions"):
                edit_column, clear_column = st.columns(2, gap="small")
                with edit_column:
                    st.button(
                        "Edit a copy", on_click=edit_baseline_copy,
                        width="stretch",
                    )
                with clear_column:
                    st.button(
                        "Clear baseline", on_click=clear_baseline,
                        width="stretch",
                    )
        st.caption(
            "Download to keep your work or reopen it on another device. "
            "The file includes your baseline and any setup edits."
        )
        uploaded = st.file_uploader(
            "Open a saved experiment", type=["json"], key="ig_import_file",
            max_upload_size=1,
        )
        if uploaded is not None:
            st.button(
                "Open experiment", on_click=open_uploaded_experiment,
                width="stretch",
                help="Restore the file’s setup, results and baseline in this workspace.",
            )
