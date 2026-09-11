"""Independent acceptance checks for Economy 0.8's competitive equilibrium.

These tests derive household and firm conditions directly from the published
model contract.  They deliberately exercise only the public period/report API,
rather than reproducing the wage solver's implementation.
"""

from copy import deepcopy
from dataclasses import asdict, replace
from math import fsum, isfinite
from random import Random

import pytest

from econ_agent_sim.economy_0_8 import (
    FIRM_NAME,
    Economy08Run,
    Firm,
    Household,
    advance_firm_period,
    default_firm,
    default_households,
    firm_report,
)


def assert_period_is_competitive_and_balanced(period, previous=None):
    """Verify the model identities without relying on its scalar reduction."""
    assert period.price > 0 and isfinite(period.price)
    assert period.wage > 0 and isfinite(period.wage)
    assert all(period.checks.values())
    assert sum(period.ownership.values()) == pytest.approx(1)
    assert set(period.ownership) == {household.name for household in period.households}

    if previous is None:
        assert period.number == 1
        expected_opening = {
            **{household.name: household.money for household in period.households},
            period.firm.name: period.firm.money,
        }
        prior_profit = 0.0
    else:
        assert period.number == previous.number + 1
        assert period.opening_cash == previous.closing_cash
        expected_opening = previous.closing_cash
        prior_profit = previous.profit
    assert period.opening_cash == pytest.approx(expected_opening)
    assert fsum(period.dividends.values()) == pytest.approx(prior_profit)

    # Reconstruct settlement in ledger order.  Every payer must remain funded,
    # and money must be conserved after every individual transfer—not only at
    # the period close.
    balances = dict(period.opening_cash)
    initial_total = fsum(balances.values())
    delivered_x = 0.0
    assert [row.transaction_id for row in period.transfers] == list(
        range(1, len(period.transfers) + 1)
    )
    for row in period.transfers:
        assert row.period == period.number
        assert row.quantity > 0 and isfinite(row.quantity)
        assert row.kind in {"dividend", "wage", "goods_payment", "goods_delivery"}
        if row.asset == "Money":
            assert balances[row.sender] >= row.quantity - 1e-9 * max(1.0, initial_total)
            balances[row.sender] -= row.quantity
            balances[row.receiver] += row.quantity
            assert min(balances.values()) >= -1e-9 * max(1.0, initial_total)
            assert fsum(balances.values()) == pytest.approx(initial_total, rel=1e-11)
        else:
            assert row.asset == "X" and row.kind == "goods_delivery"
            assert row.sender == period.firm.name
            delivered_x += row.quantity
    assert balances == pytest.approx(period.closing_cash, rel=1e-10, abs=1e-10)
    assert delivered_x == pytest.approx(period.output, rel=1e-10)
    assert fsum(period.closing_cash.values()) == pytest.approx(initial_total, rel=1e-10)

    operating_cash = period.post_dividend_cash[period.firm.name]
    assert operating_cash == pytest.approx(period.firm.money, rel=1e-9)
    assert period.post_dividend_cash[period.firm.name] == pytest.approx(
        period.opening_cash[period.firm.name] - prior_profit
    )

    for household in period.households:
        name = household.name
        weights = household.weights
        assert sum(weights.values()) == pytest.approx(1)
        dividend = prior_profit * period.ownership[name]
        cash_after_dividend = period.opening_cash[name] + dividend
        resources = cash_after_dividend + period.wage * period.work[name]

        assert period.dividends[name] == pytest.approx(dividend)
        assert period.post_dividend_cash[name] == pytest.approx(cash_after_dividend)
        assert 0 <= period.work[name] < 1
        assert period.leisure[name] == pytest.approx(1 - period.work[name])
        assert period.wages[name] == pytest.approx(period.wage * period.work[name])
        assert period.purchases[name] + period.closing_cash[name] == pytest.approx(
            resources, rel=1e-9
        )
        assert period.purchases[name] == pytest.approx(
            household.alpha * resources, rel=1e-9
        )
        assert period.closing_cash[name] == pytest.approx(
            (1 - household.alpha) * resources, rel=1e-9
        )
        assert period.consumption[name] == pytest.approx(
            period.purchases[name] / period.price, rel=1e-9
        )

        # Envelope condition after optimizing consumption versus liquid money.
        marginal_gain = ((1 - weights["leisure"]) * period.wage / resources)
        marginal_cost = weights["leisure"] / period.leisure[name]
        if period.work[name] > 1e-9:
            assert marginal_gain == pytest.approx(marginal_cost, rel=1e-8, abs=1e-9)
        else:
            assert marginal_gain <= marginal_cost + 1e-9

    labor = fsum(period.work.values())
    assert period.output == pytest.approx(
        period.firm.productivity * labor**period.firm.theta, rel=1e-10
    )
    assert fsum(period.consumption.values()) == pytest.approx(period.output, rel=1e-10)
    assert period.wage_bill == pytest.approx(period.wage * labor, rel=1e-10)
    assert period.revenue == pytest.approx(period.price * period.output, rel=1e-10)
    assert period.profit == pytest.approx(period.revenue - period.wage_bill, rel=1e-10)
    assert period.profit >= -1e-10 * max(1.0, period.revenue)

    marginal_revenue_product = (
        period.price
        * period.firm.productivity
        * period.firm.theta
        * labor ** (period.firm.theta - 1)
    )
    if period.wage_bill < operating_cash - 1e-8 * max(1.0, operating_cash):
        assert marginal_revenue_product == pytest.approx(period.wage, rel=1e-8)
    else:
        assert period.wage_bill == pytest.approx(operating_cash, rel=1e-8, abs=1e-9)
        assert marginal_revenue_product >= period.wage - 1e-8 * max(1.0, period.wage)


