from pathlib import Path

from streamlit.testing.v1 import AppTest

APP_ENTRYPOINT = Path(__file__).parents[1] / "app" / "streamlit_app.py"
ECONOMY_04_PAGE = "pages/5_Economy_0_4_Monetary_Settlement.py"


def open_economy_0_4() -> AppTest:
    app = AppTest.from_file(APP_ENTRYPOINT, default_timeout=10).run()
    return app.switch_page(ECONOMY_04_PAGE).run(timeout=10)


def expander_labels(app: AppTest) -> set[str]:
    return {item.label for item in app.expander}


def has_selected_result(app: AppTest) -> bool:
    return any(item.value == "SELECTED RESULT" for item in app.caption)


def test_economy_0_4_opens_on_monetary_overview() -> None:
    app = open_economy_0_4()

    assert not app.exception
    assert any(item.value == "Money settles the trade" for item in app.title)
    assert any(item.value == "What changed in 0.4?" for item in app.subheader)
    assert {"Settings", "Add a redistribution", "Model boundary"} <= expander_labels(app)
    assert has_selected_result(app)


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
        assert not has_selected_result(app)


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
