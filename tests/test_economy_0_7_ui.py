"""Exercise submitted work settings, period navigation and failure recovery."""

from pathlib import Path
from unittest.mock import patch

import pytest
from streamlit.testing.v1 import AppTest

APP = Path(__file__).parents[1] / "app/streamlit_app.py"


def open_app():
    app = AppTest.from_file(APP, default_timeout=10).run()
    return app.switch_page("pages/8_Economy_0_7_Work_and_Leisure.py").run()


def button(app, label):
    return next(item for item in app.button if item.label == label)


def test_work_draft_navigation_history_and_restart():
    app = open_app()
    assert not app.exception
    assert not app.session_state.work_history
    assert app.number_input(key="work_leisure_0").value == 1 / 3
    button(app, "Start new simulation").click().run()
    assert not app.exception
    first = app.session_state.work_history[0]
    assert first.market.prices["X"] == pytest.approx(1)
    assert first.effort["Agent 1"] == pytest.approx(.5)
    assert first.closing_stocks["Agent 1"]["X"] == 0
    app.session_state.work_view = "Set up"
    app.run()
    app.number_input(key="work_productivity_0").set_value(3.0).run()
    app.number_input(key="work_leisure_0").set_value(.6).run()
    app.session_state.work_view = "Results"
    app.run()
    button(app, "Next period").click().run()
    second = app.session_state.work_history[1]
    assert second.opening_stocks == first.closing_stocks
    assert second.population[0].productivity == 2
    assert second.population[0].leisure == 1 / 3
    app.selectbox(key="work_selected").set_value(1).run()
    button(app, "Next period").click().run()
    history = app.session_state.work_history
    assert [period.number for period in history] == [1, 2, 3]
    assert history[2].opening_stocks == second.closing_stocks
    assert app.session_state.work_selected == 3
    app.selectbox(key="work_selected").set_value(1).run()
    app.session_state.work_view = "Set up"
    app.run()
    assert app.number_input(key="work_productivity_0").value == 3
    assert app.number_input(key="work_leisure_0").value == .6
    app.session_state.work_view = "Results"
    app.run()
    assert app.selectbox(key="work_selected").value == 1
    app.session_state.work_view = "Set up"
    app.run()
    button(app, "Start new simulation").click().run()
    assert not app.exception
    assert len(app.session_state.work_history) == 1
    assert app.session_state.work_history[0].population[0].productivity == 3
    assert app.session_state.work_history[0].population[0].leisure == .6


def test_work_failed_start_next_and_reset_preserve_other_economies():
    app = open_app()
    button(app, "Start new simulation").click().run()
    original = app.session_state.work_history
    generation = app.session_state.work_generation
    with patch("econ_agent_sim.economy_0_7.advance_work_period", side_effect=ValueError("Test failure")):
        app.run()
        button(app, "Next period").click().run()
    assert app.error
    assert app.session_state.work_history == original
    app.session_state.work_view = "Set up"
    app.run()
    for i in range(2):
        app.number_input(key=f"work_money_{i}").set_value(0.0).run()
    button(app, "Start new simulation").click().run()
    assert not app.exception
    assert app.error
    assert app.session_state.work_history == original
    assert app.session_state.work_generation == generation
    app.session_state.prod_user_marker = "preserve other economy"
    button(app, "Reset").click().run()
    assert not app.exception
    assert not app.session_state.work_history
    assert app.session_state.work_submitted is None
    assert app.session_state.work_generation > generation
    assert app.number_input(key="work_money_0").value == 1
    assert app.number_input(key="work_x_0").value == 0
    assert app.number_input(key="work_productivity_0").value == 2
    assert app.number_input(key="work_leisure_0").value == 1 / 3
    assert app.session_state.prod_user_marker == "preserve other economy"


def test_work_resize_chat_and_history_limit():
    app = open_app()
    app.number_input(key="work_leisure_0").set_value(.6).run()
    app.number_input(key="work_count").set_value(3).run()
    assert app.number_input(key="work_leisure_0").value == .6
    assert app.number_input(key="work_leisure_2").value == 1 / 3
    app.number_input(key="work_count").set_value(2).run()
    assert len(app.session_state.work_agents) == 2
    button(app, "Start new simulation").click().run()
    app.session_state.work_view = "Ask why"
    app.run()
    assert not app.exception
    first_context = app.session_state.economy04_chat_context
    button(app, "Next period").click().run()
    assert not app.exception
    app.selectbox(key="work_selected").set_value(1).run()
    assert app.session_state.economy04_chat_context == first_context
    app.session_state.work_view = "Results"
    app.run()
    app.pills(key="work_report_scope").set_value("Cumulative").run()
    assert app.session_state.work_report_scope == "Cumulative"
    assert any("Cumulative from Period 1 through Period 1" in item.value
               for item in app.caption)
    app.session_state.work_history = [app.session_state.work_history[0]] * 100
    app.run()
    assert button(app, "Next period").disabled
