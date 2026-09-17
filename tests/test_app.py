"""Exercise the actual single-app widgets and their durable workspace state."""

import json
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = Path(__file__).parents[1] / "app/streamlit_app.py"


def open_app():
    app = AppTest.from_file(APP, default_timeout=30).run()
    assert not app.exception
    return app


def button(app, label):
    return next(item for item in app.button if item.label == label)


def payload(app):
    data = json.loads(app.get("bidi_component")[0].proto.json)
    assert all(isinstance(value, (str, int, float, bool, list))
               for value in data["diagnostics"].values())
    return data


def switch_view(app, view):
    app.pills(key="te_view").set_value(view).run()
    assert not app.exception


def test_fractional_policy_inputs_remain_visible_and_reach_the_run():
    app = open_app()
    settings = {
        "te_firm_reinvestment_rate_0": 12.3456,
        "te_firm_depreciation_rate_0": .1,
        "te_firm_reinvestment_rate_1": 1e-10,
    }
    for key, value in settings.items():
        app.number_input(key=key).set_value(value).run()
        widget = app.number_input(key=key)
        assert float(widget.proto.format % widget.value) == pytest.approx(value)
        assert float(widget.proto.format % widget.value) > 0
    button(app, "Start new simulation").click().run()
    assert not app.exception
    firms = payload(app)["reporting"]["firms"]
    assert firms[0]["parameters"]["reinvestment_rate"] == pytest.approx(.123456)
    assert firms[0]["parameters"]["depreciation_rate"] == pytest.approx(.001)
    assert firms[1]["parameters"]["reinvestment_rate"] == pytest.approx(1e-12, abs=0)
    switch_view(app, "Set up")
    for key, value in settings.items():
        assert app.number_input(key=key).value == pytest.approx(value)


def test_investment_policy_switches_preserve_inputs_and_submitted_run():
    app = open_app()
    policy_key = "te_firm_investment_policy_0"
    return_key = "te_firm_required_return_0"
    budget_key = "te_firm_reinvestment_rate_0"
    app.selectbox(key=policy_key).set_value("user_cost").run()
    app.number_input(key=return_key).set_value(17.125).run()
    app.number_input(key=budget_key).set_value(62.5).run()
    assert app.number_input(key=budget_key).label == "Maximum surplus invested %"
    assert app.session_state.te_firms[1]["investment_policy"] == "percentage"
    app.selectbox(key=policy_key).set_value("percentage").run()
    assert all(widget.key != return_key for widget in app.number_input)
    assert app.number_input(key=budget_key).value == 62.5
    assert app.session_state.te_firms[0]["required_return"] == pytest.approx(.17125)
    app.selectbox(key=policy_key).set_value("user_cost").run()
    assert app.number_input(key=return_key).value == 17.125
    switch_view(app, "Ask why")
    switch_view(app, "Set up")
    assert app.selectbox(key=policy_key).value == "user_cost"
    assert app.number_input(key=return_key).value == 17.125
    assert app.number_input(key=budget_key).value == 62.5
    button(app, "Start new simulation").click().run()
    assert not app.exception
    firm = payload(app)["reporting"]["firms"][0]
    assert firm["parameters"]["investment_policy"] == "user_cost"
    assert firm["parameters"]["required_return"] == pytest.approx(.17125)
    assert firm["parameters"]["reinvestment_rate"] == .625
    switch_view(app, "Set up")
    app.number_input(key=return_key).set_value(22.0).run()
    switch_view(app, "Results")
    button(app, "Next period →").click().run()
    assert not app.exception
    assert app.session_state.te_history[-1].firms[0].required_return == .17125
    switch_view(app, "Set up")
    button(app, "Start new simulation").click().run()
    assert not app.exception
    assert app.session_state.te_history[0].firms[0].required_return == .22


