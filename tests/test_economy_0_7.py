"""Independent economic optimality and period-accounting checks for work choice."""

import json
from copy import deepcopy
from dataclasses import asdict, replace
from math import fsum, isfinite, log
from random import Random

import pytest

from econ_agent_sim.economy_0_7 import (
    WorkAgent,
    WorkRun,
    advance_work_period,
    default_work_agents,
    work_report,
)


def assert_optimal_and_balanced(period, previous=None):
    """Check choices against feasible alternatives, independently of the solver."""
    price = period.market.prices["X"]
    assert isfinite(price) and price > 0
    for agent in period.population:
        name = agent.name
        opening = period.opening_stocks[name]
        closing = period.closing_stocks[name]
        labor = period.effort[name]
        consumption = period.consumed[name]
        cash = closing["Money"]
        assert 0 <= labor < 1
        assert period.leisure_time[name] == pytest.approx(1 - labor)
        assert period.produced[name] == pytest.approx(agent.productivity * labor)
        assert closing["X"] == 0
        assert consumption > 0 and cash > 0
        if previous:
            assert opening == previous.closing_stocks[name]
        else:
            assert opening == {"X": agent.x, "Money": agent.money}

        resources = opening["X"] + opening["Money"] / price + agent.productivity * labor
        assert consumption + cash / price == pytest.approx(resources, rel=1e-9)
        assert consumption == pytest.approx(agent.alpha * resources, rel=1e-9)
        assert cash / price == pytest.approx((1 - agent.alpha) * resources, rel=1e-9)
        marginal = (1 - agent.leisure) * agent.productivity / resources - agent.leisure / (1 - labor)
        if labor > 1e-9:
            assert marginal == pytest.approx(0, abs=1e-8)
        else:
            assert marginal <= 1e-8

        a = (1 - agent.leisure) * agent.alpha
        b = (1 - agent.leisure) * (1 - agent.alpha)
        utility = a * log(consumption) + b * log(cash / price) + agent.leisure * log(1 - labor)
        # For each alternative effort, test several affordable consumption/money
        # allocations, including its conditionally optimal allocation.
        for alternative_labor in (0, .1, .25, .5, .75, .9, .99):
            available = opening["X"] + opening["Money"] / price + agent.productivity * alternative_labor
            if available <= 0:
                continue
            for share in (.1, agent.alpha, .9):
                alternative = (a * log(share * available) + b * log((1 - share) * available)
                               + agent.leisure * log(1 - alternative_labor))
                assert utility >= alternative - 1e-8

        for asset in ("X", "Money"):
            received = fsum(t.quantity for t in period.market.transactions
                            if t.asset == asset and t.receiver == name)
            sent = fsum(t.quantity for t in period.market.transactions
                        if t.asset == asset and t.sender == name)
            produced = period.produced[name] if asset == "X" else 0
            consumed = consumption if asset == "X" else 0
            assert fsum((opening[asset], produced, received)) == pytest.approx(
                fsum((closing[asset], consumed, sent)), rel=1e-9, abs=1e-10
            )
        payments = fsum(t.payment for t in period.market.trades if t.buyer == name)
        assert payments <= opening["Money"] + 1e-9

    assert fsum(s["Money"] for s in period.closing_stocks.values()) == pytest.approx(
        fsum(s["Money"] for s in period.opening_stocks.values()), rel=1e-10
    )
    assert fsum(period.consumed.values()) == pytest.approx(
        fsum(s["X"] for s in period.opening_stocks.values()) + fsum(period.produced.values()), rel=1e-10
    )
    assert all(t.period == period.number for t in period.market.transactions)
    assert all(t.period == period.number for t in period.market.trades)
    assert all(period.checks.values()) and all(period.work_checks.values())


