"""Saved target drafts and submitted histories remain distinct in the UI."""

import json
from dataclasses import replace
from io import BytesIO
from pathlib import Path

import streamlit as st
from streamlit.testing.v1 import AppTest
from test_target_experiments import experiment

from econ_agent_sim.economy_1_1 import advance_target_period
from econ_agent_sim.target_experiments import dump_experiment

APP = Path(__file__).parents[1] / "app/streamlit_app.py"
PAGE = "pages/12_Economy_1_1_Consumption_Targets.py"


def button(app, label):
    return next(item for item in app.button if item.label == label)


def upload(monkeypatch, app, data):
    uploaded = BytesIO(data)

    def uploader(*args, key, **kwargs):
        st.session_state[key] = uploaded
        return uploaded

    monkeypatch.setattr(st, "file_uploader", uploader)
    app.run()
    button(app, "Open experiment").click().run()


def test_restore_target_draft_continues_submitted_run_and_baseline_copy_is_explicit(monkeypatch):
    baseline = experiment(2)
    saved = replace(
        baseline, name="Saved targets",
        draft_households=(replace(baseline.draft_households[0], consumption_target=0),
                          baseline.draft_households[1]),
        selected_period=2, report_scope="Cumulative", selected_firm="firm_b",
    )
    app = AppTest.from_file(APP, default_timeout=20).run().switch_page(PAGE).run()
    upload(monkeypatch, app, dump_experiment(saved, baseline=baseline))
    assert not app.exception
    assert tuple(app.session_state.tg_history) == saved.periods
    assert app.session_state.tg_baseline == baseline
    assert app.session_state.tg_selected_firm == "firm_b"
    assert app.pills(key="tg_report_scope").value == "Cumulative"
    app.session_state.tg_view = "Set up"
    app.run()
    assert app.number_input(key="tg_household_consumption_target_0").value == 0
    app.session_state.tg_view = "Results"
    app.run()
    button(app, "Next period →").click().run()
    prior = baseline.periods[-1]
    assert app.session_state.tg_history[-1] == advance_target_period(
        prior.households, prior.firms, prior,
    )
    button(app, "Copy baseline setup").click().run()
    assert app.number_input(key="tg_household_consumption_target_0").value == (
        baseline.draft_households[0].consumption_target
    )
    assert len(app.session_state.tg_history) == 3


def test_corrupted_and_old_files_leave_target_workspace_unchanged(monkeypatch):
    saved = experiment(1)
    app = AppTest.from_file(APP, default_timeout=20).run().switch_page(PAGE).run()
    upload(monkeypatch, app, dump_experiment(saved, baseline=saved))
    generation = app.session_state.tg_generation
    corrupted = json.loads(dump_experiment(saved, baseline=saved))
    corrupted["baseline"]["run"]["period_digests"][0] = "0" * 64
    upload(monkeypatch, app, json.dumps(corrupted).encode())
    assert not app.exception
    assert tuple(app.session_state.tg_history) == saved.periods
    assert app.session_state.tg_generation == generation
    assert "Could not open" in app.session_state.tg_error
    old = Path(__file__).parent / "fixtures/economy_1_0_released_workspace.json"
    upload(monkeypatch, app, old.read_bytes())
    assert not app.exception
    assert app.session_state.tg_import_legacy == "1.0"
    assert app.session_state.tg_generation == generation
    assert tuple(app.session_state.tg_history) == saved.periods
