"""Portable experiments and frozen baselines in the two-firm workspace."""

import re
from dataclasses import asdict

import streamlit as st

from econ_agent_sim.competition_experiments import (
    MAX_NAME_LENGTH,
    Experiment,
    ExperimentError,
    LegacyExperimentError,
    dump_experiment,
    load_experiment,
)
from econ_agent_sim.economy_1_0 import Firm, Household


def initialize_experiments():
    st.session_state.setdefault("cg_experiment_name", "My experiment")
    st.session_state.setdefault("cg_baseline", None)


def remember_experiment_name():
    st.session_state.cg_experiment_name = (
        st.session_state.cg_name_input.strip() or "My experiment"
    )
    st.session_state.pop("cg_copy_name", None)


def current_experiment():
    """Keep the editable setup distinct from the frozen submitted settings."""
    history = tuple(st.session_state.cg_history)
    return Experiment(
        name=st.session_state.cg_experiment_name,
        draft_households=tuple(
            Household(**item) for item in st.session_state.cg_households
        ),
        draft_firms=tuple(Firm(**item) for item in st.session_state.cg_firms),
        periods=history,
        selected_period=min(st.session_state.cg_period_focus, len(history))
        if history else 1,
        report_scope=st.session_state.cg_saved_scope,
        selected_firm=st.session_state.cg_selected_firm,
    )


def save_baseline():
    history = tuple(st.session_state.cg_history)
    if not history:
        return
    st.session_state.cg_baseline = Experiment(
        name=st.session_state.cg_experiment_name,
        draft_households=history[0].households,
        draft_firms=history[0].firms,
        periods=history,
        selected_period=st.session_state.cg_period_focus,
        report_scope=st.session_state.cg_saved_scope,
        selected_firm=st.session_state.cg_selected_firm,
    )
    st.session_state.cg_notice = (
        "Baseline kept. Its results stay fixed while you try another setup."
    )


def _replace_draft(households, firms):
    # Imported values must not be overwritten by number widgets from the old draft.
    for key in list(st.session_state):
        if key.startswith((
            "cg_household_", "cg_firm_", "cg_open_household_", "cg_open_firm_",
        )):
            del st.session_state[key]
    st.session_state.cg_households = [asdict(item) for item in households]
    st.session_state.cg_firms = [asdict(item) for item in firms]
    st.session_state.cg_count = len(households)
    st.session_state.cg_expanded = {
        key: value for key, value in st.session_state.cg_expanded.items()
        if not key.startswith(("household_", "firm_"))
    }


def edit_baseline_copy():
    baseline = st.session_state.cg_baseline
    if baseline is None:
        return
    _replace_draft(baseline.periods[0].households, baseline.periods[0].firms)
    st.session_state.cg_copy_name = f"{baseline.name[:60]} · variation"
    st.session_state.cg_view = "Set up"
    st.session_state.cg_error = None
    st.session_state.cg_notice = (
        "Baseline settings copied. Change a setting, then start a new simulation. "
        "Current results change only when you start; the baseline stays fixed."
    )


def clear_baseline():
    st.session_state.cg_baseline = None
    st.session_state.pop("cg_copy_name", None)


def restore_experiment(data):
    """Validate current and baseline completely before replacing workspace state."""
    bundle = load_experiment(data)
    current = bundle.current
    history = list(current.periods)
    _replace_draft(current.draft_households, current.draft_firms)
    st.session_state.update({
        "cg_experiment_name": current.name,
        "cg_name_input": current.name,
        "cg_history": history,
        "cg_submitted": (history[0].households, history[0].firms) if history else None,
        "cg_baseline": bundle.baseline,
        "cg_selected": current.selected_period,
        "cg_period_focus": current.selected_period,
        "cg_report_scope": current.report_scope,
        "cg_saved_scope": current.report_scope,
        "cg_selected_firm": current.selected_firm,
        "cg_generation": st.session_state.cg_generation + 1,
        "cg_view": "Results" if history else "Set up",
        "cg_error": None,
        "cg_notice": "Experiment reopened. Both firms, your setup and results are restored.",
        "cg_import_legacy": False,
    })
    for key in ("cg_copy_name", "cg_export_cache", "cg_next_view"):
        st.session_state.pop(key, None)


def open_uploaded_experiment():
    uploaded = st.session_state.get("cg_import_file")
    if uploaded is None:
        return
    try:
        restore_experiment(uploaded.getvalue())
    except LegacyExperimentError as error:
        st.session_state.cg_import_legacy = True
        st.session_state.cg_error = str(error)
    except ExperimentError as error:
        st.session_state.cg_import_legacy = False
        st.session_state.cg_error = f"Could not open this experiment: {error}"


def render_experiment_controls(expander):
    """Group occasional file actions inside one persistent compact disclosure."""
    with expander("Experiments · save and compare", "experiments"):
        st.session_state.setdefault("cg_name_input", st.session_state.cg_experiment_name)
        st.text_input(
            "Experiment name", key="cg_name_input", max_chars=MAX_NAME_LENGTH,
            on_change=remember_experiment_name,
        )
        baseline = st.session_state.cg_baseline
        try:
            current = current_experiment()
            signature = (current, baseline)
            cached = st.session_state.get("cg_export_cache")
            if cached is None or cached[0] != signature:
                cached = (signature, dump_experiment(current, baseline=baseline))
                st.session_state.cg_export_cache = cached
            export = cached[1]
        except (ExperimentError, ValueError):
            export = None
        with st.container(key="cg_experiment_actions"):
            download_column, baseline_column = st.columns(2, gap="small")
            with download_column:
                filename = re.sub(
                    r"[^a-z0-9]+", "-", st.session_state.cg_experiment_name.lower(),
                ).strip("-") or "experiment"
                st.download_button(
                    "Download", data=export or b"", file_name=f"{filename}.json",
                    mime="application/json", disabled=export is None,
                    width="stretch", on_click="ignore",
                    help="Save both firms, setup edits, completed periods and the baseline.",
                )
            with baseline_column:
                st.button(
                    "Save as baseline", on_click=save_baseline,
                    disabled=not st.session_state.cg_history, width="stretch",
                    help="Keep the completed run fixed for comparison."
                    if baseline is None else "Replace the baseline with this run.",
                )
        if baseline is not None:
            count = len(baseline.periods)
            st.caption(f"Baseline · {baseline.name} · {count} period{'s' if count != 1 else ''}")
            with st.container(key="cg_baseline_actions"):
                copy_column, clear_column = st.columns(2, gap="small")
                with copy_column:
                    st.button(
                        "Copy baseline setup", on_click=edit_baseline_copy,
                        width="stretch",
                        help="Fill the setup from the baseline. Results change only when you start.",
                    )
                with clear_column:
                    st.button("Clear baseline", on_click=clear_baseline, width="stretch")
        st.caption(
            "Download to keep your work or reopen it on another device. "
            "The file includes your baseline and any setup edits."
        )
        uploaded = st.file_uploader(
            "Open a saved experiment", type=["json"], key="cg_import_file",
            max_upload_size=1,
        )
        if uploaded is not None:
            st.button(
                "Open experiment", on_click=open_uploaded_experiment,
                width="stretch",
                help="Restore the file’s setup, results and baseline in this workspace.",
            )
        if st.session_state.get("cg_import_legacy"):
            st.page_link(
                "pages/10_Economy_0_9_Investment_and_Growth.py",
                label="Open Economy 0.9 · Investment and Growth",
            )
