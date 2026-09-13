"""Independent acceptance of the two-firm economy through public APIs.

These checks reconstruct budgets, marginal conditions and settled accounts;
they neither call the scalar solver nor accept its check flags as an oracle.
The preceding released engine supplies the proportional-split path oracle.
"""

from collections import defaultdict
from dataclasses import replace
from math import fsum, isfinite, sqrt

import pytest

from econ_agent_sim.economy_0_9 import (
    Firm as Firm09,
)
from econ_agent_sim.economy_0_9 import (
    Household as Household09,
)
from econ_agent_sim.economy_0_9 import advance_investment_period
from econ_agent_sim.economy_1_0 import Firm, Household, advance_competition_period

HOUSEHOLDS = (Household("household_1", "Household 1"),
              Household("household_2", "Household 2"))
FIRMS = (Firm("firm_a", "Firm A"), Firm("firm_b", "Firm B"))


def close(actual, expected, scale=0.0):
    """No absolute monetary floor that could conceal currency-dependent errors."""
    assert isfinite(actual) and isfinite(expected)
    tolerance = 3e-9 * max(abs(actual), abs(expected), abs(scale), 1e-280)
    assert abs(actual - expected) <= tolerance, (actual, expected, scale)


def periods_for(households, firms, count):
    result = []
    previous = None
    for _ in range(count):
        previous = advance_competition_period(households, firms, previous)
        result.append(previous)
    return tuple(result)


