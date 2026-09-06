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
    assert any(item.value == "Money settles the trade" for item in app.title)
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


def test_economy_0_4_settlement_and_audit_hide_overview_controls() -> None:
    app = open_economy_0_4()

    for view in ("Settlement", "Audit"):
        app.session_state["economy04_view_picker"] = view
        app.run(timeout=10)

        assert not app.exception
        assert any(item.value == view for item in app.subheader)
        assert "Settings" not in expander_labels(app)
        assert "Add a redistribution" not in expander_labels(app)
        assert "Model boundary" not in expander_labels(app)


def test_economy_0_4_audit_exposes_money_stock_flow_and_ledger() -> None:
    app = open_economy_0_4()
    app.session_state["economy04_view_picker"] = "Audit"
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
    for view in ("Audit", "Settlement", "Overview"):
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
    next(item for item in app.button if item.label == "Clear redistributions").click()
    app.run(timeout=10)
    assert len(app.session_state["economy04_period_populations"]) == 1
    assert app.session_state["economy04_opening_money"] == 20
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
