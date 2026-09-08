import json
from dataclasses import replace
from math import isclose
from pathlib import Path
from random import Random
from unittest.mock import patch

import pytest
from streamlit.testing.v1 import AppTest

from econ_agent_sim.economy_0_5 import (
    MoneyAgent,
    MoneyRun,
    account_rows,
    run_money_economy,
)
from econ_agent_sim.explanations import built_in_explanations


def test_symmetric_baseline_and_known_trade():
    baseline = run_money_economy((MoneyAgent("A"), MoneyAgent("B")))
    assert baseline.prices["X"] == 1
    assert not baseline.trades
    trade = run_money_economy((MoneyAgent("A", x=2), MoneyAgent("B")))
    assert trade.prices["X"] == pytest.approx(2 / 3)
    assert len(trade.trades) == 1
    assert trade.trades[0].quantity == pytest.approx(.25)
    assert trade.trades[0].payment == pytest.approx(1 / 6)
    assert trade.closing_stocks["A"]["Money"] == pytest.approx(7 / 6)
    context = MoneyRun(trade, baseline, 2, 2).context(0)
    assert all(context["checks"].values())
    assert context["assets"] == ["X", "Money"]
    assert "no Y" in built_in_explanations(context)["Why did the price move?"]
    assert "assumed" in built_in_explanations(context)["Why do agents hold money?"]
    json.dumps(context, allow_nan=False)


def test_cash_goods_and_preferences_change_the_equilibrium():
    a, b = MoneyAgent("A"), MoneyAgent("B")
    assert run_money_economy((replace(a, alpha=.8), b)).prices["X"] > 1
    double_cash = run_money_economy((replace(a, money=2), replace(b, money=2)))
    assert double_cash.prices["X"] == 2
    assert not double_cash.trades
    no_cash = run_money_economy((replace(a, money=0, x=2), replace(b, x=0)))
    assert all(s[asset] >= 0 for s in no_cash.closing_stocks.values() for asset in ("X", "Money"))
    assert no_cash.trades[0].buyer == "B"


def test_randomized_affordability_optimality_and_ledger_pairing():
    rng = Random(52)
    for _ in range(150):
        agents = tuple(MoneyAgent(f"Agent {i}", rng.uniform(.01, 50), rng.uniform(.01, 50),
                                  rng.uniform(.01, .99)) for i in range(rng.randint(2, 20)))
        result = run_money_economy(agents)
        for a in agents:
            final = result.closing_stocks[a.name]
            desired = result.desired_bundles[a.name]
            assert final["X"] == pytest.approx(desired["X"])
            assert final["Money"] == pytest.approx(desired["Money"])
            assert final["Money"] >= 0
            before = a.x**a.alpha * a.money**(1-a.alpha)
            after = final["X"]**a.alpha * final["Money"]**(1-a.alpha)
            assert after >= before - 1e-8
            spending = sum(t.payment for t in result.trades if t.buyer == a.name)
            assert spending <= a.money + 1e-10
        for trade, good, money in zip(result.trades, result.transactions[::2], result.transactions[1::2]):
            assert good.asset == "X" and money.asset == "Money"
            assert (good.sender, good.receiver) == (money.receiver, money.sender)
            assert money.quantity == trade.payment == trade.quantity * result.prices["X"]
        assert all(isclose(row["check"], 0, abs_tol=1e-9) for row in account_rows(result))


def test_invalid_inputs_and_missing_market_resources():
    for field in ("x", "money", "alpha"):
        for value in (float("nan"), float("inf"), float("-inf")):
            with pytest.raises(ValueError):
                MoneyAgent("A", **{field: value})
    for field in ("x", "money"):
        with pytest.raises(ValueError):
            MoneyAgent("A", **{field: -1})
        with pytest.raises(ValueError):
            run_money_economy((MoneyAgent("A", **{field: 0}), MoneyAgent("B", **{field: 0})))
    with pytest.raises(ValueError):
        run_money_economy((MoneyAgent("A"), MoneyAgent("A")))
    result = run_money_economy((MoneyAgent("A", x=0, money=0), MoneyAgent("B")))
    assert result.closing_stocks["A"] == {"X": 0, "Money": 0}


def test_new_chapter_draft_reset_navigation_and_chat_model():
    app = AppTest.from_file(Path(__file__).parents[1] / "app/streamlit_app.py", default_timeout=10).run()
    app.switch_page("pages/6_Economy_0_5_Good_and_Money.py").run()
    assert not app.exception
    assert app.session_state.cash_result is None
    next(b for b in app.button if b.label == "Run").click().run()
    assert app.session_state.cash_result.prices["X"] == 1
    baseline = app.session_state.cash_result
    app.session_state.cash_view = "Set up"
    app.run()
    app.number_input(key="cash_money_0").set_value(2.0).run()
    app.session_state.cash_view = "Ask why"
    app.run()
    assert not app.exception
    assert app.session_state.cash_result == baseline
    assert "Why do agents hold money?" in {e.label for e in app.expander}
    app.session_state.cash_view = "Set up"
    app.run()
    assert app.number_input(key="cash_money_0").value == 2
    next(b for b in app.button if b.label == "Run").click().run()
    assert app.session_state.cash_previous == baseline
    assert app.session_state.cash_result.prices["X"] == 1.5
    next(b for b in app.button if b.label == "Reset").click().run()
    assert not app.exception
    assert app.session_state.cash_result is None
    assert app.number_input(key="cash_money_0").value == 1


def test_money_chat_grounding_budget_and_failed_run():
    large = run_money_economy(tuple(MoneyAgent(f"Agent {i}", i+1, 20-i, .2+i*.03)
                                   for i in range(20)))
    run = MoneyRun(large, large, 2, 2)
    assert len(json.dumps(run.context(0), allow_nan=False)) < 35000
    def settings(name, default=""):
        return {"OPENAI_API_KEY": "fake", "ECON_CHAT_ENABLED": "true"}.get(name, default)
    with patch("econ_agent_sim.chat_view.chat_setting", side_effect=settings), patch("econ_agent_sim.chat_view.answer_question", return_value="Money is valued.") as answer:
        app = AppTest.from_file(Path(__file__).parents[1] / "app/streamlit_app.py", default_timeout=10).run()
        app.switch_page("pages/6_Economy_0_5_Good_and_Money.py").run()
        next(b for b in app.button if b.label == "Run").click().run()
        app.session_state.cash_view = "Ask why"
        app.run()
        app.chat_input[0].set_value("Why hold money?").run()
        assert not app.exception
        context = answer.call_args.args[1]
        assert context["model"] == "money_in_utility"
        assert "Y" not in context["agents"][0]["opening"]
        app.session_state.cash_view = "Set up"
        app.run()
        for i in range(2):
            app.number_input(key=f"cash_money_{i}").set_value(0.0).run()
        next(b for b in app.button if b.label == "Run").click().run()
        assert not app.exception
        assert app.error
        assert app.session_state.cash_result.prices["X"] == 1
