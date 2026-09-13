"""Exercise two-firm restore and baseline controls through Streamlit callbacks."""

import json
from dataclasses import replace
from io import BytesIO
from pathlib import Path

import streamlit as st
from streamlit.testing.v1 import AppTest

from econ_agent_sim.competition_experiments import Experiment, dump_experiment
from econ_agent_sim.economy_1_0 import (
    Firm,
    Household,
    advance_competition_period,
    default_firms,
    default_households,
)

APP = Path(__file__).parents[1] / "app/streamlit_app.py"
PAGE = "pages/11_Economy_1_0_Two_Firms_One_Market.py"


def open_app():
    app = AppTest.from_file(APP, default_timeout=20).run()
    return app.switch_page(PAGE).run()


def button(app, label):
    return next(item for item in app.button if item.label == label)


def upload(monkeypatch, app, data):
    # AppTest cannot manipulate uploaders, so supply bytes and click the real
    # rendered action. Browser download and mobile rendering need separate QA.
    uploaded = BytesIO(data)

    def uploader(*args, key, **kwargs):
        st.session_state[key] = uploaded
        return uploaded

    monkeypatch.setattr(st, "file_uploader", uploader)
    app.run()
    button(app, "Open experiment").click().run()


def test_copy_changes_only_draft_and_reset_preserves_immutable_baseline():
    app = open_app()
    app.text_input(key="cg_name_input").set_value("Original").run()
    button(app, "Start new simulation").click().run()
    button(app, "+10 periods").click().run()
    button(app, "Save as baseline").click().run()
    baseline = app.session_state.cg_baseline
    encoded = dump_experiment(baseline)
    button(app, "Copy baseline setup").click().run()
    assert tuple(app.session_state.cg_history) == baseline.periods
    app.number_input(key="cg_firm_reinvestment_rate_1").set_value(70.0).run()
    assert tuple(app.session_state.cg_history) == baseline.periods
    button(app, "Start new simulation").click().run()
    assert not app.exception
    assert app.session_state.cg_experiment_name == "Original · variation"
    assert len(app.session_state.cg_history) == 1
    assert app.session_state.cg_history[0].firms[1].reinvestment_rate == .7
    assert dump_experiment(app.session_state.cg_baseline) == encoded
    button(app, "Reset").click().run()
    assert not app.exception
    assert not app.session_state.cg_history
    assert app.session_state.cg_baseline == baseline
    assert app.number_input(key="cg_firm_reinvestment_rate_1").value == 40


def test_open_restores_both_draft_firms_selection_scope_baseline_and_future(monkeypatch):
    households = tuple(Household(**item) for item in default_households())
    initial_firms = tuple(Firm(**item) for item in default_firms())
    firms = (replace(initial_firms[0], productivity=2.4), initial_firms[1])
    first = advance_competition_period(households, firms)
    second = advance_competition_period(households, firms, first)
    third = advance_competition_period(households, firms, second)
    saved = Experiment(
        name="Saved experiment",
        draft_households=(
            replace(households[0], money=3), households[1],
            Household("household_3", "Household 3"),
        ),
        draft_firms=(
            replace(firms[0], reinvestment_rate=.7),
            replace(firms[1], capital=1.2),
        ),
        periods=(first, second, third), selected_period=2,
        report_scope="Cumulative", selected_firm="firm_b",
    )
    baseline = replace(saved, name="Saved baseline", periods=(first, second))
    app = open_app()
    app.number_input(key="cg_firm_reinvestment_rate_0").set_value(90.0).run()
    button(app, "Start new simulation").click().run()
    upload(monkeypatch, app, dump_experiment(saved, baseline=baseline))
    assert not app.exception
    assert tuple(app.session_state.cg_history) == saved.periods
    assert app.session_state.cg_baseline == baseline
    assert app.selectbox(key="cg_selected").value == 2
    assert app.pills(key="cg_report_scope").value == "Cumulative"
    assert app.session_state.cg_selected_firm == "firm_b"
    assert app.text_input(key="cg_name_input").value == "Saved experiment"
    app.session_state.cg_view = "Set up"
    app.run()
    assert not app.exception
    assert app.number_input(key="cg_count").value == 3
    assert app.number_input(key="cg_household_money_0").value == 3
    assert app.number_input(key="cg_firm_reinvestment_rate_0").value == 70
    assert app.number_input(key="cg_firm_capital_1").value == 1.2
    app.session_state.cg_view = "Results"
    app.run()
    button(app, "Next period →").click().run()
    assert app.session_state.cg_history[-1] == advance_competition_period(
        households, firms, third,
    )
    assert len(app.session_state.cg_baseline.periods) == 2


def test_failed_baseline_import_preserves_entire_current_workspace(monkeypatch):
    app = open_app()
    button(app, "Start new simulation").click().run()
    button(app, "Next period →").click().run()
    app.pills(key="cg_report_scope").set_value("Cumulative").run()
    app.session_state.cg_selected_firm = "firm_b"
    button(app, "Save as baseline").click().run()
    baseline = app.session_state.cg_baseline
    current_history = tuple(app.session_state.cg_history)
    app.session_state.cg_view = "Set up"
    app.run()
    app.number_input(key="cg_firm_reinvestment_rate_1").set_value(70.0).run()
    generation = app.session_state.cg_generation
    invalid = json.loads(dump_experiment(
        replace(baseline, name="Should never replace current"), baseline=baseline,
    ))
    invalid["baseline"]["run"]["period_digests"][-1] = "0" * 64
    upload(monkeypatch, app, json.dumps(invalid).encode())
    assert not app.exception
    assert "Could not open" in app.session_state.cg_error
    assert tuple(app.session_state.cg_history) == current_history
    assert app.session_state.cg_baseline == baseline
    assert app.session_state.cg_generation == generation
    assert app.session_state.cg_experiment_name != "Should never replace current"
    assert app.session_state.cg_period_focus == 2
    assert app.session_state.cg_saved_scope == "Cumulative"
    assert app.session_state.cg_selected_firm == "firm_b"
    assert app.session_state.cg_view == "Set up"
    assert app.number_input(key="cg_firm_reinvestment_rate_1").value == 70


def test_legacy_upload_guides_to_original_chapter_without_replacing_state(monkeypatch):
    from econ_agent_sim.economy_0_9 import Firm as InvestmentFirm
    from econ_agent_sim.economy_0_9 import Household as InvestmentHousehold
    from econ_agent_sim.investment_experiments import Experiment as InvestmentExperiment
    from econ_agent_sim.investment_experiments import dump_experiment as dump_legacy

    old = InvestmentExperiment(
        "Old setup", (InvestmentHousehold("One"), InvestmentHousehold("Two")),
        InvestmentFirm(),
    )
    app = open_app()
    button(app, "Start new simulation").click().run()
    history = tuple(app.session_state.cg_history)
    generation = app.session_state.cg_generation
    upload(monkeypatch, app, dump_legacy(old))
    assert not app.exception
    assert app.session_state.cg_import_legacy
    assert "Economy 0.9" in app.session_state.cg_error
    assert tuple(app.session_state.cg_history) == history
    assert app.session_state.cg_generation == generation
    assert app.session_state.cg_experiment_name == "My experiment"
