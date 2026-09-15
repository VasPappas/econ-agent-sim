"""Portable experiments and frozen baselines in the two-firm workspace."""

import re
from dataclasses import asdict

import streamlit as st

from econ_agent_sim.economy_1_1 import Firm, Household
from econ_agent_sim.target_experiments import (
    MAX_NAME_LENGTH,
    Experiment,
    ExperimentError,
    LegacyExperimentError,
    dump_experiment,
    load_experiment,
)


def initialize_experiments():
    st.session_state.setdefault("tg_experiment_name", "My experiment")
    st.session_state.setdefault("tg_baseline", None)


def remember_experiment_name():
    st.session_state.tg_experiment_name = (
        st.session_state.tg_name_input.strip() or "My experiment"
    )
    st.session_state.pop("tg_copy_name", None)


def current_experiment():
    """Keep the editable setup distinct from the frozen submitted settings."""
    history = tuple(st.session_state.tg_history)
    return Experiment(
        name=st.session_state.tg_experiment_name,
        draft_households=tuple(
            Household(**item) for item in st.session_state.tg_households
        ),
        draft_firms=tuple(Firm(**item) for item in st.session_state.tg_firms),
        periods=history,
        selected_period=min(st.session_state.tg_period_focus, len(history))
        if history else 1,
        report_scope=st.session_state.tg_saved_scope,
        selected_firm=st.session_state.tg_selected_firm,
    )


def save_baseline():
    history = tuple(st.session_state.tg_history)
    if not history:
        return
    st.session_state.tg_baseline = Experiment(
        name=st.session_state.tg_experiment_name,
        draft_households=history[0].households,
        draft_firms=history[0].firms,
        periods=history,
        selected_period=st.session_state.tg_period_focus,
        report_scope=st.session_state.tg_saved_scope,
        selected_firm=st.session_state.tg_selected_firm,
    )
    st.session_state.tg_notice = (
        "Baseline kept. Its results stay fixed while you try another setup."
    )


def _replace_draft(households, firms):
    # Imported values must not be overwritten by number widgets from the old draft.
    for key in list(st.session_state):
        if key.startswith((
            "tg_household_", "tg_firm_", "tg_open_household_", "tg_open_firm_",
        )):
            del st.session_state[key]
    st.session_state.tg_households = [asdict(item) for item in households]
    st.session_state.tg_firms = [asdict(item) for item in firms]
    st.session_state.tg_count = len(households)
    st.session_state.tg_expanded = {
        key: value for key, value in st.session_state.tg_expanded.items()
        if not key.startswith(("household_", "firm_"))
    }


def edit_baseline_copy():
    baseline = st.session_state.tg_baseline
    if baseline is None:
        return
    _replace_draft(baseline.periods[0].households, baseline.periods[0].firms)
    st.session_state.tg_copy_name = f"{baseline.name[:60]} · variation"
    st.session_state.tg_view = "Set up"
    st.session_state.tg_error = None
    st.session_state.tg_notice = (
        "Baseline settings copied. Change a setting, then start a new simulation. "
        "Current results change only when you start; the baseline stays fixed."
    )


def clear_baseline():
    st.session_state.tg_baseline = None
    st.session_state.pop("tg_copy_name", None)


def restore_experiment(data):
    """Validate current and baseline completely before replacing workspace state."""
    bundle = load_experiment(data)
    current = bundle.current
    history = list(current.periods)
    _replace_draft(current.draft_households, current.draft_firms)
    st.session_state.update({
        "tg_experiment_name": current.name,
        "tg_name_input": current.name,
        "tg_history": history,
        "tg_submitted": (history[0].households, history[0].firms) if history else None,
        "tg_baseline": bundle.baseline,
        "tg_selected": current.selected_period,
        "tg_period_focus": current.selected_period,
        "tg_report_scope": current.report_scope,
        "tg_saved_scope": current.report_scope,
        "tg_selected_firm": current.selected_firm,
        "tg_generation": st.session_state.tg_generation + 1,
        "tg_view": "Results" if history else "Set up",
        "tg_error": None,
        "tg_notice": "Experiment reopened. Both firms, your setup and results are restored.",
        "tg_import_legacy": False,
    })
    for key in ("tg_copy_name", "tg_export_cache", "tg_next_view"):
        st.session_state.pop(key, None)


def open_uploaded_experiment():
    uploaded = st.session_state.get("tg_import_file")
    if uploaded is None:
        return
    try:
        restore_experiment(uploaded.getvalue())
    except LegacyExperimentError as error:
        st.session_state.tg_import_legacy = error.economy
        st.session_state.tg_error = str(error)
    except ExperimentError as error:
        st.session_state.tg_import_legacy = False
        st.session_state.tg_error = f"Could not open this experiment: {error}"


def render_experiment_controls(expander):
    """Group occasional file actions inside one persistent compact disclosure."""
    with expander("Experiments · save and compare", "experiments"):
        st.session_state.setdefault("tg_name_input", st.session_state.tg_experiment_name)
        st.text_input(
            "Experiment name", key="tg_name_input", max_chars=MAX_NAME_LENGTH,
            on_change=remember_experiment_name,
        )
        baseline = st.session_state.tg_baseline
        try:
            current = current_experiment()
            signature = (current, baseline)
            cached = st.session_state.get("tg_export_cache")
            if cached is None or cached[0] != signature:
                cached = (signature, dump_experiment(current, baseline=baseline))
                st.session_state.tg_export_cache = cached
            export = cached[1]
        except (ExperimentError, ValueError):
            export = None
        with st.container(key="tg_experiment_actions"):
            download_column, baseline_column = st.columns(2, gap="small")
            with download_column:
                filename = re.sub(
                    r"[^a-z0-9]+", "-", st.session_state.tg_experiment_name.lower(),
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
                    disabled=not st.session_state.tg_history, width="stretch",
                    help="Keep the completed run fixed for comparison."
                    if baseline is None else "Replace the baseline with this run.",
                )
        if baseline is not None:
            count = len(baseline.periods)
            st.caption(f"Baseline · {baseline.name} · {count} period{'s' if count != 1 else ''}")
            with st.container(key="tg_baseline_actions"):
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
            "Open a saved experiment", type=["json"], key="tg_import_file",
            max_upload_size=1,
        )
        if uploaded is not None:
            st.button(
                "Open experiment", on_click=open_uploaded_experiment,
                width="stretch",
                help="Restore the file’s setup, results and baseline in this workspace.",
            )
        legacy = st.session_state.get("tg_import_legacy")
        if legacy:
            page, label = (
                ("pages/10_Economy_0_9_Investment_and_Growth.py",
                 "Open Economy 0.9 · Investment and Growth")
                if legacy == "0.9" else
                ("pages/11_Economy_1_0_Two_Firms_One_Market.py",
                 "Open Economy 1.0 · Two Firms, One Market")
            )
            st.page_link(page, label=label)
