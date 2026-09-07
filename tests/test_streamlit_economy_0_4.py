from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

APP_ENTRYPOINT = Path(__file__).parents[1] / "app" / "streamlit_app.py"
PAGE = "pages/5_Economy_0_4_Monetary_Settlement.py"


def open_app():
    return AppTest.from_file(APP_ENTRYPOINT, default_timeout=10).run().switch_page(PAGE).run()


def button(app, label):
    return next(b for b in app.button if b.label == label)


def go(app, view):
    app.session_state.lab_view = view
    return app.run()


def test_start_requires_explicit_run_and_has_symmetric_no_trade_result():
    app = open_app()
    assert not app.exception
    assert app.session_state.lab_result is None
    assert app.session_state.lab_agents == [
        {"name": "Agent 1", "x": 1.0, "y": 1.0, "alpha": .5},
        {"name": "Agent 2", "x": 1.0, "y": 1.0, "alpha": .5},
    ]
    go(app, "Results")
    assert any("No run yet" in i.value for i in app.info)
    go(app, "Set up")
    button(app, "Run").click().run()
    assert not app.exception
    assert app.session_state.lab_view == "Results"
    assert app.session_state.lab_result.trades == ()
    assert app.session_state.lab_result.periods[0].prices["X"] == 1
    assert app.session_state.lab_previous is None


def test_preference_steppers_and_complete_starting_totals():
    app = open_app()
    assert not app.slider
    assert "Money and model details" not in {e.label for e in app.expander}
    assert {"Agents · 2", "X · 2", "Y · 2", "Money · 20"} <= {m.value for m in app.markdown}
    app.number_input(key="lab_count").set_value(3).run()
    app.number_input(key="lab_x_0").set_value(2.0).run()
    app.number_input(key="lab_y_1").set_value(3.0).run()
    app.number_input(key="lab_money_input").set_value(12.0).run()
    app.number_input(key="lab_alpha_0").set_value(.51).run()
    assert not app.exception
    assert {"Agents · 3", "X · 4", "Y · 5", "Money · 36"} <= {m.value for m in app.markdown}
    assert any("51% X · 49% Y" in m.value for m in app.caption)
    assert app.session_state.lab_result is None
    summaries = {expander.label for expander in app.expander}
    assert "Agent 1 · 2 X · 1 Y · 51% X · 49% Y" in summaries
    assert "Agent 2 · 1 X · 3 Y · equal preferences" in summaries
    button(app, "Run").click().run()
    assert app.session_state.lab_result.config.opening_money_per_agent == 12
    go(app, "Set up")
    assert app.number_input(key="lab_money_input").value == 12
    assert app.number_input(key="lab_alpha_0").value == .51
    assert {"Agents · 3", "X · 4", "Y · 5", "Money · 36"} <= {m.value for m in app.markdown}


def test_draft_edits_leave_result_and_chat_context_unchanged_until_run():
    app = open_app()
    button(app, "Run").click().run()
    original = app.session_state.lab_result
    go(app, "Set up")
    app.number_input(key="lab_x_0").set_value(2.0).run()
    app.number_input(key="lab_alpha_0").set_value(.8).run()
    assert app.session_state.lab_result == original
    go(app, "Ask why")
    assert any("Setup changed" in i.value for i in app.info)
    go(app, "Set up")
    assert app.number_input(key="lab_x_0").value == 2
    assert app.number_input(key="lab_alpha_0").value == .8
    button(app, "Run").click().run()
    assert not app.exception
    assert app.session_state.lab_previous == original
    assert app.session_state.lab_number == 2
    assert app.session_state.lab_result.periods[0].population[0].alpha == .8
    assert any("spending share on X" in m.value for m in app.markdown)


