"""Exercise the actual current-model controls, charts and stateful user journeys."""

import json
from io import BytesIO
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from econ_agent_sim.domain import Settings
from econ_agent_sim.presets import PRESETS, build_preset

APP = Path(__file__).parents[1] / "app/streamlit_app.py"


def open_app():
    app = AppTest.from_file(APP, default_timeout=45).run()
    assert not app.exception
    return app


def button(app, label):
    return next(item for item in app.button if item.label == label)


def switch_view(app, view):
    app.pills(key="te_view").set_value(view).run()
    assert not app.exception


def start_default(app):
    button(app, "Start new simulation").click().run()
    assert not app.exception
    assert app.session_state.te_visible_periods == 1
    return app.session_state.te_run


def test_setup_has_six_current_controls_and_no_retired_model_or_chat(monkeypatch):
    monkeypatch.setenv("ECON_CHAT_ENABLED", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "unused")
    app = open_app()
    assert len(app.number_input) == 6
    assert len(app.selectbox) == 1
    assert tuple(app.selectbox(key="te_preset_choice").options) == tuple(
        preset.title for preset in PRESETS.values()
    )
    assert not app.chat_input and not app.chat_message
    assert not app.get("bidi_component")
    assert app.session_state.te_draft == Settings()


def test_start_reports_both_agents_and_consistent_economy_totals():
    app = open_app()
    run = start_default(app)
    assert app.pills(key="te_view").value == "Results"
    assert len(run.periods) == 100
    assert len(app.dataframe[0].value) == 2
    assert app.dataframe[0].value["Household"].tolist() == ["Household 1", "Household 2"]
    first = run.periods[0]
    output = next(metric for metric in app.metric if metric.label == "Total output · X")
    assert float(output.value.replace(",", "")) == pytest.approx(2 * first.output, abs=5e-5)
    assert any("accounts balance" in message.value for message in app.success)


def test_percent_controls_preserve_precision_drafts_and_submitted_run():
    app = open_app()
    app.number_input(key="te_input_beta").set_value(95.125).run()
    app.number_input(key="te_input_initial_firm_cash_share").set_value(50.125).run()
    assert app.session_state.te_draft.beta == pytest.approx(.95125)
    assert app.session_state.te_draft.initial_firm_cash_share == pytest.approx(.50125)
    switch_view(app, "Ask why")
    switch_view(app, "Set up")
    assert app.number_input(key="te_input_beta").value == 95.125
    run = start_default(app)
    switch_view(app, "Set up")
    app.number_input(key="te_input_initial_capital").set_value(2.).run()
    switch_view(app, "Results")
    assert any("Draft changed" in item.value for item in app.info)
    button(app, "+10 periods").click().run()
    assert not app.exception
    assert app.session_state.te_run is run
    assert run.settings.initial_capital == 1.
    assert app.session_state.te_visible_periods == 11
    switch_view(app, "Set up")
    assert app.number_input(key="te_input_initial_capital").value == 2.


def test_advancing_and_historical_cumulative_views_never_resolve(monkeypatch):
    from econ_agent_sim import workspace

    app = open_app()
    run = start_default(app)

    def unexpected_solve(*args, **kwargs):
        pytest.fail("Revealing or selecting a period must not solve a new plan")

    monkeypatch.setattr(workspace, "simulate", unexpected_solve)
    button(app, "+10 periods").click().run()
    assert not app.exception
    app.selectbox(key="te_period_picker").set_value(4).run()
    app.pills(key="te_scope_picker").set_value("Cumulative").run()
    assert any(item.value == "Periods 1–4" for item in app.subheader)
    assert app.session_state.te_scope == "Cumulative"
    switch_view(app, "Ask why")
    app.selectbox(key="te_question").set_value("Why did capital change?").run()
    assert not app.exception
    switch_view(app, "Set up")
    switch_view(app, "Results")
    assert app.selectbox(key="te_period_picker").value == 4
    assert app.pills(key="te_scope_picker").value == "Cumulative"
    button(app, "Next period →").click().run()
    assert app.session_state.te_visible_periods == 12
    assert app.session_state.te_selected_period == 12
    assert app.session_state.te_run is run
    assert not app.exception


def test_preset_selection_requires_apply_and_keeps_current_run_and_baseline():
    app = open_app()
    run = start_default(app)
    button(app, "Save as baseline").click().run()
    baseline = app.session_state.te_baseline
    switch_view(app, "Set up")
    app.selectbox(key="te_preset_choice").set_value("capital_abundant").run()
    assert app.session_state.te_draft == Settings()
    button(app, "Use this setup").click().run()
    assert app.number_input(key="te_input_initial_capital").value == 100.
    assert app.session_state.te_run is run
    assert app.session_state.te_baseline is baseline
    button(app, "Start new simulation").click().run()
    assert not app.exception
    assert app.session_state.te_run.periods[0].investment == 0
    assert any("invest zero" in item.value for item in app.info)
    button(app, "+10 periods").click().run()
    assert any("Both experiments need Period 11" in item.value for item in app.info)
    app.selectbox(key="te_period_picker").set_value(1).run()
    assert not any("Both experiments need" in item.value for item in app.info)
    button(app, "Copy baseline setup").click().run()
    assert app.pills(key="te_view").value == "Set up"
    assert app.session_state.te_draft == Settings()
    assert app.session_state.te_visible_periods == 11
    assert app.session_state.te_baseline is baseline


