"""Independent economic acceptance checks through public Economy 0.9 APIs.

The checks use budgets, marginal conditions and stock-flow identities. They do
not call the wage solver, reproduce its scalar reduction, or trust check flags
as evidence that an equilibrium is correct.
"""

from copy import deepcopy
from dataclasses import asdict, replace
from math import fsum, isfinite, sqrt
from random import Random

import pytest

from econ_agent_sim.economy_0_8 import (
    Firm as Firm08,
)
from econ_agent_sim.economy_0_8 import (
    Household as Household08,
)
from econ_agent_sim.economy_0_8 import (
    advance_firm_period,
)
from econ_agent_sim.economy_0_9 import (
    Firm,
    Household,
    advance_investment_period,
    investment_report,
)


def linked_periods(households, firm, count):
    periods = []
    previous = None
    for _ in range(count):
        previous = advance_investment_period(households, firm, previous)
        periods.append(previous)
    return tuple(periods)


def assert_close(actual, expected, scale=None):
    """Use relative accuracy without an absolute floor in monetary units."""
    tolerance = 3e-9 * (abs(expected) if scale is None else abs(scale))
    assert abs(actual - expected) <= tolerance


def assert_economic_snapshot(period, previous=None):
    """Reconstruct funded settlement and check independent optimality conditions."""
    firm = period.firm
    total_money = fsum(period.opening_cash.values())
    assert period.price > 0 and isfinite(period.price)
    assert period.wage > 0 and isfinite(period.wage)
    assert period.capital_open > 0 and period.capital_close > 0
    assert all(period.checks.values())

    expected_opening = (
        previous.closing_cash
        if previous
        else {**{h.name: h.money for h in period.households}, firm.name: firm.money}
    )
    assert period.opening_cash == expected_opening
    assert period.number == (previous.number + 1 if previous else 1)
    assert period.capital_open == (previous.capital_close if previous else firm.capital)
    dividend = (
        min(
            max(previous.net_operating_profit, 0),
            max(period.opening_cash[firm.name] - firm.money, 0),
        )
        if previous
        else 0
    )
    assert_close(period.dividends_paid, dividend, total_money)
    assert_close(fsum(period.dividends.values()), dividend, total_money)
    assert_close(
        period.operating_cash,
        period.opening_cash[firm.name] - dividend,
        total_money,
    )

    # Inspect settlement in its actual order: cash is never invented or spent
    # before receipt. Own-account investment must not masquerade as a payment.
    cash = dict(period.opening_cash)
    delivered = {h.name: 0.0 for h in period.households}
    cash_legs = {
        kind: {h.name: 0.0 for h in period.households}
        for kind in ("dividend", "wage", "goods_payment")
    }
    assert [t.transaction_id for t in period.transfers] == list(
        range(1, len(period.transfers) + 1)
    )
    kinds = []
    for transfer in period.transfers:
        assert transfer.sender != transfer.receiver
        assert transfer.period == period.number
        assert transfer.quantity > 0 and isfinite(transfer.quantity)
        assert transfer.kind in {"dividend", "wage", "goods_payment", "goods_delivery"}
        kinds.append(transfer.kind)
        if transfer.asset == "Money":
            assert transfer.kind != "goods_delivery"
            if transfer.kind == "goods_payment":
                assert transfer.receiver == firm.name
                household_name = transfer.sender
            else:
                assert transfer.sender == firm.name
                household_name = transfer.receiver
            cash_legs[transfer.kind][household_name] += transfer.quantity
            assert cash[transfer.sender] + 3e-9 * total_money >= transfer.quantity
            cash[transfer.sender] -= transfer.quantity
            cash[transfer.receiver] += transfer.quantity
            assert min(cash.values()) >= -3e-9 * total_money
            assert_close(fsum(cash.values()), total_money)
        else:
            assert transfer.asset == "X" and transfer.kind == "goods_delivery"
            assert transfer.sender == firm.name
            delivered[transfer.receiver] += transfer.quantity
    if "dividend" in kinds and "wage" in kinds:
        assert max(i for i, k in enumerate(kinds) if k == "dividend") < min(
            i for i, k in enumerate(kinds) if k == "wage"
        )
    if "wage" in kinds and "goods_payment" in kinds:
        assert max(i for i, k in enumerate(kinds) if k == "wage") < min(
            i for i, k in enumerate(kinds) if k == "goods_payment"
        )
    for name, balance in cash.items():
        assert_close(period.closing_cash[name], balance, total_money)
    for kind, mapping in (
        ("dividend", period.dividends),
        ("wage", period.wages),
        ("goods_payment", period.purchases),
    ):
        for name, amount in mapping.items():
            assert_close(cash_legs[kind][name], amount, total_money)

    for household in period.households:
        name = household.name
        a, b, g = (
            household.consumption_priority,
            household.money_priority,
            household.leisure_priority,
        )
        normalizer = a + b + g
        a, b, g = a / normalizer, b / normalizer, g / normalizer
        assert_close(period.ownership[name], 1 / len(period.households))
        assert_close(
            period.dividends[name], dividend / len(period.households), total_money
        )
        resources = (
            period.opening_cash[name] + period.dividends[name] + period.wages[name]
        )
        assert resources > 0
        assert 0 <= period.work[name] < 1
        assert_close(period.leisure[name], 1 - period.work[name])
        assert_close(period.wages[name], period.wage * period.work[name], total_money)
        assert_close(
            period.purchases[name] + period.closing_cash[name], resources, total_money
        )
        assert_close(period.purchases[name], period.price * period.consumption[name])
        assert_close(delivered[name], period.consumption[name])

        # Consumption/money marginal rate equals the relative price. The labor
        # envelope condition includes the zero-work Kuhn-Tucker inequality.
        assert_close(a * period.closing_cash[name], b * period.purchases[name])
        marginal_work_gain = (a + b) * period.wage / resources
        marginal_leisure_cost = g / period.leisure[name]
        if period.work[name] > 1e-10:
            assert_close(marginal_work_gain, marginal_leisure_cost)
        else:
            assert marginal_work_gain <= marginal_leisure_cost * (1 + 3e-9)

    labor = fsum(period.work.values())
    physical_consumption = fsum(period.consumption.values())
    expected_output = (
        firm.productivity * period.capital_open ** (1 - firm.theta) * labor**firm.theta
    )
    assert_close(period.output, expected_output)
    assert_close(period.output, physical_consumption + period.investment_quantity)
    assert_close(period.wage_bill, period.wage * labor)
    assert_close(period.production_value, period.price * period.output)
    assert_close(period.sales_received, period.price * physical_consumption)
    assert_close(period.sales_received, fsum(period.purchases.values()))
    assert_close(
        period.gross_operating_surplus, period.production_value - period.wage_bill
    )
    assert_close(
        period.investment_quantity,
        firm.reinvestment_rate * period.gross_operating_surplus / period.price,
        period.output,
    )
    assert_close(
        period.investment_value,
        period.price * period.investment_quantity,
        period.production_value,
    )
    assert_close(
        period.depreciation_quantity,
        firm.depreciation_rate * period.capital_open,
        period.capital_open,
    )
    assert_close(
        period.depreciation_value,
        period.price * period.depreciation_quantity,
        period.production_value + period.price * period.capital_open,
    )
    assert_close(
        period.capital_close,
        period.capital_open - period.depreciation_quantity + period.investment_quantity,
    )
    assert_close(
        period.net_operating_profit,
        period.gross_operating_surplus - period.depreciation_value,
        period.production_value + period.depreciation_value,
    )
    assert_close(
        period.sales_received - period.wage_bill,
        (1 - firm.reinvestment_rate) * period.gross_operating_surplus,
    )

    # Firm optimality uses the actual funded budget and value of marginal
    # physical production, independently of the scalar market-clearing solver.
    marginal_revenue_product = period.price * firm.theta * period.output / labor
    assert period.wage_bill <= period.operating_cash * (1 + 3e-9)
    if period.wage_bill < period.operating_cash * (1 - 1e-7):
        assert_close(marginal_revenue_product, period.wage)
    else:
        assert_close(period.wage_bill, period.operating_cash)
        assert marginal_revenue_product >= period.wage * (1 - 3e-9)

    prior_price = previous.price if previous else period.price
    assert period.capital_price_open == prior_price
    assert period.capital_price_close == period.price
    assert_close(period.capital_value_open, prior_price * period.capital_open)
    assert_close(period.capital_value_close, period.price * period.capital_close)
    assert_close(
        period.holding_gain,
        (period.price - prior_price) * period.capital_open,
        period.capital_value_open,
    )
    valuation_scale = period.capital_value_open + period.capital_value_close
    assert_close(
        period.capital_value_close - period.capital_value_open,
        period.investment_value - period.depreciation_value + period.holding_gain,
        valuation_scale,
    )
    assert_close(
        period.equity_open, period.opening_cash[firm.name] + period.capital_value_open
    )
    assert_close(
        period.equity_close, period.closing_cash[firm.name] + period.capital_value_close
    )
    assert_close(
        period.equity_close - period.equity_open,
        period.net_operating_profit - dividend + period.holding_gain,
        period.equity_open + period.equity_close,
    )
    assert_close(
        period.retained_earnings_open,
        previous.retained_earnings_close if previous else 0,
        period.equity_open,
    )
    assert_close(
        period.retained_earnings_close,
        period.retained_earnings_open + period.net_operating_profit - dividend,
        period.equity_open + period.equity_close,
    )
    assert_close(
        period.revaluation_reserve_open,
        previous.revaluation_reserve_close if previous else 0,
        period.equity_open,
    )
    assert_close(
        period.revaluation_reserve_close,
        period.revaluation_reserve_open + period.holding_gain,
        period.equity_open + period.equity_close,
    )
    assert_close(
        period.equity_close,
        period.contributed_equity
        + period.retained_earnings_close
        + period.revaluation_reserve_close,
    )
    if previous:
        assert period.contributed_equity == previous.contributed_equity
    else:
        assert_close(
            period.contributed_equity, firm.money + period.price * firm.capital
        )
        assert period.holding_gain == 0

    assert_close(
        period.next_dividend_budget,
        min(
            max(period.net_operating_profit, 0),
            max(period.closing_cash[firm.name] - firm.money, 0),
        ),
        total_money,
    )
    household_saving = fsum(
        period.closing_cash[h.name] - period.opening_cash[h.name]
        for h in period.households
    )
    assert_close(
        household_saving + period.net_operating_profit - dividend,
        period.investment_value - period.depreciation_value,
        period.production_value + period.depreciation_value,
    )
    assert_close(fsum(period.closing_cash.values()), total_money)