def assert_funded_ledger(period):
    """Replay actual payments, delivery consideration and all allocation margins."""
    household_ids = {h.id for h in period.households}
    firm_ids = {f.id for f in period.firms}
    labels = {entity.id: entity.name for entity in (*period.households, *period.firms)}
    cash = dict(period.opening_cash)
    money = fsum(cash.values())
    receipts = defaultdict(float)
    pairs = defaultdict(list)
    for transfer in period.transfers:
        assert transfer.period == period.number
        assert transfer.sender_id != transfer.receiver_id
        assert transfer.sender == labels[transfer.sender_id]
        assert transfer.receiver == labels[transfer.receiver_id]
        assert transfer.quantity > 0 and isfinite(transfer.quantity)
        pairs[transfer.pair_id].append(transfer)
        if transfer.kind in ("wage", "dividend", "goods_delivery"):
            assert transfer.sender_id in firm_ids
            assert transfer.receiver_id in household_ids
            firm_id, household_id = transfer.sender_id, transfer.receiver_id
        else:
            assert transfer.kind in ("goods_payment", "labor_delivery")
            assert transfer.sender_id in household_ids
            assert transfer.receiver_id in firm_ids
            household_id, firm_id = transfer.sender_id, transfer.receiver_id
        receipts[(household_id, firm_id, transfer.kind)] += transfer.quantity
        if transfer.asset == "Money":
            assert transfer.kind in ("wage", "dividend", "goods_payment")
            assert transfer.valuation_price == 1
            assert cash[transfer.sender_id] + 5e-14 * money >= transfer.quantity
            cash[transfer.sender_id] -= transfer.quantity
            cash[transfer.receiver_id] += transfer.quantity
            assert min(cash.values()) >= -5e-14 * money
            close(fsum(cash.values()), money)
        else:
            assert (transfer.asset, transfer.kind) in (
                ("Labor", "labor_delivery"), ("X", "goods_delivery")
            )
            assert transfer.valuation_price == (
                period.wage if transfer.asset == "Labor" else period.price
            )

    assert len({t.transaction_id for t in period.transfers}) == len(period.transfers)
    kinds = [t.kind for t in period.transfers]
    for earlier, later in (("dividend", "wage"), ("wage", "goods_payment")):
        if earlier in kinds and later in kinds:
            assert max(i for i, kind in enumerate(kinds) if kind == earlier) < min(
                i for i, kind in enumerate(kinds) if kind == later
            )
    for pair in pairs.values():
        by_kind = {leg.kind: leg for leg in pair}
        if "dividend" in by_kind:
            assert len(pair) == 1
            continue
        assert len(pair) == 2
        if "wage" in by_kind:
            payment, delivery = by_kind["wage"], by_kind["labor_delivery"]
            rate = period.wage
        else:
            payment, delivery = by_kind["goods_payment"], by_kind["goods_delivery"]
            rate = period.price
        assert payment.sender_id == delivery.receiver_id
        assert payment.receiver_id == delivery.sender_id
        close(payment.quantity, delivery.quantity * rate)
    for entity_id, amount in cash.items():
        close(period.closing_cash[entity_id], amount, money)

    assert len(period.allocations) == len(household_ids) * len(firm_ids)
    assert len({(a.household_id, a.firm_id) for a in period.allocations}) == len(
        period.allocations
    )
    for allocation in period.allocations:
        hid, fid = allocation.household_id, allocation.firm_id
        firm = period.firm_accounts[fid]
        close(allocation.ownership_share, 1 / len(household_ids))
        for key, kind in (("wages", "wage"), ("dividends", "dividend"),
                          ("purchases", "goods_payment"),
                          ("consumption", "goods_delivery"),
                          ("work", "labor_delivery")):
            close(getattr(allocation, key), receipts[(hid, fid, kind)],
                  money if kind in ("wage", "dividend", "goods_payment") else 0)
        close(allocation.work, period.work[hid] * firm.work / fsum(period.work.values()))
        close(allocation.consumption,
              period.consumption[hid] * firm.sales_quantity / fsum(period.consumption.values()))
        close(allocation.dividends, firm.dividends_paid / len(household_ids), money)
        close(allocation.ownership_value_open, firm.equity_open / len(household_ids))
        close(allocation.ownership_value_close, firm.equity_close / len(household_ids))
    for household_id in household_ids:
        allocated = [a for a in period.allocations if a.household_id == household_id]
        for key in ("work", "wages", "dividends", "purchases", "consumption"):
            close(fsum(getattr(a, key) for a in allocated), getattr(period, key)[household_id],
                  money if key in ("wages", "dividends", "purchases") else 0)
    for firm_id in firm_ids:
        account = period.firm_accounts[firm_id]
        allocated = [a for a in period.allocations if a.firm_id == firm_id]
        for source, target in (("work", "work"), ("wages", "wage_bill"),
                               ("dividends", "dividends_paid"),
                               ("purchases", "sales_received"),
                               ("consumption", "sales_quantity")):
            close(fsum(getattr(a, source) for a in allocated), getattr(account, target),
                  money if source in ("wages", "dividends", "purchases") else 0)
    return receipts