def test_equal_priorities_baseline_has_half_work_one_output_and_no_trade():
    agents = tuple(WorkAgent(**a) for a in default_work_agents())
    assert len(agents) == 2
    assert all((a.x, a.money, a.alpha, a.productivity, a.leisure) == (0, 1, .5, 2, 1 / 3)
               for a in agents)
    previous = None
    for number in range(1, 13):
        current = advance_work_period(agents, previous)
        assert current.number == number
        assert current.market.prices["X"] == pytest.approx(1)
        assert not current.market.trades
        assert current.effort == pytest.approx({a.name: .5 for a in agents})
        assert current.produced == pytest.approx({a.name: 1 for a in agents})
        assert current.consumed == pytest.approx({a.name: 1 for a in agents})
        assert_optimal_and_balanced(current, previous)
        previous = current


def test_different_productivity_has_independently_derived_price_work_and_trade():
    agents = (WorkAgent("A", productivity=4), WorkAgent("B"))
    period = advance_work_period(agents)
    assert period.market.prices["X"] == pytest.approx(2 / 3)
    assert period.effort == pytest.approx({"A": 13 / 24, "B": 5 / 12})
    assert period.produced == pytest.approx({"A": 13 / 6, "B": 5 / 6})
    assert period.consumed == pytest.approx({"A": 11 / 6, "B": 7 / 6})
    assert len(period.market.trades) == 1
    trade = period.market.trades[0]
    assert (trade.seller, trade.buyer) == ("A", "B")
    assert trade.quantity == pytest.approx(1 / 3)
    assert trade.payment == pytest.approx(2 / 9)
    assert_optimal_and_balanced(period)


def test_zero_work_corners_and_initial_goods_are_economically_valid():
    agents = (WorkAgent("Rich", money=100, leisure=.9), WorkAgent("Worker", leisure=.1))
    period = advance_work_period(agents)
    assert period.effort["Rich"] == 0
    assert period.market.prices["X"] == pytest.approx(50.55 / .9)
    assert period.consumed["Rich"] > 0
    assert_optimal_and_balanced(period)
    # Sufficient initial goods make everyone choose zero work in period one.
    agents = (WorkAgent("A", x=100), WorkAgent("B"))
    first = advance_work_period(agents)
    assert first.market.prices["X"] == pytest.approx(.02)
    assert first.effort == {"A": 0, "B": 0}
    second = advance_work_period(agents, first)
    assert fsum(second.produced.values()) > 0
    assert_optimal_and_balanced(first)
    assert_optimal_and_balanced(second, first)


def test_cashless_agent_can_produce_and_earn_without_borrowing():
    agents = (WorkAgent("A", money=0), WorkAgent("B"))
    period = advance_work_period(agents)
    assert period.effort["A"] == pytest.approx(2 / 3)
    assert period.closing_stocks["A"]["Money"] > 0
    assert all(t.buyer != "A" for t in period.market.trades)
    assert_optimal_and_balanced(period)


def test_currency_rescaling_and_uniform_productivity_have_correct_real_effects():
    agents = (WorkAgent("A", money=3, alpha=.7, leisure=.2),
              WorkAgent("B", productivity=4, leisure=.6))
    original = advance_work_period(agents)
    for multiplier in (.001, 1000):
        scaled = advance_work_period(tuple(replace(a, money=a.money * multiplier) for a in agents))
        assert scaled.market.prices["X"] == pytest.approx(original.market.prices["X"] * multiplier)
        assert scaled.effort == pytest.approx(original.effort)
        assert scaled.consumed == pytest.approx(original.consumed)
        for a in agents:
            assert scaled.closing_stocks[a.name]["Money"] == pytest.approx(
                original.closing_stocks[a.name]["Money"] * multiplier
            )
    # General-equilibrium productivity need not increase work: doubling every
    # agent's productivity doubles consumption and halves price with same effort.
    productive = advance_work_period(tuple(replace(a, productivity=a.productivity * 2) for a in agents))
    assert productive.effort == pytest.approx(original.effort)
    assert productive.market.prices["X"] == pytest.approx(original.market.prices["X"] / 2)
    assert productive.consumed == pytest.approx({name: 2 * c for name, c in original.consumed.items()})