def test_default_matches_closed_form_and_ten_period_capital_transition():
    households = (Household("A"), Household("B"))
    periods = linked_periods(households, Firm(), 10)
    capital = 1.0
    previous = None
    for period in periods:
        # In this default unconstrained path post-dividend cash restores the
        # symmetric allocation, so these monetary fractions remain constant.
        output = 2 * sqrt(capital * 10 / 13)
        assert_close(period.wage, 13 / 11)
        assert_close(fsum(period.work.values()), 10 / 13)
        assert_close(period.output, output)
        assert_close(period.price, (20 / 11) / output)
        assert_close(period.wage_bill, 10 / 11)
        assert_close(period.sales_received, 16 / 11)
        assert_close(period.investment_quantity, output / 5)
        assert_close(period.dividends_paid, 0 if previous is None else 6 / 11, 3)
        assert_close(period.next_dividend_budget, 6 / 11)
        assert_close(period.closing_cash["A"], 8 / 11)
        assert_close(period.closing_cash["Firm"], 17 / 11)
        capital = 0.9 * capital + output / 5
        assert_close(period.capital_close, capital)
        assert_economic_snapshot(period, previous)
        previous = period


def test_cashless_worker_and_rich_nonworker_with_funded_firm():
    households = (
        Household("Cashless", money=0, leisure_priority=8),
        Household("Rich", money=100, leisure_priority=8),
        Household("Worker", money=0.1, leisure_priority=0.1),
    )
    period = advance_investment_period(households, Firm(money=0.05))
    assert period.work["Rich"] == 0
    assert period.work["Cashless"] > 0
    assert_close(period.wage_bill, 0.05)
    # Funding can make the capital share differ from r*(1-theta).
    assert period.investment_quantity / period.output > 0.4 * 0.5
    assert_economic_snapshot(period)