def assert_economic_snapshot(period, previous=None):
    money = fsum(period.opening_cash.values())
    assert period.price > 0 and isfinite(period.price)
    assert period.wage > 0 and isfinite(period.wage)
    expected_opening = (
        previous.closing_cash if previous else
        {entity.id: entity.money for entity in (*period.households, *period.firms)}
    )
    assert period.opening_cash == expected_opening
    assert period.number == (previous.number + 1 if previous else 1)
    assert min(period.closing_cash.values()) >= 0
    assert_funded_ledger(period)

    for household in period.households:
        hid = household.id
        priorities = (household.consumption_priority, household.money_priority,
                      household.leisure_priority)
        a, b, g = (value / fsum(priorities) for value in priorities)
        available = period.opening_cash[hid] + period.dividends[hid]
        resources = available + period.wages[hid]
        close(period.post_dividend_cash[hid], available, money)
        close(period.purchases[hid] + period.closing_cash[hid], resources)
        close(period.purchases[hid], period.price * period.consumption[hid])
        close(period.wages[hid], period.wage * period.work[hid], money)
        assert 0 <= period.work[hid] < 1
        close(period.leisure[hid], 1 - period.work[hid])
        close(a * period.closing_cash[hid], b * period.purchases[hid])
        marginal_gain = (a + b) * period.wage / resources
        marginal_cost = g / period.leisure[hid]
        if period.work[hid] > 1e-10:
            close(marginal_gain, marginal_cost)
        else:
            assert marginal_gain <= marginal_cost * (1 + 3e-9)

    production_events = [e for e in period.events if e.kind == "production"]
    assert {e.entity_id for e in production_events} == {f.id for f in period.firms}
    for firm in period.firms:
        account = period.firm_accounts[firm.id]
        prior = previous.firm_accounts[firm.id] if previous else None
        price_open = previous.price if previous else period.price
        close(account.capital_open, prior.capital_close if prior else firm.capital)
        close(account.opening_cash, period.opening_cash[firm.id])
        close(account.closing_cash, period.closing_cash[firm.id])
        expected_dividend = min(max(prior.net_operating_profit, 0),
                                max(account.opening_cash - firm.money, 0)) if prior else 0
        close(account.dividends_paid, expected_dividend, money)
        close(account.operating_cash, account.opening_cash - expected_dividend)
        close(period.post_dividend_cash[firm.id], account.operating_cash)
        assert account.work > 0 and account.output > 0 and account.capital_close > 0
        close(account.output, firm.productivity * sqrt(account.capital_open * account.work))
        close(account.wage_bill, period.wage * account.work)
        close(account.production_value, period.price * account.output)
        close(account.sales_quantity + account.investment_quantity, account.output)
        close(account.sales_received, period.price * account.sales_quantity)
        close(account.gross_operating_surplus, account.production_value - account.wage_bill)
        close(account.investment_value, firm.reinvestment_rate * account.gross_operating_surplus,
              account.production_value)
        close(account.investment_value, period.price * account.investment_quantity,
              account.production_value)
        close(account.depreciation_quantity, firm.depreciation_rate * account.capital_open,
              account.capital_open)
        close(account.depreciation_value, period.price * account.depreciation_quantity,
              period.price * account.capital_open)
        close(account.capital_close,
              account.capital_open - account.depreciation_quantity + account.investment_quantity)
        close(account.net_operating_profit,
              account.production_value - account.wage_bill - account.depreciation_value,
              account.production_value + account.depreciation_value)
        close(account.sales_received - account.wage_bill,
              (1 - firm.reinvestment_rate) * account.gross_operating_surplus)
        close(account.sales_share, account.sales_quantity / fsum(period.consumption.values()))
        close(account.production_share, account.output / period.output)

        # Certify the funded optimum against its marginal condition and feasible
        # alternative hiring choices at the actual common price and wage.
        marginal_product = period.price * account.output / (2 * account.work)
        assert account.wage_bill <= account.operating_cash * (1 + 3e-9)
        if account.wage_bill < account.operating_cash * (1 - 1e-7):
            close(marginal_product, period.wage)
        else:
            close(account.wage_bill, account.operating_cash)
            assert marginal_product >= period.wage * (1 - 3e-9)
        for fraction in (0, .1, .3, .5, .7, .9, 1):
            alternative_work = account.operating_cash / period.wage * fraction
            alternative_surplus = (
                period.price * firm.productivity * sqrt(account.capital_open * alternative_work)
                - period.wage * alternative_work
            )
            assert alternative_surplus <= account.gross_operating_surplus + 3e-9 * account.production_value

        close(account.capital_price_open, price_open)
        close(account.capital_price_close, period.price)
        close(account.capital_value_open, price_open * account.capital_open)
        close(account.capital_value_close, period.price * account.capital_close)
        close(account.holding_gain, (period.price - price_open) * account.capital_open,
              account.capital_value_open)
        close(account.capital_value_close - account.capital_value_open,
              account.investment_value - account.depreciation_value + account.holding_gain,
              account.capital_value_open + account.capital_value_close)
        close(account.equity_open, account.opening_cash + account.capital_value_open)
        close(account.equity_close, account.closing_cash + account.capital_value_close)
        close(account.equity_close - account.equity_open,
              account.net_operating_profit - account.dividends_paid + account.holding_gain,
              account.equity_open + account.equity_close)
        close(account.retained_earnings_open, prior.retained_earnings_close if prior else 0,
              account.equity_open)
        close(account.retained_earnings_close,
              account.retained_earnings_open + account.net_operating_profit - account.dividends_paid,
              account.equity_open + account.equity_close)
        close(account.revaluation_reserve_open, prior.revaluation_reserve_close if prior else 0,
              account.equity_open)
        close(account.revaluation_reserve_close,
              account.revaluation_reserve_open + account.holding_gain,
              account.equity_open + account.equity_close)
        close(account.equity_close, account.contributed_equity + account.retained_earnings_close
              + account.revaluation_reserve_close)
        close(account.contributed_equity,
              prior.contributed_equity if prior else firm.money + period.price * firm.capital)
        close(account.next_dividend_budget,
              min(max(account.net_operating_profit, 0), max(account.closing_cash - firm.money, 0)),
              money)
        events = {e.kind: e for e in period.events if e.entity_id == firm.id}
        for kind, amount in (("production", account.output),
                             ("capital_installation", account.investment_quantity),
                             ("capital_wear", account.depreciation_quantity)):
            if amount:
                close(events[kind].quantity, amount)
            elif kind in events:
                assert events[kind].quantity == 0
        if "revaluation" in events:
            close(events["revaluation"].value, account.holding_gain, account.capital_value_open)

    close(fsum(period.work.values()), fsum(a.work for a in period.firm_accounts.values()))
    close(period.output, fsum(period.consumption.values()) + period.investment_quantity)
    close(period.production_value - period.depreciation_value,
          fsum(period.wages.values()) + period.net_operating_profit,
          period.production_value + period.depreciation_value)
    saving = fsum(period.closing_cash[h.id] - period.opening_cash[h.id] for h in period.households)
    close(saving + period.net_operating_profit - period.dividends_paid,
          period.investment_value - period.depreciation_value,
          period.production_value + period.depreciation_value)
    close(fsum(period.closing_cash.values()), money)
    assert all(period.checks.values())