def test_heterogeneous_linked_periods_optimize_and_reconcile_without_shocks():
    rng = Random(707)
    for _ in range(8):
        agents = tuple(WorkAgent(str(i), x=rng.uniform(0, 3), money=rng.uniform(.01, 5),
                                 alpha=rng.uniform(.1, .9), productivity=rng.uniform(.1, 5),
                                 leisure=rng.uniform(.1, .9)) for i in range(rng.randint(2, 20)))
        previous = None
        for _ in range(8):
            current = advance_work_period(agents, previous)
            assert current.population == agents
            assert_optimal_and_balanced(current, previous)
            previous = current


def test_continuation_preserves_history_and_requires_restart_for_new_settings():
    agents = (WorkAgent("A", x=2, alpha=.7), WorkAgent("B", money=2, leisure=.7))
    first = advance_work_period(agents)
    snapshot = deepcopy(asdict(first))
    second = advance_work_period(agents, first)
    assert asdict(first) == snapshot
    assert advance_work_period(agents, first) == second
    assert advance_work_period(agents) == first
    for name in first.closing_stocks:
        assert second.opening_stocks[name] is not first.closing_stocks[name]
    for field, value in (("productivity", 5), ("leisure", .2), ("alpha", .2), ("money", 5)):
        with pytest.raises(ValueError):
            advance_work_period((replace(agents[0], **{field: value}), agents[1]), first)
    assert asdict(first) == snapshot


@pytest.mark.parametrize("specs", [
    (("0", .001, 1, .01, 2, .01), ("1", 0, 0, .5, 2, .01),
     ("4", 1e6, 1e6, .1, .1, .1), ("5", .001, .001, .1, .1, 1 / 3),
     ("7", 1, 0, .5, 2, .99), ("8", 0, 1e6, .1, .1, 1 / 3),
     ("9", .001, 1e6, .5, 100, .99), ("10", .001, 1e6, .1, 100, .8),
     ("11", 0, 1, .5, 100, .01), ("12", 1e6, .001, .9, 2, 1 / 3),
     ("13", 0, 1, .1, .1, 1 / 3)),
    (("0", 1e6, 1e6, .99, 100, .01), ("1", 1e6, 1e6, .9, .1, .99),
     ("2", .001, 1e6, .1, 100, .8), ("3", .001, .001, .01, 100, 1 / 3),
     ("4", .001, 1, .9, 100, .8), ("5", 0, 0, .5, 2, .99),
     ("6", 1, .001, .1, .1, 1 / 3), ("7", 0, 0, .9, 2, .8)),
])
def test_ui_scale_extremes_do_not_reject_settlement_roundoff(specs):
    # Regressions: aggregate supply roundoff reaches a small counterparty, and
    # discarding tiny goods transfers at high prices loses meaningful money.
    agents = tuple(WorkAgent(*spec) for spec in specs)
    previous = None
    for _ in range(30):
        current = advance_work_period(agents, previous)
        assert all(current.checks.values()) and all(current.work_checks.values())
        assert fsum(s["Money"] for s in current.closing_stocks.values()) == pytest.approx(
            fsum(a.money for a in agents), rel=1e-12
        )
        for name in current.closing_stocks:
            assert current.closing_stocks[name]["Money"] >= 0
            assert current.consumed[name] >= 0
        previous = current


