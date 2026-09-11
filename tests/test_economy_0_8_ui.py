"""Exercise Economy 0.8 setup, linked periods and report controls."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = Path(__file__).parents[1] / "app/streamlit_app.py"


def open_app():
    app = AppTest.from_file(APP, default_timeout=10).run()
    return app.switch_page("pages/9_Economy_0_8_Firms_and_Wages.py").run()


def button(app, label):
    return next(item for item in app.button if item.label == label)


def test_baseline_setup_start_and_linked_periods():
    app = open_app()
    assert not app.exception
    assert [item.label for item in app.expander] == ["Household 1", "Household 2", "Firm"]
    assert app.number_input(key="fw_household_money_0").value == 1
    assert app.number_input(key="fw_household_consumption_priority_0").value == 1
    assert app.number_input(key="fw_household_money_priority_0").value == 1
    assert app.number_input(key="fw_household_leisure_priority_0").value == 1
    assert app.number_input(key="fw_firm_money").value == 1
    assert app.number_input(key="fw_firm_productivity").value == 2

    button(app, "Start new simulation").click().run()
    assert not app.exception
    first = app.session_state.fw_history[0]
    assert first.price == pytest.approx((2 / 3) ** .5)
    assert first.wage == pytest.approx(1)
    assert first.work["Household 1"] == pytest.approx(1 / 3)
    assert first.dividends["Household 1"] == 0

    button(app, "Next period").click().run()
    assert not app.exception
    second = app.session_state.fw_history[1]
    assert second.opening_cash == first.closing_cash
    assert second.dividends["Household 1"] == pytest.approx(1 / 3)
    assert app.session_state.fw_selected == 2


def test_draft_is_preserved_but_does_not_change_running_economy():
    app = open_app()
    button(app, "Start new simulation").click().run()
    app.session_state.fw_view = "Set up"
    app.run()
    app.number_input(key="fw_household_leisure_priority_0").set_value(3.0).run()
    app.number_input(key="fw_firm_productivity").set_value(3.0).run()
    assert [item.label for item in app.expander] == ["Household 1", "Household 2", "Firm"]
    app.session_state.fw_view = "Results"
    app.run()
    button(app, "Next period").click().run()
    assert app.session_state.fw_history[-1].firm.productivity == 2
    assert app.session_state.fw_history[-1].households[0].leisure_priority == 1
    app.session_state.fw_view = "Set up"
    app.run()
    assert app.number_input(key="fw_household_leisure_priority_0").value == 3
    assert app.number_input(key="fw_firm_productivity").value == 3
    button(app, "Start new simulation").click().run()
    assert len(app.session_state.fw_history) == 1
    assert app.session_state.fw_history[0].firm.productivity == 3
    assert app.session_state.fw_history[0].households[0].leisure_priority == 3


def test_resize_scope_and_reset():
    app = open_app()
    app.number_input(key="fw_household_consumption_priority_0").set_value(2.0).run()
    app.number_input(key="fw_count").set_value(3).run()
    assert app.number_input(key="fw_household_consumption_priority_0").value == 2
    assert app.number_input(key="fw_household_consumption_priority_2").value == 1
    app.number_input(key="fw_count").set_value(2).run()
    assert len(app.session_state.fw_households) == 2

    button(app, "Start new simulation").click().run()
    app.pills(key="fw_report_scope").set_value("Cumulative").run()
    assert app.session_state.fw_report_scope == "Cumulative"
    assert any("Cumulative from Period 1 through Period 1" in item.value for item in app.caption)

    app.session_state.prod_user_marker = "keep"
    button(app, "Reset").click().run()
    assert not app.session_state.fw_history
    assert app.number_input(key="fw_household_money_0").value == 1
    assert app.number_input(key="fw_firm_productivity").value == 2
    assert app.session_state.prod_user_marker == "keep"


def test_ask_why_uses_period_transfers_without_duplicate_price_explanation():
    app = open_app()
    button(app, "Start new simulation").click().run()
    app.session_state.fw_view = "Ask why"
    app.run()

    assert not app.exception
    labels = [item.label for item in app.expander]
    assert labels.count("How were the wage and price found?") == 1
    assert "How was the price found?" not in labels
    assert app.selectbox(key="fw_chat_transfer").options[0] == "Whole period"
    assert any(option.startswith("Wage") for option in app.selectbox(
        key="fw_chat_transfer"
    ).options)