def test_equal_resource_split_matches_released_09_for_100_linked_periods():
    previous09 = previous10 = None
    for _ in range(100):
        old = advance_investment_period((Household09("Household 1"), Household09("Household 2")),
                                        Firm09(), previous09)
        new = advance_competition_period(HOUSEHOLDS, FIRMS, previous10)
        assert_economic_snapshot(new, previous10)
        for key in ("price", "wage", "output", "wage_bill", "production_value",
                    "net_operating_profit", "dividends_paid", "capital_close", "investment_quantity",
                    "depreciation_quantity", "equity_close", "holding_gain"):
            close(getattr(new, key), getattr(old, key), old.equity_open + old.equity_close)
        for hid, name in (("household_1", "Household 1"), ("household_2", "Household 2")):
            close(new.closing_cash[hid], old.closing_cash[name])
            close(new.consumption[hid], old.consumption[name])
            close(new.work[hid], old.work[name])
        for account in new.firm_accounts.values():
            close(account.output, old.output / 2)
            close(account.capital_close, old.capital_close / 2)
            close(account.closing_cash, old.closing_cash["Firm"] / 2)
        previous09, previous10 = old, new
    first = advance_competition_period(HOUSEHOLDS, FIRMS)
    close(first.wage, 13 / 11)
    close(first.price, (10 / 11) * sqrt(13 / 10))
    close(first.output, 2 * sqrt(10 / 13))


@pytest.mark.parametrize("case", ("slack", "one_capped", "both_capped", "unequal_productivity",
                                 "unequal_investment", "no_investment_or_wear", "near_boundary"))