def test_unsupported_setup_keeps_existing_results_and_baseline_and_can_recover():
    app = open_app()
    run = start_default(app)
    button(app, "Save as baseline").click().run()
    baseline = app.session_state.te_baseline
    switch_view(app, "Set up")
    app.number_input(key="te_input_initial_capital").set_value(.1).run()
    app.number_input(key="te_input_initial_firm_cash_share").set_value(99.).run()
    button(app, "Start new simulation").click().run()
    assert not app.exception
    assert any("opening money unspent" in item.value for item in app.error)
    assert app.session_state.te_run is run
    assert app.session_state.te_baseline is baseline
    assert app.session_state.te_visible_periods == 1
    app.selectbox(key="te_preset_choice").set_value("growing").run()
    button(app, "Use this setup").click().run()
    button(app, "Start new simulation").click().run()
    assert not app.exception and not app.error
    assert app.session_state.te_run.settings == Settings()


def test_stationary_preset_does_not_round_away_the_analytical_start():
    app = open_app()
    app.selectbox(key="te_preset_choice").set_value("stationary").run()
    button(app, "Use this setup").click().run()
    expected = build_preset("stationary")
    assert app.session_state.te_draft == expected
    button(app, "Start new simulation").click().run()
    assert not app.exception
    run = app.session_state.te_run
    assert run.settings.initial_capital == expected.initial_capital
    assert run.settings.initial_firm_cash_share == pytest.approx(expected.initial_firm_cash_share)
    assert run.periods[-1].capital == pytest.approx(run.periods[0].capital, rel=1e-8)


def test_invalid_rename_recovers_and_user_names_are_literal():
    from econ_agent_sim.ui_text import literal

    app = open_app()
    run = start_default(app)
    app.text_input(key="te_name_input").set_value("Bad\tname").run()
    assert any("Could not rename" in item.value for item in app.error)
    assert app.text_input(key="te_name_input").value == "My experiment"
    assert app.session_state.te_run is run
    name = "![preview](https://example.com/image)"
    app.text_input(key="te_name_input").set_value(name).run()
    assert not app.exception and not app.error
    assert any(literal(name) in item.value for item in app.caption)
    assert not any(name in item.value for item in app.markdown)


def test_old_file_open_fails_atomically_and_reset_retains_baseline(monkeypatch):
    import streamlit as st

    uploaded = BytesIO(json.dumps({"format": "tiny-economy-experiment", "format_version": 5}).encode())

    def uploader(*args, **kwargs):
        st.session_state[kwargs["key"]] = uploaded
        return uploaded

    monkeypatch.setattr(st, "file_uploader", uploader)
    app = open_app()
    run = start_default(app)
    button(app, "Save as baseline").click().run()
    baseline = app.session_state.te_baseline
    button(app, "Open experiment").click().run()
    assert not app.exception and app.error
    assert app.session_state.te_run is run
    assert app.session_state.te_baseline is baseline
    button(app, "Reset to default").click().run()
    assert not app.exception
    assert app.session_state.te_run is None
    assert app.session_state.te_draft == Settings()
    assert app.session_state.te_baseline is baseline
    assert app.pills(key="te_view").value == "Set up"


def test_a_previous_model_session_starts_fresh_with_an_explanation():
    app = AppTest.from_file(APP, default_timeout=45)
    app.session_state.te_model_id = "old-one-period-model"
    app.session_state.te_history = ["old results"]
    app.session_state.te_name = "Old experiment"
    app.run()
    assert not app.exception
    assert app.session_state.te_run is None
    assert app.session_state.te_name == "My experiment"
    assert any("previous" in item.value for item in app.success)


def test_saved_experiment_reopens_draft_run_baseline_and_report_selection(monkeypatch):
    import streamlit as st

    from econ_agent_sim.experiments import dumps_experiment

    upload = [None]

    def uploader(*args, **kwargs):
        st.session_state[kwargs["key"]] = upload[0]
        return upload[0]

    monkeypatch.setattr(st, "file_uploader", uploader)
    app = open_app()
    start_default(app)
    button(app, "+10 periods").click().run()
    app.pills(key="te_scope_picker").set_value("Cumulative").run()
    button(app, "Save as baseline").click().run()
    switch_view(app, "Set up")
    app.number_input(key="te_input_initial_capital").set_value(2.).run()
    app.text_input(key="te_name_input").set_value("Saved experiment").run()
    saved = dumps_experiment(app.session_state)
    button(app, "Reset to default").click().run()
    upload[0] = BytesIO(saved.encode())
    app.run()
    button(app, "Open experiment").click().run()
    assert not app.exception and not app.error
    assert app.session_state.te_name == "Saved experiment"
    assert app.session_state.te_draft.initial_capital == 2.
    assert app.session_state.te_run.settings.initial_capital == 1.
    assert app.session_state.te_visible_periods == 11
    assert app.session_state.te_baseline.visible_periods == 11
    assert app.session_state.te_selected_period == 11
    switch_view(app, "Results")
    assert app.pills(key="te_scope_picker").value == "Cumulative"
    assert any("Draft changed" in item.value for item in app.info)
    assert any(item.value == "Periods 1–11" for item in app.subheader)
