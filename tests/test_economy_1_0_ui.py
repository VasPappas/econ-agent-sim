"""Protect submitted runs and setup continuity in the two-firm workspace."""

import json
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = Path(__file__).parents[1] / "app/streamlit_app.py"


def open_app():
    app = AppTest.from_file(APP, default_timeout=20).run()
    return app.switch_page("pages/11_Economy_1_0_Two_Firms_One_Market.py").run()


def button(app, label):
    return next(item for item in app.button if item.label == label)


def test_component_wire_payload_is_an_object_with_a_real_report():
    app = open_app()
    button(app, "Start new simulation").click().run()

    def check_payload(scope):
        component = app.get("bidi_component")[0]
        payload = json.loads(component.proto.json)
        # Streamlit silently stringifies the WHOLE payload when one nested
        # value is not JSON serializable. Python-only exception checks miss
        # this failure because the crash happens later in the browser.
        assert isinstance(payload, dict)
        assert payload["reporting"]["model"] == "competition"
        assert payload["reporting"]["scope"] == scope
        assert len(payload["reporting"]["firms"]) == 2
        assert payload["selected_firm"] == "firm_a"
        assert all(isinstance(value, (str, int, float, bool))
                   for value in payload["diagnostics"].values())
        assert payload["diagnostics"]["relative_market_error"] < 1e-9

    check_payload("period")
    button(app, "+10 periods").click().run()
    app.pills(key="cg_report_scope").set_value("Cumulative").run()
    check_payload("cumulative")


def test_baseline_and_atomic_ten_period_advance():
    app = open_app()
    assert not app.exception
    assert app.number_input(key="cg_firm_capital_0").value == .5
    assert app.number_input(key="cg_firm_reinvestment_rate_0").value == 40
    assert app.number_input(key="cg_firm_capital_1").value == .5
    assert app.number_input(key="cg_firm_depreciation_rate_0").value == 10
    button(app, "Start new simulation").click().run()
    assert not app.exception
    first = app.session_state.cg_history[0]
    assert first.capital_close == pytest.approx(1.2508232077228116)
    button(app, "+10 periods").click().run()
    assert not app.exception
    assert len(app.session_state.cg_history) == 11
    assert app.session_state.cg_selected == 11
    assert app.session_state.cg_history[1].opening_cash == first.closing_cash
    assert app.session_state.cg_history[1].capital_open == first.capital_close


def test_draft_percentages_and_expansion_survive_navigation():
    app = open_app()
    # Native expander state is independent of child widget rerenders. Simulate
    # the browser's tracked state; AppTest does not expose an expander toggle.
    app.session_state.cg_open_household_0 = True
    app.session_state.cg_expanded["household_0"] = True
    app.number_input(key="cg_household_consumption_priority_0").set_value(1.1).run()
    assert app.session_state.cg_open_household_0 is True
    app.number_input(key="cg_firm_reinvestment_rate_0").set_value(70.0).run()
    app.number_input(key="cg_firm_productivity_1").set_value(2.4).run()
    assert app.session_state.cg_firms[0]["productivity"] == 2.0
    assert app.session_state.cg_firms[1]["productivity"] == 2.4
    assert app.session_state.cg_firms[0]["reinvestment_rate"] == pytest.approx(.7)
    button(app, "Start new simulation").click().run()
    app.session_state.cg_view = "Set up"
    app.run()
    assert app.session_state.cg_open_household_0 is True
    app.number_input(key="cg_firm_reinvestment_rate_0").set_value(30.0).run()
    app.number_input(key="cg_household_leisure_priority_0").set_value(3.0).run()
    app.session_state.cg_view = "Results"
    app.run()
    button(app, "Next period →").click().run()
    assert app.session_state.cg_history[-1].firms[0].reinvestment_rate == .7
    assert app.session_state.cg_history[-1].households[0].leisure_priority == 1
    app.session_state.cg_view = "Set up"
    app.run()
    assert app.number_input(key="cg_firm_reinvestment_rate_0").value == 30
    assert app.number_input(key="cg_household_leisure_priority_0").value == 3
    button(app, "Start new simulation").click().run()
    assert len(app.session_state.cg_history) == 1
    assert app.session_state.cg_history[0].firms[0].reinvestment_rate == .3


def test_scope_ask_why_and_reset_preserve_other_chapters():
    app = open_app()
    app.number_input(key="cg_count").set_value(3).run()
    assert app.number_input(key="cg_household_money_2").value == 1
    app.number_input(key="cg_count").set_value(2).run()
    assert len(app.session_state.cg_households) == 2
    button(app, "Start new simulation").click().run()
    button(app, "+10 periods").click().run()
    app.pills(key="cg_report_scope").set_value("Cumulative").run()
    app.session_state.cg_view = "Set up"
    app.run()
    app.session_state.cg_view = "Results"
    app.run()
    assert app.pills(key="cg_report_scope").value == "Cumulative"
    app.session_state.cg_view = "Ask why"
    app.run()
    assert not app.exception
    assert app.session_state.cg_report_scope == "Cumulative"
    assert any(item.label == "Explore a question" for item in app.selectbox)
    app.session_state.ig_marker = "preserve"
    button(app, "Reset").click().run()
    assert not app.session_state.cg_history
    assert app.number_input(key="cg_firm_reinvestment_rate_0").value == 40
    assert app.number_input(key="cg_firm_capital_0").value == .5
    assert app.session_state.ig_marker == "preserve"
    button(app, "Start new simulation").click().run()
    assert app.pills(key="cg_report_scope").value == "This period"


def test_failed_batch_does_not_append_partial_history(monkeypatch):
    from econ_agent_sim import economy_1_0

    app = open_app()
    button(app, "Start new simulation").click().run()
    first = app.session_state.cg_history[0]
    actual_advance = economy_1_0.advance_competition_period

    def fail_third(households, firm, previous=None):
        if previous and previous.number >= 2:
            raise ArithmeticError("Deliberate convergence failure")
        return actual_advance(households, firm, previous=previous)

    monkeypatch.setattr(economy_1_0, "advance_competition_period", fail_third)
    app.run()  # Bind the callback to the patched advance function.
    button(app, "+10 periods").click().run()
    assert not app.exception
    assert app.session_state.cg_history == [first]
    assert app.session_state.cg_selected == 1
    assert "Deliberate convergence failure" in app.session_state.cg_error


def test_selected_firm_survives_tab_navigation_and_external_restore():
    app = open_app()
    button(app, "Start new simulation").click().run()
    # Opening a file restores the durable selection independently of the
    # mounted component. The next click must start from that restored value.
    firm_b = app.session_state.cg_firms[1]["id"]
    app.session_state.cg_selected_firm = firm_b
    app.run()
    assert not app.exception
    assert app.session_state.cg_results_component["selected_firm"] == firm_b
    app.session_state.cg_view = "Set up"
    app.run()
    app.session_state.cg_view = "Results"
    app.run()
    assert app.session_state.cg_selected_firm == firm_b
    assert app.session_state.cg_results_component["selected_firm"] == firm_b
    button(app, "Reset").click().run()
    assert app.session_state.cg_selected_firm == app.session_state.cg_firms[0]["id"]