def test_contrasting_linked_paths_satisfy_individual_optima_and_accounts(case):
    a, b = FIRMS
    firms = {
        "slack": (replace(a, money=1), replace(b, money=1)),
        "one_capped": (replace(a, money=.01), replace(b, money=.99)),
        "both_capped": (replace(a, money=.02), replace(b, money=.02)),
        "unequal_productivity": (replace(a, productivity=3), b),
        "unequal_investment": (replace(a, reinvestment_rate=.8), replace(b, reinvestment_rate=.2)),
        "no_investment_or_wear": tuple(replace(f, reinvestment_rate=0, depreciation_rate=0) for f in FIRMS),
        "near_boundary": (replace(a, reinvestment_rate=.99, depreciation_rate=.99), b),
    }[case]
    previous = None
    for period in periods_for(HOUSEHOLDS, firms, 8):
        assert_economic_snapshot(period, previous)
        if previous is None and case in ("slack", "one_capped", "both_capped"):
            observed = sum(a.wage_bill >= a.operating_cash * (1 - 1e-8)
                           for a in period.firm_accounts.values())
            assert observed == {"slack": 0, "one_capped": 1, "both_capped": 2}[case]
        previous = period


def test_zero_cash_worker_and_wealthy_nonworker_can_trade_with_both_firms():
    households = (replace(HOUSEHOLDS[0], money=100, leisure_priority=100),
                  replace(HOUSEHOLDS[1], money=0))
    period = advance_competition_period(households, FIRMS)
    assert period.work[households[0].id] == 0
    assert period.work[households[1].id] > 0
    assert all(a.consumption > 0 for a in period.allocations)
    assert_economic_snapshot(period)


def test_sales_shares_follow_sold_output_not_production_when_investment_differs():
    firms = (replace(FIRMS[0], money=1, reinvestment_rate=.8),
             replace(FIRMS[1], money=1, reinvestment_rate=.2))
    period = advance_competition_period(HOUSEHOLDS, firms)
    a, b = (period.firm_accounts[f.id] for f in firms)
    assert a.wage_bill < a.operating_cash and b.wage_bill < b.operating_cash
    close(a.output, b.output)
    close(a.production_share, .5)
    close(a.sales_share, .4)
    close(b.sales_share, .6)
    for allocation in period.allocations:
        close(allocation.consumption / period.consumption[allocation.household_id],
              .4 if allocation.firm_id == firms[0].id else .6)
    assert_economic_snapshot(period)


def test_firm_b_dividend_survives_firm_a_loss_and_uses_its_own_cash():
    firms = (replace(FIRMS[0], capital=100, depreciation_rate=.9), FIRMS[1])
    periods = periods_for(HOUSEHOLDS, firms, 2)
    first, second = periods
    a, b = (first.firm_accounts[f.id] for f in firms)
    assert a.net_operating_profit < 0 < b.net_operating_profit
    assert a.net_operating_profit + b.net_operating_profit < 0
    assert second.firm_accounts[firms[0].id].dividends_paid == 0
    close(second.firm_accounts[firms[1].id].dividends_paid, b.net_operating_profit)
    for transfer in second.transfers:
        if transfer.kind == "dividend":
            assert transfer.sender_id == firms[1].id
    assert_economic_snapshot(first)
    assert_economic_snapshot(second, first)