@pytest.mark.parametrize(("capital", "payout_period"), [(100, 7), (10_000, 58)])
def test_dividends_resume_after_capital_losses_without_erasing_retained_losses(
    capital, payout_period
):
    periods = linked_periods(
        (Household("A"), Household("B")), Firm(capital=capital), payout_period
    )
    assert periods[0].net_operating_profit < 0
    assert periods[0].sales_received > periods[0].wage_bill
    assert all(period.dividends_paid == 0 for period in periods[:-1])
    resumed = periods[-1]
    assert resumed.dividends_paid > 0
    assert resumed.retained_earnings_open < 0
    assert periods[-2].net_operating_profit > 0
    # An accumulated-loss gate would veto this dividend and recreate the
    # independently found payout trap. Policy C uses the last period's profit.
    assert (
        min(
            max(resumed.retained_earnings_open, 0),
            max(resumed.opening_cash["Firm"] - resumed.firm.money, 0),
        )
        == 0
    )
    previous = None
    for period in periods:
        assert_economic_snapshot(period, previous)
        previous = period


@pytest.mark.parametrize(("investment", "wear"), [(0, 0.1), (0.4, 0), (0.99, 0.99)])
def test_physical_boundary_policies_preserve_opening_capital_timing(investment, wear):
    periods = linked_periods(
        (Household("A"), Household("B")),
        Firm(reinvestment_rate=investment, depreciation_rate=wear),
        4,
    )
    previous = None
    for period in periods:
        assert_economic_snapshot(period, previous)
        if investment == 0:
            assert period.investment_quantity == 0
            assert period.capital_close < period.capital_open
        if wear == 0:
            assert period.depreciation_quantity == 0
            assert period.capital_close > period.capital_open
        previous = period


