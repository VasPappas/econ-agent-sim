from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

APP_ENTRYPOINT = Path(__file__).parents[1] / "app" / "streamlit_app.py"
ECONOMY_04_PAGE = "pages/5_Economy_0_4_Monetary_Settlement.py"


def open_economy_0_4() -> AppTest:
    app = AppTest.from_file(APP_ENTRYPOINT, default_timeout=10).run()
    return app.switch_page(ECONOMY_04_PAGE).run(timeout=10)


def expander_labels(app: AppTest) -> set[str]:
    return {item.label for item in app.expander}


def test_economy_0_4_opens_on_monetary_overview() -> None:
    app = open_economy_0_4()

    assert not app.exception
    assert app.session_state["economy04_view_picker"] == "Experiment"
    assert any(item.value == "What changed in 0.4?" for item in app.subheader)
    assert {"Settings", "Add a redistribution", "Model boundary"} <= expander_labels(
        app
    )
    assert app.session_state["economy04_revision"] == 0


def test_economy_0_4_can_apply_even_agent_count() -> None:
    app = open_economy_0_4()

    agent_count = next(
        item for item in app.number_input if item.label == "Number of agents"
    )
    agent_count.set_value(2)
    apply_button = next(item for item in app.button if item.label == "Apply and close")
    apply_button.click()
    app.run(timeout=10)

    assert not app.exception
    assert app.session_state["economy04_agent_count"] == 2
    assert len(app.session_state["economy04_period_populations"][0]) == 2
    assert app.session_state["economy04_revision"] == 1

    assert any("2 agents · 2 X and 2 Y" in item.value for item in app.markdown)
    assert "Meet the agents at baseline" in expander_labels(app)
    assert next(b for b in app.button if b.label == "Reset to baseline").disabled


def test_economy_0_4_settlement_and_audit_hide_overview_controls() -> None:
    app = open_economy_0_4()

    for view in ("Results", "Results"):
        app.session_state["economy04_view_picker"] = view
        app.run(timeout=10)

        assert not app.exception
        assert "Inspect the evidence" in expander_labels(app)
        assert "Settings" not in expander_labels(app)
        assert "Add a redistribution" not in expander_labels(app)
        assert "Model boundary" not in expander_labels(app)


def test_economy_0_4_audit_exposes_money_stock_flow_and_ledger() -> None:
    app = open_economy_0_4()
    app.session_state["economy04_view_picker"] = "Results"
    app.run(timeout=10)

    assert not app.exception
    labels = expander_labels(app)
    assert "Agent decisions" in labels
    assert "Stock-flow accounts" in labels
    assert "Settlement ledger" in labels
    assert "Price-discovery iterations" in labels


def test_settings_survive_hidden_views_and_page_navigation() -> None:
    app = open_economy_0_4()
    next(
        item for item in app.number_input if item.label == "Opening money per agent"
    ).set_value(20)
    next(item for item in app.button if item.label == "Apply and close").click()
    app.run(timeout=10)
    for view in ("Results", "Results", "Experiment"):
        app.session_state["economy04_view_picker"] = view
        app.run(timeout=10)
    assert not app.exception
    assert app.session_state["economy04_opening_money"] == 20
    assert (
        next(
            item for item in app.number_input if item.label == "Opening money per agent"
        ).value
        == 20
    )
    app.switch_page("streamlit_app.py").run()
    app.switch_page(ECONOMY_04_PAGE).run(timeout=10)
    assert not app.exception
    assert (
        next(
            item for item in app.number_input if item.label == "Opening money per agent"
        ).value
        == 20
    )