def test_currency_and_relative_priority_rescaling_leave_real_choices_unchanged():
    households = (replace(HOUSEHOLDS[0], money=.7, consumption_priority=3, money_priority=.4,
                          leisure_priority=2),
                  replace(HOUSEHOLDS[1], money=2.3, consumption_priority=.2, money_priority=4,
                          leisure_priority=.7))
    firms = (replace(FIRMS[0], money=.2, productivity=3), replace(FIRMS[1], money=.8))
    reference = periods_for(households, firms, 5)
    rescored = periods_for((replace(households[0], consumption_priority=30, money_priority=4,
                                   leisure_priority=20), households[1]), firms, 5)
    variants = [(1.0, rescored)]
    for factor in (1e-12, 1e12):
        variants.append((factor, periods_for(tuple(replace(h, money=h.money * factor) for h in households),
                                            tuple(replace(f, money=f.money * factor) for f in firms), 5)))
    for factor, periods in variants:
        previous = None
        for old, new in zip(reference, periods, strict=True):
            assert_economic_snapshot(new, previous)
            close(new.price / factor, old.price)
            close(new.wage / factor, old.wage)
            for hid in old.work:
                close(new.work[hid], old.work[hid])
                close(new.consumption[hid], old.consumption[hid])
            for fid in old.firm_accounts:
                a, b = old.firm_accounts[fid], new.firm_accounts[fid]
                for key in ("work", "output", "capital_open", "capital_close", "sales_quantity",
                            "investment_quantity", "depreciation_quantity", "sales_share"):
                    close(getattr(b, key), getattr(a, key))
                for key in ("opening_cash", "closing_cash", "dividends_paid", "net_operating_profit",
                            "wage_bill", "sales_received", "equity_close", "holding_gain"):
                    close(getattr(b, key) / factor, getattr(a, key), a.equity_open + a.equity_close)
            previous = new


def test_reordering_entities_and_duplicate_labels_preserve_id_keyed_outcomes():
    households = (replace(HOUSEHOLDS[0], name="Firm A", consumption_priority=3),
                  replace(HOUSEHOLDS[1], name="Firm A", money=2, leisure_priority=2))
    firms = (replace(FIRMS[0], productivity=3, money=.1), replace(FIRMS[1], money=.9))
    forward = periods_for(households, firms, 10)
    reverse = periods_for(tuple(reversed(households)), tuple(reversed(firms)), 10)
    previous = None
    for a, b in zip(forward, reverse, strict=True):
        assert_economic_snapshot(b, previous)
        close(a.price, b.price)
        close(a.wage, b.wage)
        for key in a.closing_cash:
            close(a.closing_cash[key], b.closing_cash[key])
        for fid, first in a.firm_accounts.items():
            second = b.firm_accounts[fid]
            for key in ("output", "work", "capital_close", "sales_quantity", "sales_share",
                        "net_operating_profit", "dividends_paid", "equity_close"):
                close(getattr(first, key), getattr(second, key), first.equity_open + first.equity_close)
        previous = b


def test_twenty_households_at_ui_bounds_keep_tiny_firm_and_paired_allocations():
    # This deliberately combines cashless households, wealthy nonworkers and
    # each preference extreme. One firm becomes many orders of magnitude smaller
    # without vanishing from the real accounts or the settled evidence.
    priorities = ((.01, 100, .01), (100, .01, .01), (.01, .01, 100), (1, 1, 1))
    households = tuple(
        Household(
            f"household_{i + 1}", f"Household {i + 1}",
            money=0 if i % 3 == 0 else 1_000_000,
            consumption_priority=priorities[i % 4][0],
            money_priority=priorities[i % 4][1],
            leisure_priority=priorities[i % 4][2],
        ) for i in range(20)
    )
    firms = (
        replace(FIRMS[0], money=.01, capital=.1, productivity=.1,
                reinvestment_rate=.9, depreciation_rate=.9),
        replace(FIRMS[1], money=1_000_000, capital=1_000_000, productivity=100,
                reinvestment_rate=0, depreciation_rate=0),
    )
    previous = None
    for period in periods_for(households, firms, 10):
        assert_economic_snapshot(period, previous)
        assert len(period.transfers) <= 200
        small = period.firm_accounts[firms[0].id]
        assert small.output > 0 and small.sales_quantity > 0 and small.sales_share > 0
        assert any(t.kind == "goods_delivery" and t.sender_id == firms[0].id
                   for t in period.transfers)
        previous = period
    assert previous.firm_accounts[firms[0].id].sales_share < 1e-15
