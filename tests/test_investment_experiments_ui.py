"""Protect baseline and import state through real Streamlit callbacks."""

import json
from dataclasses import replace
from io import BytesIO
from pathlib import Path

import streamlit as st
from streamlit.testing.v1 import AppTest

from econ_agent_sim.economy_0_9 import (
    Firm,
    Household,
    advance_investment_period,
    investment_report,
)
from econ_agent_sim.investment_experiments import Experiment, dump_experiment

APP = Path(__file__).parents[1] / "app/streamlit_app.py"


def open_app():
    app = AppTest.from_file(APP, default_timeout=20).run()
    return app.switch_page("pages/10_Economy_0_9_Investment_and_Growth.py").run()


def button(app, label):
    return next(item for item in app.button if item.label == label)


def upload(monkeypatch, app, data):
    # AppTest has no file-uploader interaction. Supply its uploaded bytes while
    # still exercising the real rendered Open button and import callback.
    uploaded = BytesIO(data)

    def uploader(*args, key, **kwargs):
        st.session_state[key] = uploaded
        return uploaded

    monkeypatch.setattr(st, "file_uploader", uploader)
    app.run()
    button(app, "Open experiment").click().run()


def test_baseline_survives_copy_edit_new_run_navigation_and_reset():
    app = open_app()
    app.text_input(key="ig_name_input").set_value("Original").run()
    button(app, "Start new simulation").click().run()
    button(app, "+10 periods").click().run()
    button(app, "Save as baseline").click().run()
    baseline = app.session_state.ig_baseline
    accounts = investment_report(baseline.periods, cumulative=True)
    button(app, "Edit a copy").click().run()
    assert len(app.session_state.ig_history) == 11
    app.number_input(key="ig_firm_reinvestment_rate").set_value(70.0).run()
    button(app, "Start new simulation").click().run()
    assert not app.exception
    assert app.session_state.ig_experiment_name == "Original · variation"
    assert len(app.session_state.ig_history) == 1
    assert app.session_state.ig_history[0].firm.reinvestment_rate == .7
    button(app, "Next period →").click().run()
    app.session_state.ig_view = "Set up"
    app.run()
    app.session_state.ig_view = "Results"
    app.run()
    assert app.session_state.ig_baseline == baseline
    assert investment_report(
        app.session_state.ig_baseline.periods, cumulative=True
    ) == accounts
    button(app, "Reset").click().run()
    assert not app.exception
    assert not app.session_state.ig_history
    assert app.session_state.ig_baseline == baseline
    assert app.number_input(key="ig_firm_reinvestment_rate").value == 40


def test_open_restores_draft_selection_scope_baseline_and_continuable_run(monkeypatch):
    households = (Household("Household 1"), Household("Household 2"))
    firm = Firm(reinvestment_rate=.2)
    first = advance_investment_period(households, firm)
    second = advance_investment_period(households, firm, first)
    third = advance_investment_period(households, firm, second)
    saved = Experiment(
        name="Saved experiment",
        draft_households=(
            replace(households[0], money=3), households[1],
            Household("Household 3"),
        ),
        draft_firm=replace(firm, reinvestment_rate=.7),
        periods=(first, second, third),
        selected_period=2,
        report_scope="Cumulative",
    )
    baseline = replace(saved, name="Saved baseline", periods=(first, second))
    app = open_app()
    app.number_input(key="ig_firm_reinvestment_rate").set_value(90.0).run()
    button(app, "Start new simulation").click().run()
    upload(monkeypatch, app, dump_experiment(saved, baseline=baseline))
    assert not app.exception
    assert tuple(app.session_state.ig_history) == saved.periods
    assert app.session_state.ig_baseline == baseline
    assert app.selectbox(key="ig_selected").value == 2
    assert app.pills(key="ig_report_scope").value == "Cumulative"
    assert app.text_input(key="ig_name_input").value == "Saved experiment"
    app.session_state.ig_view = "Set up"
    app.run()
    assert not app.exception
    assert app.number_input(key="ig_count").value == 3
    assert app.number_input(key="ig_household_money_0").value == 3
    assert app.number_input(key="ig_firm_reinvestment_rate").value == 70
    app.session_state.ig_view = "Results"
    app.run()
    button(app, "Next period →").click().run()
    expected = advance_investment_period(households, firm, third)
    assert app.session_state.ig_history[-1] == expected
    assert len(app.session_state.ig_baseline.periods) == 2


def test_failed_baseline_import_preserves_whole_current_workspace(monkeypatch):
    app = open_app()
    button(app, "Start new simulation").click().run()
    button(app, "Next period →").click().run()
    app.pills(key="ig_report_scope").set_value("Cumulative").run()
    button(app, "Save as baseline").click().run()
    baseline = app.session_state.ig_baseline
    current_history = tuple(app.session_state.ig_history)
    app.session_state.ig_view = "Set up"
    app.run()
    app.number_input(key="ig_firm_reinvestment_rate").set_value(70.0).run()
    generation = app.session_state.ig_generation
    invalid = json.loads(dump_experiment(
        replace(baseline, name="Should never replace current"), baseline=baseline
    ))
    invalid["baseline"]["run"]["period_digests"][-1] = "0" * 64
    upload(monkeypatch, app, json.dumps(invalid).encode())
    assert not app.exception
    assert "Could not open" in app.session_state.ig_error
    assert tuple(app.session_state.ig_history) == current_history
    assert app.session_state.ig_baseline == baseline
    assert app.session_state.ig_generation == generation
    assert app.session_state.ig_experiment_name != "Should never replace current"
    assert app.session_state.ig_period_focus == 2
    assert app.session_state.ig_saved_scope == "Cumulative"
    assert app.session_state.ig_view == "Set up"
    assert app.number_input(key="ig_firm_reinvestment_rate").value == 70