def test_linked_currency_scaling_and_relative_priorities_leave_real_choices_unchanged():
    households = (
        Household(
            "A",
            money=0.7,
            consumption_priority=3,
            money_priority=0.4,
            leisure_priority=2,
        ),
        Household(
            "B",
            money=2.3,
            consumption_priority=0.2,
            money_priority=4,
            leisure_priority=0.7,
        ),
        Household(
            "C", money=0, consumption_priority=1, money_priority=2, leisure_priority=5
        ),
    )
    firm = Firm(money=0.8, productivity=3, capital=4, theta=0.4)
    original = linked_periods(households, firm, 5)
    rescored = linked_periods(
        (
            replace(
                households[0],
                consumption_priority=30,
                money_priority=4,
                leisure_priority=20,
            ),
            *households[1:],
        ),
        firm,
        5,
    )
    for first, second in zip(original, rescored, strict=True):
        assert second.work == pytest.approx(first.work, rel=3e-9, abs=0)
        assert second.consumption == pytest.approx(first.consumption, rel=3e-9, abs=0)
        assert_close(second.capital_close, first.capital_close)
        assert_close(second.price, first.price)

    for multiplier in (1e-9, 1e9):
        scaled = linked_periods(
            tuple(replace(h, money=h.money * multiplier) for h in households),
            replace(firm, money=firm.money * multiplier),
            5,
        )
        for first, second in zip(original, scaled, strict=True):
            assert second.work == pytest.approx(first.work, rel=3e-9, abs=0)
            assert second.consumption == pytest.approx(
                first.consumption, rel=3e-9, abs=0
            )
            for field in (
                "output",
                "capital_open",
                "capital_close",
                "investment_quantity",
                "depreciation_quantity",
            ):
                assert_close(getattr(second, field), getattr(first, field))
            for field in (
                "wage",
                "price",
                "production_value",
                "net_operating_profit",
                "equity_close",
                "retained_earnings_close",
                "holding_gain",
                "next_dividend_budget",
                "contributed_equity",
            ):
                assert_close(
                    getattr(second, field),
                    getattr(first, field) * multiplier,
                    (first.equity_open + first.equity_close) * multiplier,
                )
            assert second.closing_cash == pytest.approx(
                {
                    name: value * multiplier
                    for name, value in first.closing_cash.items()
                },
                rel=3e-9,
                abs=0,
            )