def test_draft_and_expansion_survive_navigation_and_run_uses_submitted_settings():
    app = open_app()
    app.session_state.te_open_household_0 = True
    app.session_state.te_expanded["household_0"] = True
    app.number_input(key="te_household_consumption_target_0").set_value(1.0).run()
    assert app.session_state.te_open_household_0 is True
    button(app, "Start new simulation").click().run()
    assert not app.exception
    assert payload(app)["reporting"]["households"][0]["parameters"]["consumption_target"] == 1
    switch_view(app, "Set up")
    assert app.session_state.te_open_household_0 is True
    app.number_input(key="te_household_consumption_target_0").set_value(.8).run()
    switch_view(app, "Results")
    assert any("Draft changed" in notice.value for notice in app.info)
    button(app, "Next period →").click().run()
    assert app.session_state.te_history[-1].households[0].consumption_target == 1
    switch_view(app, "Set up")
    assert app.number_input(key="te_household_consumption_target_0").value == .8
    button(app, "Start new simulation").click().run()
    assert len(app.session_state.te_history) == 1
    assert app.session_state.te_history[0].households[0].consumption_target == .8


def test_preset_requires_apply_and_preserves_results_and_baseline_until_start():
    app = open_app()
    button(app, "Start new simulation").click().run()
    first = app.session_state.te_history[0]
    button(app, "Save as baseline").click().run()
    baseline = app.session_state.te_baseline
    switch_view(app, "Set up")
    app.selectbox(key="te_preset_choice").set_value("fixed_capacity").run()
    assert app.session_state.te_households[0]["consumption_target"] == .5
    button(app, "Use this setup").click().run()
    assert not app.exception
    assert app.session_state.te_history == [first]
    assert app.session_state.te_baseline == baseline
    assert all(item["consumption_target"] == 0 for item in app.session_state.te_households)
    assert all(item["reinvestment_rate"] == item["depreciation_rate"] == 0
               for item in app.session_state.te_firms)
    button(app, "Start new simulation").click().run()
    assert payload(app)["comparison"] is not None
    button(app, "+10 periods").click().run()
    assert not app.exception
    assert len(app.session_state.te_history) == 11
    button(app, "Copy baseline setup").click().run()
    assert app.pills(key="te_view").value == "Set up"
    assert app.number_input(key="te_household_consumption_target_0").value == .5
    assert len(app.session_state.te_history) == 11
    assert app.session_state.te_baseline == baseline


def test_imported_names_are_literal_in_explanations_and_reset_clears_run(monkeypatch):
    from econ_agent_sim.ui_text import literal

    # Old deployment settings must not bring the retired chat UI back.
    monkeypatch.setenv("ECON_CHAT_ENABLED", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "unused-test-key")
    app = open_app()
    name = "![preview](https://example.com/image)"
    app.session_state.te_experiment_name = name
    app.session_state.te_firms[0]["name"] = name
    app.run()
    assert not app.exception
    assert any(literal(name) in item.value for item in app.caption)
    assert any(item.label == literal(name) for item in app.expander)
    button(app, "Start new simulation").click().run()
    switch_view(app, "Ask why")
    app.selectbox(key="te_explanation_question_topic").set_value(
        "Why does one firm sell more?"
    ).run()
    assert not app.exception
    assert any(name in item.value for item in app.text)
    assert not any(name in item.value for item in app.markdown)
    assert not app.chat_input
    assert not app.chat_message
    button(app, "Reset to default").click().run()
    assert not app.exception
    assert not app.session_state.te_history
    assert app.session_state.te_experiment_name == "My experiment"


def test_invalid_name_edit_preserves_run_and_baseline_then_recovers():
    app = open_app()
    button(app, "Start new simulation").click().run()
    button(app, "Save as baseline").click().run()
    history = tuple(app.session_state.te_history)
    baseline = app.session_state.te_baseline
    name = app.session_state.te_experiment_name
    app.text_input(key="te_name_input").set_value("Bad\tname").run()
    assert not app.exception
    assert any("Could not rename this experiment" in item.value for item in app.error)
    assert app.session_state.te_experiment_name == name
    assert app.text_input(key="te_name_input").value == name
    assert tuple(app.session_state.te_history) == history
    assert app.session_state.te_baseline == baseline
    app.text_input(key="te_name_input").set_value("Recovered experiment").run()
    assert not app.exception
    assert not app.error
    assert app.session_state.te_experiment_name == "Recovered experiment"
    assert tuple(app.session_state.te_history) == history
    assert app.session_state.te_baseline == baseline