def test_published_baseline_and_next_period_dividends_are_exact():
    households = tuple(Household(**row) for row in default_households())
    firm = Firm(**default_firm())
    first = advance_firm_period(households, firm)

    assert first.wage == pytest.approx(1)
    assert first.price == pytest.approx((2 / 3) ** 0.5)
    assert first.work == pytest.approx({household.name: 1 / 3 for household in households})
    assert first.output == pytest.approx(2 * (2 / 3) ** 0.5)
    assert first.wage_bill == pytest.approx(2 / 3)
    assert first.revenue == pytest.approx(4 / 3)
    assert first.profit == pytest.approx(2 / 3)
    assert first.dividends == {household.name: 0 for household in households}
    assert first.closing_cash == pytest.approx(
        {households[0].name: 2 / 3, households[1].name: 2 / 3, firm.name: 5 / 3}
    )
    assert not first.solution["funding_binding"]
    assert_period_is_competitive_and_balanced(first)

    second = advance_firm_period(households, firm, first)
    assert second.dividends == pytest.approx(
        {household.name: 1 / 3 for household in households}
    )
    assert second.post_dividend_cash == pytest.approx(
        {households[0].name: 1, households[1].name: 1, firm.name: 1}
    )
    for field in ("price", "wage", "output", "revenue", "wage_bill", "profit"):
        assert getattr(second, field) == pytest.approx(getattr(first, field))
    assert second.work == pytest.approx(first.work)
    assert_period_is_competitive_and_balanced(second, first)


def test_firm_funding_constraint_and_household_zero_work_corner():
    households = (
        Household("Cash rich", money=100, leisure_priority=20),
        Household("Worker", money=1, leisure_priority=.2),
    )
    period = advance_firm_period(households, Firm(money=.1))
    assert period.work["Cash rich"] == 0
    assert period.work["Worker"] > 0
    assert period.solution["funding_binding"]
    assert period.wage_bill == pytest.approx(.1)
    assert period.solution["marginal_revenue_product"] > period.wage
    assert_period_is_competitive_and_balanced(period)


def test_cashless_household_is_allowed_but_aggregate_cash_is_required():
    households = (Household("Cashless", money=0), Household("Funded"))
    period = advance_firm_period(households, Firm())
    assert period.work["Cashless"] > 0
    assert period.consumption["Cashless"] > 0
    assert period.closing_cash["Cashless"] > 0
    assert_period_is_competitive_and_balanced(period)

    with pytest.raises(ValueError, match="positive aggregate cash"):
        advance_firm_period(
            (Household("A", money=0), Household("B", money=0)), Firm()
        )


def test_currency_units_and_priority_score_units_do_not_change_real_choices():
    households = (
        Household("A", money=.7, consumption_priority=3, money_priority=.4,
                  leisure_priority=2),
        Household("B", money=2.3, consumption_priority=.2, money_priority=4,
                  leisure_priority=.7),
        Household("C", money=0, consumption_priority=1, money_priority=2,
                  leisure_priority=5),
    )
    firm = Firm(money=.8, productivity=3, theta=.4)
    original = advance_firm_period(households, firm)

    rescored = advance_firm_period(
        (replace(households[0], consumption_priority=30, money_priority=4,
                 leisure_priority=20), *households[1:]),
        firm,
    )
    assert rescored.work == pytest.approx(original.work, rel=1e-9)
    assert rescored.consumption == pytest.approx(original.consumption, rel=1e-9)
    assert rescored.closing_cash == pytest.approx(original.closing_cash, rel=1e-9)
    assert rescored.price == pytest.approx(original.price, rel=1e-9)
    assert rescored.wage == pytest.approx(original.wage, rel=1e-9)

    for multiplier in (.001, 1000):
        scaled = advance_firm_period(
            tuple(replace(household, money=household.money * multiplier)
                  for household in households),
            replace(firm, money=firm.money * multiplier),
        )
        assert scaled.price == pytest.approx(original.price * multiplier, rel=1e-8)
        assert scaled.wage == pytest.approx(original.wage * multiplier, rel=1e-8)
        assert scaled.work == pytest.approx(original.work, rel=1e-8)
        assert scaled.consumption == pytest.approx(original.consumption, rel=1e-8)
        assert scaled.output == pytest.approx(original.output, rel=1e-8)
        assert scaled.closing_cash == pytest.approx(
            {name: value * multiplier for name, value in original.closing_cash.items()},
            rel=1e-8,
        )