def test_zero_investment_and_wear_nest_actual_economy_08_over_linked_periods():
    households = (
        Household("A", money=0.2, consumption_priority=3, money_priority=0.5),
        Household("B", money=2, leisure_priority=4),
    )
    firm = Firm(
        money=0.4, productivity=3, theta=0.6, reinvestment_rate=0, depreciation_rate=0
    )
    households08 = tuple(Household08(**asdict(h)) for h in households)
    firm08 = Firm08(money=firm.money, productivity=firm.productivity, theta=firm.theta)
    previous08 = previous09 = None
    for _ in range(8):
        period08 = advance_firm_period(households08, firm08, previous08)
        period09 = advance_investment_period(households, firm, previous09)
        for field in ("price", "wage", "output", "wage_bill"):
            assert_close(getattr(period09, field), getattr(period08, field))
        for field in ("work", "consumption", "closing_cash", "dividends"):
            assert getattr(period09, field) == pytest.approx(
                getattr(period08, field), rel=3e-9, abs=1e-12
            )
        assert_close(period09.net_operating_profit, period08.profit)
        assert_close(period09.sales_received, period08.revenue)
        assert period09.capital_close == 1
        assert_economic_snapshot(period09, previous09)
        previous08, previous09 = period08, period09


def test_higher_reinvestment_can_reduce_steady_consumption_despite_more_output():
    households = (Household("A"), Household("B"))
    # Start at analytically derived physical steady states. The first-period
    # cash transition is intentional; subsequent baseline cash is stationary.
    low = linked_periods(households, Firm(capital=61.25, reinvestment_rate=0.7), 3)
    high = linked_periods(households, Firm(capital=180, reinvestment_rate=0.9), 3)
    assert_close(low[-1].output, 14)
    assert_close(fsum(low[-1].consumption.values()), 7.875)
    assert_close(high[-1].output, 24)
    assert_close(fsum(high[-1].consumption.values()), 6)
    assert high[-1].capital_close > low[-1].capital_close
    assert high[-1].output > low[-1].output
    assert fsum(high[-1].consumption.values()) < fsum(low[-1].consumption.values())
    assert_close(low[-1].capital_close, low[-1].capital_open)
    assert_close(high[-1].capital_close, high[-1].capital_open)
    assert_economic_snapshot(low[-1], low[-2])
    assert_economic_snapshot(high[-1], high[-2])


def test_small_heterogeneous_matrix_covers_both_funding_regimes():
    random = Random(909)
    constrained = nonworkers = 0
    for case in range(12):
        households = tuple(
            Household(
                str(index),
                money=(0 if index == 0 else random.uniform(0.1, 4)),
                consumption_priority=random.uniform(0.1, 5),
                money_priority=random.uniform(0.1, 5),
                leisure_priority=random.uniform(0.1, 5),
            )
            for index in range(2 + case % 4)
        )
        firm = Firm(
            money=random.uniform(0.03, 2),
            capital=random.uniform(0.1, 30),
            productivity=random.uniform(0.5, 4),
            theta=random.uniform(0.2, 0.8),
            reinvestment_rate=random.uniform(0, 0.9),
            depreciation_rate=random.uniform(0, 0.5),
        )
        previous = None
        for period in linked_periods(households, firm, 4):
            assert_economic_snapshot(period, previous)
            constrained += period.wage_bill >= period.operating_cash * (1 - 1e-7)
            nonworkers += sum(work == 0 for work in period.work.values())
            previous = period
    assert 0 < constrained < 48
    assert nonworkers > 0