def test_native_transfer_and_reset_have_distinct_semantics() -> None:
    app = open_economy_0_4()
    next(
        item for item in app.number_input if item.label == "Opening money per agent"
    ).set_value(20)
    next(item for item in app.button if item.label == "Apply and close").click()
    app.run(timeout=10)
    next(item for item in app.button if item.label == "Add as next period").click()
    app.run(timeout=10)
    assert len(app.session_state["economy04_period_populations"]) == 2
    app.session_state["economy04_view_picker"] = "Experiment"
    app.run()
    next(item for item in app.button if item.label == "Reset to baseline").click()
    app.run(timeout=10)
    assert len(app.session_state["economy04_period_populations"]) == 1
    assert app.session_state["economy04_opening_money"] == 20
    assert app.session_state["economy04_period_picker"] == "Baseline"
    assert app.session_state["economy04_view_picker"] == "Experiment"
    assert any("Back at baseline" in item.value for item in app.success)
    next(
        item for item in app.button if item.label == "Restore default settings"
    ).click()
    app.run(timeout=10)
    assert not app.exception
    assert app.session_state["economy04_opening_money"] == 10
    assert (
        next(
            item for item in app.number_input if item.label == "Opening money per agent"
        ).value
        == 10
    )


def test_component_actions_are_processed_once_and_stale_actions_are_rejected() -> None:
    app = open_economy_0_4()
    action = {
        "id": "first",
        "kind": "redistribute",
        "revision": 0,
        "sender": "Agent 1",
        "receiver": "Agent 2",
        "amount": 0.1,
    }
    with patch(
        "econ_agent_sim.playground_component.render_playground",
        return_value=SimpleNamespace(action=action),
    ):
        app.run(timeout=10)
        app.run(timeout=10)
    assert not app.exception
    assert len(app.session_state["economy04_period_populations"]) == 2
    assert app.session_state["economy04_revision"] == 1
    action = {**action, "id": "stale"}
    with patch(
        "econ_agent_sim.playground_component.render_playground",
        return_value=SimpleNamespace(action=action),
    ):
        app.run(timeout=10)
    assert not app.exception
    assert len(app.session_state["economy04_period_populations"]) == 2
    assert "experiment changed" in app.session_state["economy04_error"]


def test_chat_without_key_is_disabled_and_preserves_the_economy():
    with patch("econ_agent_sim.chat_view.chat_setting", return_value=""):
        app = open_economy_0_4()
        app.session_state["economy04_view_picker"] = "Ask why"
        app.run()
        assert not app.exception
        assert app.chat_input[0].disabled
        assert any("not connected" in item.value for item in app.info)
        assert len(app.session_state["economy04_period_populations"]) == 1


def test_builtin_explanations_work_without_an_api_key_or_request():
    with (
        patch("econ_agent_sim.chat_view.chat_setting", return_value=""),
        patch("econ_agent_sim.chat_view.answer_question") as answer,
    ):
        app = open_economy_0_4()
        app.session_state["economy04_view_picker"] = "Ask why"
        app.run()
        assert not app.exception
        assert "Why did X change but not Y?" in expander_labels(app)
        assert "Was any money created?" in expander_labels(app)
        assert any("100.0000 Money" in item.value for item in app.markdown)
        answer.assert_not_called()


def test_return_from_chat_restores_the_selected_trade():
    app = open_economy_0_4()
    event = {"id": "trade-six", "revision": 0, "selected_index": 0, "trade_index": 5}
    with patch(
        "econ_agent_sim.playground_component.render_playground",
        return_value=SimpleNamespace(action=None, question=event),
    ):
        app.run()
    next(b for b in app.button if b.label == "← Back to results").click()
    with patch(
        "econ_agent_sim.playground_component.render_playground",
        return_value=SimpleNamespace(action=None),
    ) as component:
        app.run()
    assert not app.exception
    assert app.session_state["economy04_view_picker"] == "Results"
    assert component.call_args.args[0]["selected_trade"] == 5
    app.session_state["economy04_view_picker"] = "Ask why"
    app.run()
    assert next(s for s in app.selectbox if s.label == "Focus").value == 5


