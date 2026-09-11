"""Economic and accounting checks for firms, wages and delayed dividends."""

import json
from copy import deepcopy
from dataclasses import asdict, replace
from math import fsum, log
from random import Random

import pytest

from econ_agent_sim.economy_0_8 import (
    Economy08Run,
    Firm,
    Household,
    advance_firm_period,
    default_firm,
    default_households,
    firm_report,
)


def assert_period_is_optimal_and_balanced(period, previous=None):
    households = period.households
    firm = period.firm
    names = [household.name for household in households]
    assert period.price > 0 and period.wage > 0 and period.output > 0
    assert all(period.checks.values())
    assert sum(period.ownership.values()) == pytest.approx(1)
    assert set(period.ownership) == set(names)
    assert period.opening_cash == (
        previous.closing_cash
        if previous
        else {**{h.name: h.money for h in households}, firm.name: firm.money}
    )

    prior_profit = previous.profit if previous else 0
    assert fsum(period.dividends.values()) == pytest.approx(prior_profit)
    assert period.post_dividend_cash[firm.name] == pytest.approx(firm.money)
    assert period.wage_bill <= firm.money + 1e-9
    assert fsum(period.work.values()) == pytest.approx(
        period.solution["total_labor"]
    )
    assert period.output == pytest.approx(
        firm.productivity * fsum(period.work.values()) ** firm.theta
    )
    assert fsum(period.consumption.values()) == pytest.approx(period.output)
    assert fsum(period.purchases.values()) == pytest.approx(period.revenue)
    assert period.revenue == pytest.approx(period.price * period.output)
    assert period.profit == pytest.approx(period.revenue - period.wage_bill)

    # Independently test household budget identities and utility against a
    # broad set of feasible alternatives at the equilibrium prices.
    for household in households:
        name = household.name
        weights = household.weights
        available = period.post_dividend_cash[name]
        income = available + period.wages[name]
        labor = period.work[name]
        consumption = period.consumption[name]
        closing_money = period.closing_cash[name]
        assert 0 <= labor < 1
        assert period.leisure[name] == pytest.approx(1 - labor)
        assert period.wages[name] == pytest.approx(period.wage * labor)
        assert period.purchases[name] + closing_money == pytest.approx(income)
        assert period.purchases[name] == pytest.approx(household.alpha * income)
        assert closing_money == pytest.approx((1 - household.alpha) * income)
        utility = (
            weights["consumption"] * log(consumption)
            + weights["money"] * log(closing_money / period.price)
            + weights["leisure"] * log(1 - labor)
        )
        for alternative_labor in (0, .05, .2, .5, .8, .95, .999):
            alternative_income = available + period.wage * alternative_labor
            if alternative_income <= 0:
                continue
            for share in (.05, household.alpha, .95):
                alternative = (
                    weights["consumption"]
                    * log(share * alternative_income / period.price)
                    + weights["money"]
                    * log((1 - share) * alternative_income / period.price)
                    + weights["leisure"] * log(1 - alternative_labor)
                )
                assert utility >= alternative - 1e-8

    # At fixed equilibrium prices the firm cannot improve within its cash cap.
    labor = fsum(period.work.values())
    profit = period.price * firm.productivity * labor**firm.theta - period.wage * labor
    limit = firm.money / period.wage
    for fraction in (0, .01, .1, .25, .5, .75, .9, 1):
        alternative_labor = fraction * limit
        alternative_profit = (
            period.price * firm.productivity * alternative_labor**firm.theta
            - period.wage * alternative_labor
        )
        assert profit >= alternative_profit - 1e-8

    assert fsum(period.opening_cash.values()) == pytest.approx(
        fsum(period.closing_cash.values()), rel=1e-10
    )
    assert min(period.post_dividend_cash.values()) >= 0
    assert min(period.closing_cash.values()) >= 0
    kinds = {transfer.kind for transfer in period.transfers}
    assert kinds <= {"dividend", "wage", "goods_payment", "goods_delivery"}
    assert all(transfer.period == period.number for transfer in period.transfers)
    for transfer in period.transfers:
        assert transfer.quantity > 0
        assert transfer.sender != transfer.receiver