def test_failed_continuation_does_not_mutate_accepted_snapshot():
    households = (Household("A"), Household("B"))
    firm = Firm()
    first = advance_investment_period(households, firm)
    original = deepcopy(investment_report((first,)))
    with pytest.raises(ValueError, match="Restart|restart"):
        advance_investment_period(
            households, replace(firm, reinvestment_rate=0.5), first
        )
    with pytest.raises(ValueError, match="Restart|restart"):
        advance_investment_period(
            (replace(households[0], money=3), households[1]), firm, first
        )
    assert investment_report((first,)) == original


def test_cumulative_income_uses_original_prices_and_balance_sheets_use_endpoints():
    periods = linked_periods((Household("A"), Household("B")), Firm(), 4)
    for selected, cumulative in (
        (periods, True),
        (periods, False),
        (periods[1:3], True),
    ):
        report = investment_report(selected, cumulative=cumulative)
        scope = selected if cumulative else selected[-1:]
        first, last = scope[0], scope[-1]
        firm, economy = report["firm"], report["economy"]
        assert report["period_count"] == len(scope)
        assert report["price_wage_period"] == last.number
        assert report["price"] == last.price
        assert report["wage"] == last.wage
        assert_close(report["real_wage"], last.wage / last.price)
        for field in (
            "production_value",
            "sales_received",
            "gross_operating_surplus",
            "net_operating_profit",
            "investment_quantity",
            "investment_value",
            "depreciation_quantity",
            "depreciation_value",
            "holding_gain",
            "dividends_paid",
        ):
            assert_close(
                firm[field],
                fsum(getattr(p, field) for p in scope),
                fsum(p.equity_open + p.equity_close for p in scope),
            )
        for field in (
            "capital",
            "capital_value",
            "equity",
            "retained_earnings",
            "revaluation_reserve",
        ):
            assert firm[f"{field}_open"] == getattr(first, f"{field}_open")
            assert firm[f"{field}_close"] == getattr(last, f"{field}_close")
        assert firm["opening_money"] == first.opening_cash["Firm"]
        assert firm["closing_money"] == last.closing_cash["Firm"]
        assert firm["next_dividend_budget"] == last.next_dividend_budget
        assert firm["contributed_equity"] == periods[0].equity_open
        assert_close(
            firm["capital_value_close"] - firm["capital_value_open"],
            firm["investment_value"]
            - firm["depreciation_value"]
            + firm["holding_gain"],
            first.equity_open + last.equity_close,
        )
        assert_close(
            firm["equity_close"] - firm["equity_open"],
            firm["net_operating_profit"]
            - firm["dividends_paid"]
            + firm["holding_gain"],
            first.equity_open + last.equity_close,
        )
        assert_close(economy["produced_x"], fsum(p.output for p in scope))
        assert_close(
            economy["consumed_x"],
            fsum(c for p in scope for c in p.consumption.values()),
        )
        assert_close(
            economy["produced_x"],
            economy["consumed_x"] + economy["investment_quantity"],
        )
        assert_close(
            economy["production_value"], fsum(p.price * p.output for p in scope)
        )
        assert_close(
            economy["net_income"],
            economy["production_value"] - economy["depreciation_value"],
        )
        assert_close(
            economy["net_income"], economy["wages"] + economy["net_operating_profit"]
        )
        assert_close(
            economy["household_cash_saving"] + economy["firm_net_saving"],
            economy["investment_value"] - economy["depreciation_value"],
            economy["production_value"],
        )
        for entry, household in zip(
            report["households"], first.households, strict=True
        ):
            assert entry["opening_money"] == first.opening_cash[household.name]
            assert entry["closing_money"] == last.closing_cash[household.name]
            assert entry["parameters"]["scores"] == household.scores
            assert_close(
                entry["total_work"], fsum(p.work[household.name] for p in scope)
            )
            assert_close(entry["average_work"], entry["total_work"] / len(scope))
            assert_close(entry["ownership_value_close"], last.equity_close / 2)
            assert_close(
                entry["assets_close"],
                last.closing_cash[household.name] + last.equity_close / 2,
            )
        # Household claims equal firm equity; including both again would double
        # count the same capital. Consolidation retains only cash and capital.
        assert_close(
            fsum(h["ownership_value_close"] for h in report["households"]),
            firm["equity_close"],
        )
        assert_close(
            economy["assets_close"],
            fsum(last.closing_cash.values()) + last.capital_value_close,
        )
        assert_close(
            economy["assets_open"],
            fsum(first.opening_cash.values()) + first.capital_value_open,
        )
        assert all(report["checks"].values())

    cumulative = investment_report(periods, cumulative=True)
    assert (
        abs(
            cumulative["economy"]["production_value"]
            - periods[-1].price * cumulative["economy"]["produced_x"]
        )
        > 0.1
    )
    assert cumulative["firm"]["next_dividend_budget"] < fsum(
        p.next_dividend_budget for p in periods
    )


