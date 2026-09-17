"""Independent optimality and funded accounting for the current model.

These tests reconstruct the agreed utility and budgets from public snapshots;
the production solver's intermediate answers and check flags are not oracles.
"""

from collections import defaultdict
from dataclasses import replace
from itertools import pairwise
from math import fsum, isfinite, log, sqrt

import pytest

from econ_agent_sim.engine import (
    Firm,
    Household,
    advance_period,
    household_choice,
)

HOUSEHOLDS = (Household("household_1", "Household 1"),
              Household("household_2", "Household 2"))
FIRMS = (Firm("firm_a", "Firm A"), Firm("firm_b", "Firm B"))


def close(actual, expected, scale=0.0):
    """No absolute monetary floor that could conceal currency-dependent errors."""
    assert isfinite(actual) and isfinite(expected)
    tolerance = 3e-9 * max(abs(actual), abs(expected), abs(scale), 1e-280)
    assert abs(actual - expected) <= tolerance, (actual, expected, scale)


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


def periods_for(households, firms, count):
    periods = []
    for _ in range(count):
        periods.append(advance_period(
            households, firms, periods[-1] if periods else None,
        ))
    return tuple(periods)


def utility(household, consumption, money, leisure):
    scores = (household.consumption_priority, household.money_priority,
              household.leisure_priority)
    a, d, g = (score / fsum(scores) for score in scores)
    result = a * log(consumption) + d * log(money) + g * log(leisure)
    target = household.consumption_target
    if 0 < consumption < target:
        ratio = consumption / target
        result -= ratio - 1 - log(ratio)
    return result


def certify_household_choices(period, *, check_grid=False):
    """Certify the concave household problem including the no-work corner."""
    for household in period.households:
        hid = household.id
        consumption, money = period.consumption[hid], period.closing_cash[hid]
        leisure, work = period.leisure[hid], period.work[hid]
        assert consumption > 0 and money > 0 and 0 < leisure <= 1
        assert 0 <= work < 1
        close(leisure, 1 - work)
        cash = period.opening_cash[hid] + period.dividends[hid]
        budget = cash + period.wage * work
        close(money + period.price * consumption, budget)
        scores = (household.consumption_priority, household.money_priority,
                  household.leisure_priority)
        a, d, g = (score / fsum(scores) for score in scores)
        target = household.consumption_target
        marginal_consumption = a / consumption
        if 0 < consumption < target:
            marginal_consumption += 1 / consumption - 1 / target
        marginal_money = d / money
        close(marginal_consumption, period.price * marginal_money)
        marginal_wages = period.wage * marginal_money
        marginal_leisure = g / leisure
        if work > 1e-9:
            close(marginal_wages, marginal_leisure)
        else:
            assert marginal_wages <= marginal_leisure * (1 + 3e-8)
        if not check_grid:
            continue
        achieved = utility(household, consumption, money, leisure)
        # Try feasible work and spending choices independently of all engine
        # demand helpers, including both sides of the consumption threshold.
        for other_work in (0, .01, .1, .3, .5, .7, .9, .99, .9999):
            available = cash + period.wage * other_work
            if available <= 0:
                continue
            for spent_fraction in (.001, .01, .1, .3, .5, .7, .9, .99, .999):
                other_consumption = available * spent_fraction / period.price
                other_money = available * (1 - spent_fraction)
                alternative = utility(household, other_consumption,
                                      other_money, 1 - other_work)
                assert alternative <= achieved + 2e-9


def certify_accounts(period, previous=None):
    assert isfinite(period.price) and period.price > 0
    assert isfinite(period.wage) and period.wage > 0
    money = fsum(period.opening_cash.values())
    assert min(period.closing_cash.values()) >= 0
    if previous:
        assert period.opening_cash == previous.closing_cash
    assert_funded_ledger(period)
    close(fsum(period.closing_cash.values()), money)
    close(fsum(period.work.values()), fsum(a.work for a in period.firm_accounts.values()))
    close(period.output, fsum(period.consumption.values()) + period.investment_quantity)
    close(period.production_value - period.depreciation_value,
          period.wage_bill + period.net_operating_profit,
          period.production_value + period.depreciation_value)
    for firm in period.firms:
        account = period.firm_accounts[firm.id]
        close(account.output, firm.productivity * sqrt(account.capital_open * account.work))
        close(account.wage_bill, period.wage * account.work)
        assert account.wage_bill <= account.operating_cash * (1 + 3e-9)
        marginal_revenue = period.price * account.output / (2 * account.work)
        if account.wage_bill < account.operating_cash * (1 - 1e-7):
            close(marginal_revenue, period.wage)
        else:
            assert marginal_revenue >= period.wage * (1 - 3e-9)
        close(account.capital_close, account.capital_open * (1 - firm.depreciation_rate)
              + account.investment_quantity)
        close(account.sales_quantity + account.investment_quantity, account.output)
        close(account.equity_close - account.equity_open,
              account.net_operating_profit - account.dividends_paid + account.holding_gain,
              account.equity_open + account.equity_close)
    assert all(period.checks.values())