def test_analytical_baseline_and_delayed_dividend_stationarity():
    households = tuple(Household(**values) for values in default_households())
    firm = Firm(**default_firm())
    assert [h.name for h in households] == ["Household 1", "Household 2"]
    assert all(h.weights == pytest.approx({
        "consumption": 1 / 3, "money": 1 / 3, "leisure": 1 / 3,
    }) for h in households)

    first = advance_firm_period(households, firm)
    assert first.number == 1
    assert first.wage == pytest.approx(1)
    assert first.price == pytest.approx((2 / 3) ** .5)
    assert first.work == pytest.approx({h.name: 1 / 3 for h in households})
    assert first.output == pytest.approx((8 / 3) ** .5)
    assert first.wage_bill == pytest.approx(2 / 3)
    assert first.revenue == pytest.approx(4 / 3)
    assert first.profit == pytest.approx(2 / 3)
    assert first.dividends == {h.name: 0 for h in households}
    assert first.closing_cash == pytest.approx(
        {"Household 1": 2 / 3, "Household 2": 2 / 3, "Firm": 5 / 3}
    )
    assert "dividend" not in {transfer.kind for transfer in first.transfers}
    assert_period_is_optimal_and_balanced(first)

    previous = first
    for number in range(2, 8):
        current = advance_firm_period(households, firm, previous)
        assert current.number == number
        assert current.dividends == pytest.approx({h.name: 1 / 3 for h in households})
        assert current.post_dividend_cash == pytest.approx(
            {"Household 1": 1, "Household 2": 1, "Firm": 1}
        )
        assert current.price == pytest.approx(first.price)
        assert current.wage == pytest.approx(first.wage)
        assert current.work == pytest.approx(first.work)
        assert current.closing_cash == pytest.approx(first.closing_cash)
        assert_period_is_optimal_and_balanced(current, previous)
        previous = current


def test_cashless_household_zero_work_corner_and_binding_firm_funding():
    households = (
        Household("Cashless", money=0, leisure_priority=8),
        Household("Rich", money=100, leisure_priority=8),
        Household("Worker", money=.1, leisure_priority=.1),
    )
    period = advance_firm_period(households, Firm(money=.05))
    assert period.work["Rich"] == 0
    assert period.work["Cashless"] > 0
    assert period.solution["funding_binding"]
    assert period.wage_bill == pytest.approx(.05)
    assert period.solution["marginal_revenue_product"] >= period.wage
    assert_period_is_optimal_and_balanced(period)


def test_currency_and_priority_score_scaling_leave_real_choices_unchanged():
    households = (
        Household("A", .5, 2, .5, 3),
        Household("B", 4, .5, 4, 1),
    )
    firm = Firm(money=.8, productivity=3, theta=.4)
    original = advance_firm_period(households, firm)
    for multiplier in (.001, 1000):
        scaled = advance_firm_period(
            tuple(replace(h, money=h.money * multiplier) for h in households),
            replace(firm, money=firm.money * multiplier),
        )
        assert scaled.wage == pytest.approx(original.wage * multiplier)
        assert scaled.price == pytest.approx(original.price * multiplier)
        assert scaled.work == pytest.approx(original.work)
        assert scaled.output == pytest.approx(original.output)
        assert scaled.consumption == pytest.approx(original.consumption)
        assert scaled.profit == pytest.approx(original.profit * multiplier)

    rescaled_scores = advance_firm_period(
        (replace(
            households[0],
            consumption_priority=20,
            money_priority=5,
            leisure_priority=30,
        ), households[1]),
        firm,
    )
    assert rescaled_scores.price == pytest.approx(original.price)
    assert rescaled_scores.wage == pytest.approx(original.wage)
    assert rescaled_scores.work == pytest.approx(original.work)
    assert rescaled_scores.consumption == pytest.approx(original.consumption)


def test_heterogeneous_linked_periods_reconcile_across_regimes():
    random = Random(808)
    binding_periods = resting_households = 0
    for case in range(20):
        households = tuple(
            Household(
                str(index),
                money=(0 if index == 0 and case % 2 else random.uniform(.01, 5)),
                consumption_priority=random.uniform(.05, 5),
                money_priority=random.uniform(.05, 5),
                leisure_priority=random.uniform(.05, 5),
            )
            for index in range(random.randint(2, 12))
        )
        firm = Firm(
            money=random.uniform(.01, 5),
            productivity=random.uniform(.1, 4),
            theta=random.uniform(.1, .9),
        )
        previous = None
        for _ in range(5):
            current = advance_firm_period(households, firm, previous)
            assert_period_is_optimal_and_balanced(current, previous)
            binding_periods += current.solution["funding_binding"]
            resting_households += current.solution["resting_households"]
            previous = current
    assert binding_periods > 0
    assert resting_households > 0


def test_failed_or_changed_continuation_does_not_mutate_history():
    households = (Household("A"), Household("B"))
    firm = Firm()
    first = advance_firm_period(households, firm)
    snapshot = deepcopy(asdict(first))
    assert advance_firm_period(households, firm, first) == advance_firm_period(
        households, firm, first
    )
    for changed_households, changed_firm in (
        ((replace(households[0], money=2), households[1]), firm),
        (households, replace(firm, productivity=3)),
    ):
        with pytest.raises(ValueError, match="Restart"):
            advance_firm_period(changed_households, changed_firm, first)
    assert asdict(first) == snapshot