def test_population_changes_are_independent_and_inputs_survive_navigation():
    app = open_app()
    button(app, "Run").click().run()
    go(app, "Set up")
    app.number_input(key="lab_count").set_value(3).run()
    app.number_input(key="lab_y_2").set_value(2.0).run()
    go(app, "Results")
    assert len(app.session_state.lab_result.periods[0].population) == 2
    go(app, "Set up")
    assert app.number_input(key="lab_count").value == 3
    assert app.number_input(key="lab_y_2").value == 2
    button(app, "Run").click().run()
    assert not app.exception
    assert len(app.session_state.lab_result.periods[0].population) == 3
    assert any("Agent 3 added" in m.value for m in app.markdown)
    go(app, "Set up")
    app.number_input(key="lab_count").set_value(2).run()
    button(app, "Run").click().run()
    assert any("Agent 3 removed" in m.value for m in app.markdown)


def test_failed_run_keeps_both_snapshots_and_reset_has_one_meaning():
    app = open_app()
    button(app, "Run").click().run()
    original = app.session_state.lab_result
    go(app, "Set up")
    app.number_input(key="lab_x_0").set_value(0.0).run()
    app.number_input(key="lab_x_1").set_value(0.0).run()
    button(app, "Run").click().run()
    assert not app.exception
    assert any("positive total" in e.value for e in app.error)
    assert app.session_state.lab_result == original
    assert app.session_state.lab_number == 1
    button(app, "Reset").click().run()
    assert not app.exception
    assert app.session_state.lab_result is None
    assert app.session_state.lab_previous is None
    assert app.session_state.lab_number == 0
    assert app.number_input(key="lab_x_0").value == 1
    assert app.number_input(key="lab_alpha_0").value == .5


def test_builtin_explanations_do_not_use_ai():
    with patch("econ_agent_sim.chat_view.chat_setting", return_value=""), patch("econ_agent_sim.chat_view.answer_question") as answer:
        app = open_app()
        button(app, "Run").click().run()
        go(app, "Ask why")
        assert not app.exception
        assert app.chat_input[0].disabled
        assert "Why is there no trade?" in {e.label for e in app.expander}
        assert any("each agent already holds their desired bundle" in m.value for m in app.markdown)
        assert "Why did the price move?" in {e.label for e in app.expander}
        answer.assert_not_called()


def test_chat_receives_submitted_run_and_previous_run_only():
    def settings(name, default=""):
        return {"OPENAI_API_KEY": "fake", "ECON_CHAT_ENABLED": "true"}.get(name, default)
    with patch("econ_agent_sim.chat_view.chat_setting", side_effect=settings), patch("econ_agent_sim.chat_view.answer_question", return_value="A model explanation.") as answer:
        app = open_app()
        button(app, "Run").click().run()
        go(app, "Set up")
        app.number_input(key="lab_alpha_0").set_value(.8).run()
        button(app, "Run").click().run()
        go(app, "Set up")
        app.number_input(key="lab_x_0").set_value(9.0).run()
        go(app, "Ask why")
        app.chat_input[0].set_value("What changed?").run()
        assert not app.exception
        context = answer.call_args.args[1]
        assert context["label"] == "Run 2"
        assert context["agents"][0]["opening"]["X"] == 1
        assert context["agents"][0]["alpha"] == .8
        assert context["previous_run"]["agents"][0]["alpha"] == .5
        go(app, "Results")
        go(app, "Ask why")
        assert len(app.session_state.economy04_chat_messages) == 2
        assert answer.call_count == 1


def test_trade_questions_are_selected_in_ask_why():
    app = open_app()
    app.number_input(key="lab_alpha_0").set_value(.8).run()
    button(app, "Run").click().run()
    go(app, "Ask why")
    assert app.selectbox[0].options[0] == "Whole run"
    assert any(option.startswith("Trade 1 of") for option in app.selectbox[0].options)
    app.selectbox[0].select_index(1).run()
    assert app.session_state.economy04_chat_trade == 0
    assert "Explain this trade" in {expander.label for expander in app.expander}
    assert "How was the price found?" in {expander.label for expander in app.expander}