def test_zero_targets_remain_optimal_and_funded_over_100_linked_periods():
    households = (
        replace(HOUSEHOLDS[0], money=.7, consumption_priority=3, money_priority=.4,
                leisure_priority=2, consumption_target=0),
        replace(HOUSEHOLDS[1], money=2.3, consumption_priority=.2, money_priority=4,
                leisure_priority=.7, consumption_target=0),
    )
    firms = (replace(FIRMS[0], money=.2, productivity=3), replace(FIRMS[1], money=.8))
    previous = None
    for period in periods_for(households, firms, 100):
        certify_household_choices(period, check_grid=period.number in (1, 100))
        certify_accounts(period, previous)
        previous = period


@pytest.mark.parametrize("target,price,wage,work,consumption,money", (
    (.5, 1.036523113726489, 1.1818181818181817, .38461538461538447,
     .7016464154456233, .7272727272727273),
    (1, 1.2903398715616203, 1.0413072843170306, .4801656605407679,
     .7429768984219033, .5413072843170303),
    (2, 1.4300838102605546, .8909572503712235, .5611941535821967,
     .775508918898057, .3909572503712234),
    (100, 1.489896010644106, .8014550307187263, .6238653209920108,
     .8044487405286249, .30145503071872626),
))
def test_symmetric_equilibrium_matches_independently_derived_anchors(
    target, price, wage, work, consumption, money,
):
    households = tuple(replace(h, consumption_target=target) for h in HOUSEHOLDS)
    period = advance_period(households, FIRMS)
    close(period.price, price)
    close(period.wage, wage)
    for household in households:
        close(period.work[household.id], work)
        close(period.consumption[household.id], consumption)
        close(period.closing_cash[household.id], money)
    close(period.firm_accounts["firm_a"].sales_share, .5)


def test_isolated_choice_anchors_and_increasing_target_at_fixed_prices():
    household = replace(HOUSEHOLDS[0], consumption_target=1)
    chosen = household_choice(household, available_cash=1, price=1, wage=1)
    close(chosen["work"], 1 - 1 / sqrt(3))
    close(chosen["consumption"], 2 - 2 / sqrt(3))
    close(chosen["money"], 1 / sqrt(3))
    close(chosen["leisure"], 1 / sqrt(3))
    rested = household_choice(replace(household, consumption_target=5),
                              available_cash=5, price=1, wage=1)
    assert rested["work"] == 0
    close(rested["consumption"], 10 / 3)
    close(rested["money"], 5 / 3)
    choices = [household_choice(replace(household, consumption_target=target),
                                available_cash=1, price=1, wage=1)
               for target in (0, .1, 2 / 3, 1, 2, 100, 1e9)]
    assert all(right["consumption"] >= left["consumption"] - 1e-12
               for left, right in pairwise(choices))
    assert all(0 <= choice["work"] < 1 and choice["money"] > 0 for choice in choices)
    # At an unreachable target the finite bonus tends to one extra log(C)
    # coefficient: the optimum remains interior, without spending every penny.
    close(choices[-1]["consumption"], 4 / 3)
    close(choices[-1]["money"], 1 / 3)
    close(choices[-1]["work"], 2 / 3)


@pytest.mark.parametrize("case", ("above_target", "below_target", "mixed_targets",
                                 "cashless_worker", "wealthy_nonworker", "unequal_firms"))
