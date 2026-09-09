from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

APP = Path(__file__).parents[1] / "app/streamlit_app.py"


def open_app():
    app = AppTest.from_file(APP, default_timeout=10).run()
    return app.switch_page("pages/7_Economy_0_6_Production_and_Consumption.py").run()


def button(app, label):
    return next(item for item in app.button if item.label == label)


def test_production_draft_navigation_history_and_nonbranching():
    app = open_app()
    assert not app.exception
    assert not app.session_state.prod_history
    button(app, "Start new simulation").click().run()
    assert not app.exception
    first = app.session_state.prod_history[0]
    assert first.market.prices["X"] == 1
    assert first.closing_stocks["Agent 1"]["X"] == 0
    app.session_state.prod_view = "Set up"
    app.run()
    app.number_input(key="prod_production_0").set_value(2.0).run()
    app.session_state.prod_view = "Results"
    app.run()
    button(app, "Next period").click().run()
    second = app.session_state.prod_history[1]
    assert second.opening_stocks == first.closing_stocks
    assert second.produced["Agent 1"] == 1
    assert second.market.prices["X"] == 1
    app.selectbox(key="prod_selected").set_value(1).run()
    button(app, "Next period").click().run()
    history = app.session_state.prod_history
    assert [period.number for period in history] == [1, 2, 3]
    assert history[2].opening_stocks == second.closing_stocks
    assert app.session_state.prod_selected == 3
    app.selectbox(key="prod_selected").set_value(1).run()
    app.session_state.prod_view = "Set up"
    app.run()
    assert app.number_input(key="prod_production_0").value == 2
    app.session_state.prod_view = "Results"
    app.run()
    assert app.selectbox(key="prod_selected").value == 1
    app.session_state.prod_view = "Set up"
    app.run()
    button(app, "Start new simulation").click().run()
    assert len(app.session_state.prod_history) == 1
    assert app.session_state.prod_history[0].produced["Agent 1"] == 2


def test_production_failed_start_next_and_reset_are_atomic():
    app = open_app()
    button(app, "Start new simulation").click().run()
    original = app.session_state.prod_history
    generation = app.session_state.prod_generation
    with patch("econ_agent_sim.economy_0_6.advance_period", side_effect=ValueError("Test failure")):
        # Rerun imports the patched function before the callback uses it.
        app.run()
        button(app, "Next period").click().run()
    assert app.error
    assert app.session_state.prod_history == original
    app.session_state.prod_view = "Set up"
    app.run()
    for i in range(2):
        app.number_input(key=f"prod_money_{i}").set_value(0.0).run()
    button(app, "Start new simulation").click().run()
    assert not app.exception
    assert app.error
    assert app.session_state.prod_history == original
    assert app.session_state.prod_generation == generation
    app.session_state.cash_user_marker = "preserve other economy"
    button(app, "Reset").click().run()
    assert not app.exception
    assert not app.session_state.prod_history
    assert app.session_state.prod_submitted is None
    assert app.session_state.prod_generation > generation
    assert app.number_input(key="prod_money_0").value == 1
    assert app.number_input(key="prod_x_0").value == 0
    assert app.number_input(key="prod_production_0").value == 1
    assert app.session_state.cash_user_marker == "preserve other economy"


def test_production_resize_chat_and_history_limit():
    app = open_app()
    app.number_input(key="prod_production_0").set_value(2.0).run()
    app.number_input(key="prod_count").set_value(3).run()
    assert app.number_input(key="prod_production_0").value == 2
    assert app.number_input(key="prod_production_2").value == 1
    app.number_input(key="prod_count").set_value(2).run()
    assert len(app.session_state.prod_agents) == 2
    button(app, "Start new simulation").click().run()
    app.session_state.prod_view = "Ask why"
    app.run()
    assert not app.exception
    first_context = app.session_state.economy04_chat_context
    button(app, "Next period").click().run()
    assert not app.exception
    app.selectbox(key="prod_selected").set_value(1).run()
    assert app.session_state.economy04_chat_context == first_context
    app.session_state.prod_history = [app.session_state.prod_history[0]] * 100
    app.session_state.prod_view = "Results"
    app.run()
    assert button(app, "Next period").disabled
