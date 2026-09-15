"""Protect target editing, submitted settings and the real component payload."""

import json
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = Path(__file__).parents[1] / "app/streamlit_app.py"


def open_app():
    app = AppTest.from_file(APP, default_timeout=30).run()
    return app.switch_page("pages/12_Economy_1_1_Consumption_Targets.py").run()


def button(app, label):
    return next(item for item in app.button if item.label == label)


def payload(app):
    result = json.loads(app.get("bidi_component")[0].proto.json)
    assert isinstance(result, dict)
    assert result["reporting"]["model"] == "consumption_target"
    assert all(isinstance(value, (str, int, float, bool))
               for value in result["diagnostics"].values())
    return result


def test_target_controls_and_expansion_survive_navigation():
    app = open_app()
    target = app.number_input(key="tg_household_consumption_target_0")
    assert target.value == .5
    assert target.step == .1
    assert target.min == 0
    app.session_state.tg_open_household_0 = True
    app.session_state.tg_expanded["household_0"] = True
    target.set_value(1.0).run()
    assert app.session_state.tg_open_household_0 is True
    button(app, "Start new simulation").click().run()
    assert not app.exception
    first = app.session_state.tg_history[0]
    assert first.households[0].consumption_target == 1.0
    parameters = payload(app)["reporting"]["households"][0]["parameters"]
    assert parameters["consumption_target"] == 1.0
    assert parameters["weights"]["consumption"] == pytest.approx(1 / 3)
    app.session_state.tg_view = "Set up"
    app.run()
    assert app.session_state.tg_open_household_0 is True
    app.number_input(key="tg_household_consumption_target_0").set_value(.8).run()
    app.session_state.tg_view = "Results"
    app.run()
    button(app, "Next period →").click().run()
    assert app.session_state.tg_history[-1].households[0].consumption_target == 1.0
    app.session_state.tg_view = "Set up"
    app.run()
    assert app.number_input(key="tg_household_consumption_target_0").value == .8
    button(app, "Start new simulation").click().run()
    assert len(app.session_state.tg_history) == 1
    assert app.session_state.tg_history[0].households[0].consumption_target == .8


def test_cumulative_target_report_and_navigation_preserve_state():
    app = open_app()
    app.number_input(key="tg_household_consumption_target_0").set_value(1.0).run()
    button(app, "Start new simulation").click().run()
    button(app, "+10 periods").click().run()
    assert not app.exception
    assert len(app.session_state.tg_history) == 11
    app.pills(key="tg_report_scope").set_value("Cumulative").run()
    report = payload(app)["reporting"]
    assert report["scope"] == "cumulative"
    assert report["economy"]["needed_x"] == 16.5
    assert report["households"][0]["needed_x"] == 11
    app.session_state.tg_selected_firm = "firm_b"
    app.run()
    assert payload(app)["selected_firm"] == "firm_b"
    app.session_state.tg_view = "Ask why"
    app.run()
    assert not app.exception
    assert any(item.label == "Explore a question" for item in app.selectbox)
    app.session_state.tg_view = "Results"
    app.run()
    assert app.pills(key="tg_report_scope").value == "Cumulative"
    assert payload(app)["selected_firm"] == "firm_b"


def test_target_off_and_reset_preserve_the_other_chapter():
    app = open_app()
    for index in range(2):
        app.number_input(key=f"tg_household_consumption_target_{index}").set_value(0).run()
    app.session_state.cg_marker = "keep Economy 1.0"
    button(app, "Start new simulation").click().run()
    report = payload(app)["reporting"]
    assert report["economy"]["needed_x"] == 0
    assert report["economy"]["shortfall_x"] == 0
    assert report["economy"]["target_coverage"] is None
    button(app, "Reset").click().run()
    assert not app.exception
    assert not app.session_state.tg_history
    assert app.number_input(key="tg_household_consumption_target_0").value == .5
    assert app.session_state.cg_marker == "keep Economy 1.0"