def test_invalid_unicode_upload_shows_error_without_replacing_work(monkeypatch):
    from io import BytesIO

    import streamlit as st

    document = json.loads(
        (Path(__file__).parent / "fixtures/current_model_workspace.json").read_bytes()
    )
    document["current"]["draft"]["firms"][0]["name"] = "Bad\ud800name"
    uploaded = BytesIO(json.dumps(document).encode())

    # AppTest has no uploader driver; substitute the upload boundary and use
    # the app's real Open experiment button and callback for the entire restore.
    def file_uploader(*args, **kwargs):
        st.session_state[kwargs["key"]] = uploaded
        return uploaded

    monkeypatch.setattr(st, "file_uploader", file_uploader)
    app = open_app()
    button(app, "Start new simulation").click().run()
    button(app, "Save as baseline").click().run()
    history = tuple(app.session_state.te_history)
    baseline = app.session_state.te_baseline
    name = app.session_state.te_experiment_name
    button(app, "Open experiment").click().run()
    assert not app.exception
    assert any("valid Unicode text" in item.value for item in app.error)
    assert tuple(app.session_state.te_history) == history
    assert app.session_state.te_baseline == baseline
    assert app.session_state.te_experiment_name == name


def test_bulk_preferences_leave_money_and_submitted_settings_unchanged():
    app = open_app()
    app.number_input(key="te_count").set_value(3).run()
    app.number_input(key="te_household_money_1").set_value(2.0).run()
    app.number_input(key="te_household_consumption_target_0").set_value(1.2).run()
    app.number_input(key="te_household_consumption_priority_0").set_value(2.0).run()
    button(app, "Start new simulation").click().run()
    submitted = app.session_state.te_submitted
    switch_view(app, "Set up")
    button(app, "Copy preferences and target to all").click().run()
    assert not app.exception
    households = app.session_state.te_households
    assert all(item["consumption_target"] == 1.2 for item in households)
    assert all(item["consumption_priority"] == 2 for item in households)
    assert households[1]["money"] == 2
    assert app.session_state.te_submitted == submitted
    assert submitted[0][1].consumption_target == .5
    assert app.number_input(key="te_household_consumption_target_2").value == 1.2


def test_cumulative_navigation_and_reset_keep_explicit_baseline():
    app = open_app()
    switch_view(app, "Results")
    button(app, "Go to set up").click().run()
    assert app.pills(key="te_view").value == "Set up"
    app.number_input(key="te_household_consumption_target_0").set_value(1.0).run()
    button(app, "Start new simulation").click().run()
    button(app, "+10 periods").click().run()
    app.pills(key="te_report_scope").set_value("Cumulative").run()
    report = payload(app)["reporting"]
    assert report["scope"] == "cumulative"
    assert report["economy"]["needed_x"] == pytest.approx(16.5)
    app.session_state.te_selected_firm = "firm_b"
    switch_view(app, "Ask why")
    app.selectbox(key="te_explanation_question_topic").set_value(
        "How are target gaps counted?"
    ).run()
    assert any("Periods 1–11" in item.value for item in app.text)
    app.selectbox(key="te_selected").set_value(3).run()
    assert any("Periods 1–3" in item.value for item in app.text)
    app.pills(key="te_report_scope").set_value("This period").run()
    assert any("Period 3" in item.value for item in app.text)
    app.pills(key="te_report_scope").set_value("Cumulative").run()
    app.selectbox(key="te_selected").set_value(11).run()
    switch_view(app, "Results")
    assert app.pills(key="te_report_scope").value == "Cumulative"
    assert payload(app)["selected_firm"] == "firm_b"
    button(app, "Save as baseline").click().run()
    baseline = app.session_state.te_baseline
    comparison = payload(app)["comparison"]
    switch_view(app, "Ask why")
    app.selectbox(key="te_explanation_question_topic").set_value(
        "How should I read the baseline comparison?"
    ).run()
    assert any(comparison["note"] in item.value for item in app.text)
    button(app, "Next period →").click().run()
    assert any("Both experiments need Period 12" in item.value for item in app.text)
    button(app, "Reset to default").click().run()
    assert not app.exception
    assert not app.session_state.te_history
    assert app.session_state.te_baseline == baseline
    assert app.number_input(key="te_household_consumption_target_0").value == .5