def test_component_navigation_is_validated_and_does_not_change_model():
    app = open_economy_0_4()
    event = {"id": "results", "revision": 0, "selected_index": 0, "view": "Results"}
    with patch(
        "econ_agent_sim.playground_component.render_playground",
        return_value=SimpleNamespace(action=None, navigation=event),
    ):
        app.run()
    assert not app.exception
    assert app.session_state["economy04_view_picker"] == "Results"
    assert app.session_state["economy04_revision"] == 0
    event = {**event, "id": "stale", "revision": -1, "view": "Experiment"}
    with patch(
        "econ_agent_sim.playground_component.render_playground",
        return_value=SimpleNamespace(action=None, navigation=event),
    ):
        app.run()
    assert app.session_state["economy04_view_picker"] == "Results"


def test_viewing_history_does_not_reset_and_reset_works_from_results():
    app = open_economy_0_4()
    next(b for b in app.button if b.label == "Add as next period").click().run()
    assert app.session_state["economy04_view_picker"] == "Results"
    next(s for s in app.selectbox if s.label == "Your experiments").set_value("Baseline").run()
    assert any("Viewing a past experiment" in i.value for i in app.info)
    assert len(app.session_state["economy04_period_populations"]) == 2
    next(b for b in app.button if b.label == "Reset to baseline").click().run()
    assert not app.exception
    assert app.session_state["economy04_view_picker"] == "Experiment"
    assert len(app.session_state["economy04_period_populations"]) == 1
    assert app.session_state["economy04_period_picker"] == "Baseline"


def enabled_settings(name, default=""):
    return {"OPENAI_API_KEY": "fake-key", "ECON_CHAT_ENABLED": "true"}.get(
        name, default
    )


def test_chat_followups_stay_in_session_and_context_changes_reset_history():
    with (
        patch("econ_agent_sim.chat_view.chat_setting", side_effect=enabled_settings),
        patch(
            "econ_agent_sim.chat_view.answer_question", return_value="Y is fixed at 1."
        ) as answer,
    ):
        app = open_economy_0_4()
        app.session_state["economy04_view_picker"] = "Ask why"
        app.run()
        app.chat_input[0].set_value("Why is Y fixed?").run()
        assert not app.exception
        assert len(app.session_state["economy04_chat_messages"]) == 2
        app.run()
        assert answer.call_count == 1
        app.chat_input[0].set_value("What about X?").run()
        assert answer.call_count == 2
        assert len(app.session_state["economy04_chat_messages"]) == 4
        next(s for s in app.selectbox if s.label == "Focus").set_value(0).run()
        assert app.session_state["economy04_chat_messages"] == []
        next(s for s in app.selectbox if s.label == "Focus").set_value(-1).run()
        assert len(app.session_state["economy04_chat_messages"]) == 4
        app.session_state["economy04_view_picker"] = "Experiment"
        app.run()
        assert not app.exception
        assert app.session_state["economy04_revision"] == 0


def test_component_can_open_chat_about_the_actual_selected_trade():
    app = open_economy_0_4()
    event = {"id": "ask-one", "revision": 0, "selected_index": 0, "trade_index": 5}
    with patch(
        "econ_agent_sim.playground_component.render_playground",
        return_value=SimpleNamespace(action=None, question=event),
    ):
        app.run()
    assert not app.exception
    assert app.session_state["economy04_view_picker"] == "Ask why"
    assert next(s for s in app.selectbox if s.label == "Focus").value == 5


def test_chat_failure_does_not_pollute_history_or_change_simulation():
    from econ_agent_sim.experiment_chat import ChatUnavailable

    with (
        patch("econ_agent_sim.chat_view.chat_setting", side_effect=enabled_settings),
        patch(
            "econ_agent_sim.chat_view.answer_question",
            side_effect=ChatUnavailable("The assistant is busy."),
        ),
    ):
        app = open_economy_0_4()
        app.session_state["economy04_view_picker"] = "Ask why"
        app.run()
        app.chat_input[0].set_value("Explain").run()
        assert not app.exception
        assert app.session_state["economy04_chat_messages"] == []
        assert app.session_state["economy04_revision"] == 0
        assert any("busy" in w.value for w in app.warning)
