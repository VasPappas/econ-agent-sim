"""Protect submitted runs and setup continuity in the investment workspace."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = Path(__file__).parents[1] / "app/streamlit_app.py"


def open_app():
    app = AppTest.from_file(APP, default_timeout=20).run()
    return app.switch_page("pages/10_Economy_0_9_Investment_and_Growth.py").run()


def button(app, label):
    return next(item for item in app.button if item.label == label)


def test_baseline_and_atomic_ten_period_advance():
    app = open_app()
    assert not app.exception
    assert app.number_input(key="ig_firm_capital").value == 1
    assert app.number_input(key="ig_firm_reinvestment_rate").value == 40
    assert app.number_input(key="ig_firm_depreciation_rate").value == 10
    button(app, "Start new simulation").click().run()
    assert not app.exception
    first = app.session_state.ig_history[0]
    assert first.capital_close == pytest.approx(1.2508232077228116)
    button(app, "+10 periods").click().run()
    assert not app.exception
    assert len(app.session_state.ig_history) == 11
    assert app.session_state.ig_selected == 11
    assert app.session_state.ig_history[1].opening_cash == first.closing_cash
    assert app.session_state.ig_history[1].capital_open == first.capital_close


def test_draft_percentages_and_expansion_survive_navigation():
    app = open_app()
    # Native expander state is independent of child widget rerenders. Simulate
    # the browser's tracked state; AppTest does not expose an expander toggle.
    app.session_state.ig_open_household_0 = True
    app.session_state.ig_expanded["household_0"] = True
    app.number_input(key="ig_household_consumption_priority_0").set_value(1.1).run()
    assert app.session_state.ig_open_household_0 is True
    app.number_input(key="ig_firm_reinvestment_rate").set_value(70.0).run()
    assert app.session_state.ig_firm["reinvestment_rate"] == pytest.approx(.7)
    button(app, "Start new simulation").click().run()
    app.session_state.ig_view = "Set up"
    app.run()
    assert app.session_state.ig_open_household_0 is True
    app.number_input(key="ig_firm_reinvestment_rate").set_value(30.0).run()
    app.number_input(key="ig_household_leisure_priority_0").set_value(3.0).run()
    app.session_state.ig_view = "Results"
    app.run()
    button(app, "Next period →").click().run()
    assert app.session_state.ig_history[-1].firm.reinvestment_rate == .7
    assert app.session_state.ig_history[-1].households[0].leisure_priority == 1
    app.session_state.ig_view = "Set up"
    app.run()
    assert app.number_input(key="ig_firm_reinvestment_rate").value == 30
    assert app.number_input(key="ig_household_leisure_priority_0").value == 3
    button(app, "Start new simulation").click().run()
    assert len(app.session_state.ig_history) == 1
    assert app.session_state.ig_history[0].firm.reinvestment_rate == .3


def test_scope_ask_why_and_reset_preserve_other_chapters():
    app = open_app()
    app.number_input(key="ig_count").set_value(3).run()
    assert app.number_input(key="ig_household_money_2").value == 1
    app.number_input(key="ig_count").set_value(2).run()
    assert len(app.session_state.ig_households) == 2
    button(app, "Start new simulation").click().run()
    button(app, "+10 periods").click().run()
    app.pills(key="ig_report_scope").set_value("Cumulative").run()
    app.session_state.ig_view = "Ask why"
    app.run()
    assert not app.exception
    assert app.session_state.ig_report_scope == "Cumulative"
    assert any(item.label == "Explore a question" for item in app.selectbox)
    app.session_state.fw_marker = "preserve"
    button(app, "Reset").click().run()
    assert not app.session_state.ig_history
    assert app.number_input(key="ig_firm_reinvestment_rate").value == 40
    assert app.number_input(key="ig_firm_capital").value == 1
    assert app.session_state.fw_marker == "preserve"


def test_failed_batch_does_not_append_partial_history(monkeypatch):
    from econ_agent_sim import economy_0_9

    app = open_app()
    button(app, "Start new simulation").click().run()
    first = app.session_state.ig_history[0]
    actual_advance = economy_0_9.advance_investment_period

    def fail_third(households, firm, previous=None):
        if previous and previous.number >= 2:
            raise ArithmeticError("Deliberate convergence failure")
        return actual_advance(households, firm, previous=previous)

    monkeypatch.setattr(economy_0_9, "advance_investment_period", fail_third)
    app.run()  # Bind the callback to the patched advance function.
    button(app, "+10 periods").click().run()
    assert not app.exception
    assert app.session_state.ig_history == [first]
    assert app.session_state.ig_selected == 1
    assert "Deliberate convergence failure" in app.session_state.ig_error