def test_individual_optimality_and_funded_accounts_across_household_and_firm_cases(case):
    households = {
        "above_target": tuple(replace(h, consumption_target=.01) for h in HOUSEHOLDS),
        "below_target": tuple(replace(h, consumption_target=10) for h in HOUSEHOLDS),
        "mixed_targets": (replace(HOUSEHOLDS[0], consumption_target=2),
                          replace(HOUSEHOLDS[1], consumption_target=0)),
        "cashless_worker": (replace(HOUSEHOLDS[0], money=0, consumption_target=2),
                            replace(HOUSEHOLDS[1], consumption_target=.01)),
        "wealthy_nonworker": (replace(HOUSEHOLDS[0], money=100, leisure_priority=100),
                               replace(HOUSEHOLDS[1], money=0, consumption_target=3)),
        "unequal_firms": tuple(replace(h, consumption_target=2) for h in HOUSEHOLDS),
    }[case]
    firms = ((replace(FIRMS[0], money=.01, productivity=3, reinvestment_rate=.8),
              replace(FIRMS[1], money=.99, reinvestment_rate=.2))
             if case == "unequal_firms" else FIRMS)
    previous = None
    for period in periods_for(households, firms, 12):
        certify_household_choices(period, check_grid=period.number in (1, 12))
        certify_accounts(period, previous)
        previous = period


def test_low_productivity_high_wear_shortfalls_continue_without_cash_exhaustion():
    households = tuple(replace(h, consumption_target=10) for h in HOUSEHOLDS)
    firms = tuple(replace(f, capital=100, productivity=.1, depreciation_rate=.9)
                  for f in FIRMS)
    previous = None
    for period in periods_for(households, firms, 100):
        certify_household_choices(period, check_grid=period.number in (1, 100))
        certify_accounts(period, previous)
        assert all(period.consumption[h.id] < h.consumption_target for h in households)
        assert all(period.closing_cash[h.id] > 0 for h in households)
        previous = period


def test_currency_units_and_priority_rescaling_preserve_real_choices():
    households = (replace(HOUSEHOLDS[0], consumption_target=1.5, consumption_priority=3,
                          money_priority=.4, leisure_priority=2),
                  replace(HOUSEHOLDS[1], money=2.3, consumption_target=.1))
    firms = (replace(FIRMS[0], money=.2, productivity=3), replace(FIRMS[1], money=.8))
    reference = periods_for(households, firms, 5)
    rescored = (replace(households[0], consumption_priority=30, money_priority=4,
                        leisure_priority=20), households[1])
    variants = [(1, periods_for(rescored, firms, 5))]
    for factor in (1e-12, 1e12):
        variants.append((factor, periods_for(
            tuple(replace(h, money=h.money * factor) for h in households),
            tuple(replace(f, money=f.money * factor) for f in firms), 5,
        )))
    for factor, periods in variants:
        for old, new in zip(reference, periods, strict=True):
            close(new.price / factor, old.price)
            close(new.wage / factor, old.wage)
            for h in households:
                close(new.work[h.id], old.work[h.id])
                close(new.consumption[h.id], old.consumption[h.id])
                close(new.closing_cash[h.id] / factor, old.closing_cash[h.id])


def test_goods_units_rescale_quantities_and_targets_without_changing_behavior():
    households = tuple(replace(h, consumption_target=2) for h in HOUSEHOLDS)
    reference = periods_for(households, FIRMS, 5)
    for factor in (.001, 1000):
        rescaled_households = tuple(replace(h, consumption_target=h.consumption_target * factor)
                                    for h in households)
        rescaled_firms = tuple(replace(f, capital=f.capital * factor,
                                      productivity=f.productivity * sqrt(factor)) for f in FIRMS)
        rescaled = periods_for(rescaled_households, rescaled_firms, 5)
        for old, new in zip(reference, rescaled, strict=True):
            close(new.price * factor, old.price)
            close(new.wage, old.wage)
            close(new.output / factor, old.output)
            close(new.capital_close / factor, old.capital_close)
            for h in households:
                close(new.work[h.id], old.work[h.id])
                close(new.consumption[h.id] / factor, old.consumption[h.id])
                close(new.closing_cash[h.id], old.closing_cash[h.id])


def test_order_and_duplicate_labels_do_not_change_household_or_firm_allocations():
    households = (replace(HOUSEHOLDS[0], name="Same", consumption_target=2),
                  replace(HOUSEHOLDS[1], name="Same", consumption_target=.1, money=3))
    firms = (replace(FIRMS[0], name="Same", productivity=3),
             replace(FIRMS[1], name="Same", reinvestment_rate=.8))
    forward = periods_for(households, firms, 5)
    reversed_run = periods_for(tuple(reversed(households)), tuple(reversed(firms)), 5)
    for old, new in zip(forward, reversed_run, strict=True):
        close(new.price, old.price)
        close(new.wage, old.wage)
        for field in ("work", "consumption", "closing_cash"):
            for key, value in getattr(old, field).items():
                close(getattr(new, field)[key], value, fsum(old.opening_cash.values()))
        for firm in firms:
            close(new.firm_accounts[firm.id].sales_share, old.firm_accounts[firm.id].sales_share)
