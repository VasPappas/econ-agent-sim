"""Compact Streamlit controls over the framework-independent workspace."""

import re

import streamlit as st

from econ_agent_sim import workspace
from econ_agent_sim.experiments import MAX_NAME_LENGTH, ExperimentError, dump_experiment
from econ_agent_sim.ui_text import literal


def initialize_experiments():
    workspace.initialize(st.session_state)


def remember_experiment_name():
    st.session_state.te_experiment_name = (
        st.session_state.te_name_input.strip() or "My experiment"
    )
    st.session_state.pop("te_copy_name", None)


def current_experiment():
    return workspace.current_experiment(st.session_state)


def restore_experiment(data):
    workspace.restore_experiment(st.session_state, data)


def open_uploaded_experiment():
    uploaded = st.session_state.get("te_import_file")
    if uploaded is None:
        return
    try:
        restore_experiment(uploaded.getvalue())
    except ExperimentError as error:
        st.session_state.te_error = f"Could not open this experiment: {error}"


def render_experiment_controls(expander):
    """Keep file actions, comparison management and reset in one disclosure."""
    with expander("Experiment · save, compare, reset", "experiments"):
        st.session_state.setdefault("te_name_input", st.session_state.te_experiment_name)
        st.text_input(
            "Experiment name", key="te_name_input", max_chars=MAX_NAME_LENGTH,
            on_change=remember_experiment_name,
        )
        baseline = st.session_state.te_baseline
        try:
            current = current_experiment()
            signature = (current, baseline)
            cached = st.session_state.get("te_export_cache")
            if cached is None or cached[0] != signature:
                cached = (signature, dump_experiment(current, baseline=baseline))
                st.session_state.te_export_cache = cached
            export = cached[1]
        except (ExperimentError, ValueError):
            export = None
        with st.container(key="te_experiment_actions"):
            download_column, baseline_column = st.columns(2, gap="small")
            with download_column:
                filename = re.sub(
                    r"[^a-z0-9]+", "-", st.session_state.te_experiment_name.lower(),
                ).strip("-") or "experiment"
                st.download_button(
                    "Download", data=export or b"", file_name=f"{filename}.json",
                    mime="application/json", disabled=export is None,
                    width="stretch", on_click="ignore",
                    help="Save setup edits, completed periods and the comparison baseline.",
                )
            with baseline_column:
                st.button(
                    "Save as baseline", on_click=workspace.save_baseline,
                    args=(st.session_state,), disabled=not st.session_state.te_history,
                    width="stretch",
                    help="Keep the completed run fixed for comparison."
                    if baseline is None else "Replace the baseline with this run.",
                )
        if baseline is not None:
            count = len(baseline.periods)
            st.caption(f"Baseline · {literal(baseline.name)} · {count} period{'s' if count != 1 else ''}")
            with st.container(key="te_baseline_actions"):
                copy_column, clear_column = st.columns(2, gap="small")
                with copy_column:
                    st.button(
                        "Copy baseline setup", on_click=workspace.edit_baseline_copy,
                        args=(st.session_state,), width="stretch",
                        help="Fill the setup from the baseline. Results change only when you start.",
                    )
                with clear_column:
                    st.button(
                        "Clear baseline", on_click=workspace.clear_baseline,
                        args=(st.session_state,), width="stretch",
                    )
        st.caption(
            "Download to keep your work or reopen it on another device. "
            "The file includes your baseline and any setup edits."
        )
        uploaded = st.file_uploader(
            "Open a saved experiment", type=["json"], key="te_import_file",
            max_upload_size=1,
        )
        if uploaded is not None:
            st.button(
                "Open experiment", on_click=open_uploaded_experiment,
                width="stretch",
                help="Restore the file’s setup, results and baseline in this workspace.",
            )
        st.button(
            "Reset to default", on_click=workspace.reset, args=(st.session_state,),
            width="stretch",
            help="Clear this run and restore the default setup. Keep the saved baseline.",
        )