def test_invalid_specs_and_no_money_are_rejected():
    for field in ("x", "money", "alpha", "productivity", "leisure"):
        for value in (float("nan"), float("inf"), float("-inf")):
            with pytest.raises(ValueError):
                WorkAgent("A", **{field: value})
    for field in ("x", "money", "productivity"):
        with pytest.raises(ValueError):
            WorkAgent("A", **{field: -1})
    for field in ("alpha", "leisure"):
        for value in (0, 1, -1, 2):
            with pytest.raises(ValueError):
                WorkAgent("A", **{field: value})
    with pytest.raises(ValueError):
        WorkAgent("A", productivity=0)
    with pytest.raises(ValueError):
        advance_work_period(())
    with pytest.raises(ValueError):
        advance_work_period((WorkAgent("A"), WorkAgent("A")))
    with pytest.raises(ValueError):
        advance_work_period((WorkAgent("A", money=0), WorkAgent("B", money=0)))


def test_adapter_carries_actual_work_period_flows_and_serializable_context():
    agents = (WorkAgent("A", productivity=4), WorkAgent("B"))
    first = advance_work_period(agents)
    second = advance_work_period(agents, first)
    run = WorkRun(second, first, 7)
    data = run.data
    assert run.period == second.market
    assert data["model"] == "work_leisure"
    assert data["assets"] == ["X", "Money"]
    assert data["revision"] == 7
    assert data["effort"] == second.effort
    assert data["leisure_time"] == second.leisure_time
    assert data["period_opening"] == first.closing_stocks
    assert data["produced"] == second.produced
    assert data["consumed"] == second.consumed
    assert data["period_closing"] == second.closing_stocks
    assert data["previous_run"]["prices"] == first.market.prices
    assert all(data["work_checks"].values())
    assert run.context(0)["selected_trade"] == data["trades"][0]
    for index in (-1, len(data["trades"]), True, "0", None):
        assert run.context(index)["selected_trade"] is None
    json.dumps(run.context(), allow_nan=False)


def test_period_and_cumulative_reports_separate_stocks_from_flows():
    population = (WorkAgent("A", productivity=4, alpha=.7, leisure=.2),
                  WorkAgent("B", money=2, productivity=1.5, alpha=.3, leisure=.6))
    periods = []
    previous = None
    for _ in range(3):
        previous = advance_work_period(population, previous)
        periods.append(previous)

    current = work_report(tuple(periods), cumulative=False)
    cumulative = work_report(tuple(periods), cumulative=True)
    assert current["label"] == "Period 3" and current["period_count"] == 1
    assert cumulative["label"] == "Periods 1–3" and cumulative["period_count"] == 3
    assert cumulative["opening"] == {
        asset: fsum(periods[0].opening_stocks[name][asset] for name in ("A", "B"))
        for asset in ("X", "Money")
    }
    assert cumulative["closing"] == {
        asset: fsum(periods[-1].closing_stocks[name][asset] for name in ("A", "B"))
        for asset in ("X", "Money")
    }
    assert cumulative["produced"] == pytest.approx(
        fsum(value for period in periods for value in period.produced.values())
    )
    assert cumulative["consumed"] == pytest.approx(
        fsum(value for period in periods for value in period.consumed.values())
    )
    assert cumulative["gross_money_exchanged"] == pytest.approx(
        fsum(t.payment for period in periods for t in period.market.trades)
    )
    assert cumulative["gross_x_exchanged"] == pytest.approx(
        fsum(t.quantity for period in periods for t in period.market.trades)
    )
    assert cumulative["average_work"] == pytest.approx(
        fsum(value for period in periods for value in period.effort.values()) / 6
    )
    assert len(cumulative["rows"]) == 3 * 2 * 2
    assert {row["period"] for row in cumulative["rows"]} == {1, 2, 3}
    for agent in cumulative["agents"]:
        assert agent["net_trade_cash"] == pytest.approx(
            agent["closing"]["Money"] - agent["opening"]["Money"]
        )
        assert sum(agent["parameters"]["weights"].values()) == pytest.approx(1)
    assert all(cumulative["checks"].values())
    assert work_report((periods[0],), cumulative=True)["label"] == "Period 1"
    with pytest.raises(ValueError):
        work_report(())
    json.dumps(cumulative, allow_nan=False)