def test_evidence_exports_distinguish_physical_investment_from_cash_payments():
    households = (Household("Firm-looking household"), Household("Second"))
    periods = linked_periods(households, Firm(name="Workshop"), 3)
    report = investment_report(periods, cumulative=True)
    party_ids = {
        "Firm-looking household": "household_1",
        "Second": "household_2",
        "Workshop": "firm",
    }
    assert {row["record_type"] for row in report["rows"]} == {
        "account",
        "transfer",
        "event",
    }
    accounts = [row for row in report["rows"] if row["record_type"] == "account"]
    assert len(accounts) == len(periods) * 3
    assert len(report["transfers"]) == sum(len(p.transfers) for p in periods)
    assert len(report["events"]) == sum(len(p.events) for p in periods)
    for row in report["transfers"]:
        assert row["sender_id"] == party_ids[row["sender"]]
        assert row["receiver_id"] == party_ids[row["receiver"]]
        assert row["sender_id"] != row["receiver_id"]
        assert row["kind"] in {"dividend", "wage", "goods_payment", "goods_delivery"}
        assert row["unit"] == ("Money" if row["asset"] == "Money" else "X units")
        assert row["valuation_price"] == (
            1 if row["asset"] == "Money" else periods[row["period"] - 1].price
        )
    for period in periods:
        events = [row for row in report["events"] if row["period"] == period.number]
        assert {row["kind"] for row in events} == {
            "production",
            "consumption",
            "capital_wear",
            "capital_installation",
            "revaluation",
        }
        by_kind = {
            kind: [row for row in events if row["kind"] == kind]
            for kind in {row["kind"] for row in events}
        }
        assert_close(
            fsum(row["quantity"] for row in by_kind["production"]), period.output
        )
        assert_close(
            fsum(row["quantity"] for row in by_kind["consumption"]),
            fsum(period.consumption.values()),
        )
        assert_close(
            by_kind["capital_installation"][0]["quantity"], period.investment_quantity
        )
        assert_close(
            by_kind["capital_wear"][0]["quantity"], period.depreciation_quantity
        )
        for row in events:
            assert row["entity_id"] == party_ids[row["entity"]]
            assert row["asset"] != "Money"
            assert row["valuation_price"] == period.price
            if row["kind"] == "revaluation":
                assert row["opening_valuation_price"] == period.capital_price_open
                assert_close(
                    row["value"],
                    (row["valuation_price"] - row["opening_valuation_price"])
                    * row["quantity"],
                    period.capital_value_open,
                )
            else:
                assert_close(row["value"], row["quantity"] * row["valuation_price"])
        firm_account = next(
            row
            for row in accounts
            if row["period"] == period.number and row["entity_id"] == "firm"
        )
        assert firm_account["capital_value_open"] == period.capital_value_open
        assert firm_account["production_value"] == period.production_value
        assert firm_account["investment_value"] == period.investment_value