def test_linked_periods_are_continuous_and_failed_restart_is_atomic():
    households = (
        Household("A", money=.5, consumption_priority=2, leisure_priority=3),
        Household("B", money=2, money_priority=4, leisure_priority=.5),
    )
    firm = Firm(money=.4, productivity=1.5, theta=.6)
    first = advance_firm_period(households, firm)
    snapshot = deepcopy(asdict(first))
    second = advance_firm_period(households, firm, first)
    assert_period_is_competitive_and_balanced(second, first)

    with pytest.raises(ValueError, match="Restart"):
        advance_firm_period((replace(households[0], money=9), households[1]), firm, first)
    with pytest.raises(ValueError, match="Restart"):
        advance_firm_period(households, replace(firm, productivity=9), first)
    assert asdict(first) == snapshot


def test_period_and_cumulative_reports_use_stocks_flows_and_income_once():
    households = (Household("A", money=.5, consumption_priority=3), Household("B", money=2))
    firm = Firm(money=.6, productivity=1.5)
    periods = []
    previous = None
    for _ in range(3):
        previous = advance_firm_period(households, firm, previous)
        periods.append(previous)

    current = firm_report(tuple(periods))
    cumulative = firm_report(tuple(periods), cumulative=True)
    assert current["label"] == "Period 3" and current["period_count"] == 1
    assert cumulative["label"] == "Periods 1–3" and cumulative["period_count"] == 3
    assert cumulative["economy"]["opening_money"] == pytest.approx(
        fsum(periods[0].opening_cash.values())
    )
    assert cumulative["economy"]["closing_money"] == pytest.approx(
        fsum(periods[-1].closing_cash.values())
    )
    assert cumulative["economy"]["produced_x"] == pytest.approx(
        fsum(period.output for period in periods)
    )
    assert cumulative["economy"]["consumed_x"] == pytest.approx(
        fsum(value for period in periods for value in period.consumption.values())
    )
    assert cumulative["economy"]["output_value"] == pytest.approx(
        cumulative["economy"]["wages"] + cumulative["economy"]["profit"]
    )
    assert cumulative["firm"]["dividends_paid"] == pytest.approx(
        fsum(value for period in periods for value in period.dividends.values())
    )
    assert cumulative["price"] == periods[-1].price
    assert cumulative["wage"] == periods[-1].wage
    assert len(cumulative["rows"]) == len(periods) * (len(households) + 1)
    assert all(cumulative["checks"].values())

    data = Economy08Run(periods[-1], periods[-2], revision=4).data
    assert data["report"] == current
    assert data["settings"]["ownership"] == periods[-1].ownership


@pytest.mark.parametrize("field", ["money", "consumption_priority", "money_priority", "leisure_priority"])
@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_nonfinite_household_inputs_are_rejected(field, value):
    with pytest.raises(ValueError):
        Household("A", **{field: value})


def test_random_heterogeneous_linked_economies_satisfy_external_conditions():
    rng = Random(808)
    for economy_number in range(24):
        count = rng.randint(2, 12)
        households = tuple(
            Household(
                f"E{economy_number} H{index}",
                money=0 if index == 0 and economy_number % 3 == 0 else rng.uniform(.02, 6),
                consumption_priority=rng.uniform(.05, 8),
                money_priority=rng.uniform(.05, 8),
                leisure_priority=rng.uniform(.05, 8),
            )
            for index in range(count)
        )
        firm = Firm(
            money=rng.uniform(.02, 5),
            productivity=rng.uniform(.2, 5),
            theta=rng.uniform(.15, .85),
        )
        previous = None
        for _ in range(4):
            period = advance_firm_period(households, firm, previous)
            assert_period_is_competitive_and_balanced(period, previous)
            previous = period


def test_invalid_settings_and_names_are_rejected():
    assert FIRM_NAME == "Firm"
    for kwargs in (
        {"money": -1},
        {"consumption_priority": 0},
        {"money_priority": -1},
        {"leisure_priority": 0},
    ):
        with pytest.raises(ValueError):
            Household("A", **kwargs)
    for kwargs in (
        {"money": 0},
        {"productivity": 0},
        {"productivity": -1},
        {"theta": 0},
        {"theta": 1},
    ):
        with pytest.raises(ValueError):
            Firm(**kwargs)
    with pytest.raises(ValueError):
        advance_firm_period((), Firm())
    with pytest.raises(ValueError):
        advance_firm_period((Household("A"), Household("A")), Firm())
    with pytest.raises(ValueError):
        advance_firm_period((Household(FIRM_NAME),), Firm())