@pytest.mark.parametrize(
    ("factory", "values"),
    [
        (Household, {"name": ""}),
        (Household, {"money": -1}),
        (Household, {"consumption_priority": 0}),
        (Household, {"money_priority": -1}),
        (Household, {"leisure_priority": 0}),
        (Firm, {"name": ""}),
        (Firm, {"money": 0}),
        (Firm, {"productivity": 0}),
        (Firm, {"theta": 0}),
        (Firm, {"theta": 1}),
    ],
)
def test_invalid_settings_are_rejected(factory, values):
    with pytest.raises(ValueError):
        factory(**({"name": "A"} | values) if factory is Household else values)


def test_nonfinite_settings_and_invalid_populations_are_rejected():
    for value in (float("nan"), float("inf"), float("-inf")):
        for field in (
            "money", "consumption_priority", "money_priority", "leisure_priority"
        ):
            with pytest.raises(ValueError):
                Household("A", **{field: value})
        for field in ("money", "productivity", "theta"):
            with pytest.raises(ValueError):
                Firm(**{field: value})
    with pytest.raises(ValueError):
        advance_firm_period((), Firm())
    with pytest.raises(ValueError):
        advance_firm_period((Household("A"), Household("A")), Firm())
    with pytest.raises(ValueError):
        advance_firm_period((Household("Firm"),), Firm())
    with pytest.raises(ValueError, match="aggregate cash"):
        advance_firm_period((Household("A", money=0),), Firm())


def test_period_and_cumulative_reports_keep_stocks_and_flows_distinct():
    households = (
        Household("A", .5, 2, 1, .5),
        Household("B", 2, .5, 2, 3),
    )
    firm = Firm(money=.7, productivity=3, theta=.6)
    periods = []
    previous = None
    for _ in range(3):
        previous = advance_firm_period(households, firm, previous)
        periods.append(previous)
    current = firm_report(tuple(periods))
    cumulative = firm_report(tuple(periods), cumulative=True)

    assert current["label"] == "Period 3" and current["period_count"] == 1
    assert cumulative["label"] == "Periods 1–3"
    assert cumulative["period_count"] == 3
    assert cumulative["price"] == periods[-1].price
    assert cumulative["wage"] == periods[-1].wage
    assert cumulative["economy"]["opening_money"] == pytest.approx(
        fsum(periods[0].opening_cash.values())
    )
    assert cumulative["economy"]["closing_money"] == pytest.approx(
        fsum(periods[-1].closing_cash.values())
    )
    assert cumulative["economy"]["produced"] == pytest.approx(
        fsum(period.output for period in periods)
    )
    assert cumulative["economy"]["output_value"] == pytest.approx(
        cumulative["economy"]["wages"] + cumulative["economy"]["profit"]
    )
    assert cumulative["firm"]["produced_x"] == pytest.approx(
        fsum(period.output for period in periods)
    )
    assert cumulative["firm"]["sold_x"] == pytest.approx(
        fsum(sum(period.consumption.values()) for period in periods)
    )
    assert cumulative["firm"]["profit_awaiting_distribution"] == periods[-1].profit
    assert len(cumulative["rows"]) == 3 * 3
    assert {row["period"] for row in cumulative["rows"]} == {1, 2, 3}
    assert all(cumulative["checks"].values())
    assert firm_report((periods[0],), cumulative=True)["label"] == "Period 1"
    with pytest.raises(ValueError):
        firm_report(())
    json.dumps(cumulative, allow_nan=False)


def test_run_adapter_exposes_tutor_context_and_serializes():
    households = (Household("A"), Household("B"))
    firm = Firm()
    first = advance_firm_period(households, firm)
    second = advance_firm_period(households, firm, first)
    run = Economy08Run(second, first, 7)
    data = run.data
    assert run.period == second and run.current == second
    assert data["model"] == "firms_wages"
    assert data["number"] == 2 and data["revision"] == 7
    assert data["prices"]["X"] == second.price
    assert data["wage"] == second.wage and data["output"] == second.output
    assert data["work"] == second.work and data["leisure_time"] == second.leisure
    assert data["previous_run"]["prices"] == first.prices
    assert data["totals"]["opening"]["Money"] == pytest.approx(3)
    assert data["reporting"] == data["report"]
    assert data["trades"] == []
    assert run.context(0)["selected_transfer"] == data["transfers"][0]
    for index in (-1, len(data["transfers"]), True, "0", None):
        assert run.context(index)["selected_transfer"] is None
    json.dumps(run.context(), allow_nan=False)
