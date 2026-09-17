"""Independent funded accounting and conditional investment in integrated runs."""

from dataclasses import replace
from math import fsum, sqrt

import pytest
from test_engine_acceptance import certify_accounts, certify_household_choices
from test_investment import reference_objective

from econ_agent_sim.domain import Firm, Household
from econ_agent_sim.engine import advance_period
from econ_agent_sim.reporting import build_report


def setup(*, mixed=False, target=.5):
    households = (
        Household("h1", "Household 1", consumption_target=target),
        Household("h2", "Household 2", consumption_target=target),
    )
    firms = (
        Firm("f1", "Firm 1", investment_policy="user_cost"),
        Firm("f2", "Firm 2", investment_policy="percentage" if mixed else "user_cost"),
    )
    return households, firms


def certify_conditional_investment(period):
    for firm in period.firms:
        account = period.firm_accounts[firm.id]
        budget = firm.reinvestment_rate * account.gross_operating_surplus
        assert 0 <= account.investment_value <= budget * (1 + 3e-9)
        assert account.operating_cash >= firm.money * (1 - 3e-9)
        assert account.closing_cash >= account.operating_cash * (1 - 3e-9)
        assert account.sales_received - account.wage_bill == pytest.approx(
            account.gross_operating_surplus - account.investment_value, rel=3e-9,
        )
        if firm.investment_policy == "percentage":
            assert account.investment_value == pytest.approx(budget, rel=3e-9)
            continue
        arguments = (
            firm, account.capital_open, account.production_value,
            account.wage_bill, account.operating_cash, period.price, period.wage,
        )
        selected = reference_objective(arguments, account.investment_value)
        for index in range(101):
            alternative = reference_objective(arguments, budget * index / 100)
            assert alternative <= selected + 3e-9 * max(1.0, abs(selected))
        assert period.solution["investment_values"][firm.id] == pytest.approx(
            account.investment_value, rel=3e-9,
        )


@pytest.mark.parametrize("mixed,target,required_return", (
    (False, 0.0, .05), (False, 1.0, .05), (True, .5, .05),
    (False, 0.0, .75), (True, 1.0, .9),
))
def test_forward_and_mixed_economies_reconcile_over_ten_linked_periods(
    mixed, target, required_return,
):
    households, firms = setup(mixed=mixed, target=target)
    firms = tuple(replace(firm, required_return=required_return) for firm in firms)
    previous = None
    periods = []
    for _ in range(10):
        period = advance_period(households, firms, previous)
        certify_household_choices(period, check_grid=previous is None)
        certify_accounts(period, previous)
        certify_conditional_investment(period)
        assert fsum(period.closing_cash.values()) == pytest.approx(3.0)
        periods.append(period)
        previous = period
    report = build_report(periods, cumulative=True)
    assert all(report["checks"].values())


def test_high_required_return_can_withhold_a_positive_internal_budget():
    households, firms = setup(target=0.0)
    firms = tuple(replace(firm, required_return=.9) for firm in firms)
    period = advance_period(households, firms)
    certify_household_choices(period)
    certify_accounts(period)
    certify_conditional_investment(period)
    for account in period.firm_accounts.values():
        assert account.gross_operating_surplus > 0
        assert account.investment_value == 0


def test_capital_target_can_select_interior_investment_in_a_cleared_economy():
    households, firms = setup(target=0.0)
    firms = tuple(replace(firm, required_return=.75) for firm in firms)
    period = advance_period(households, firms)
    certify_household_choices(period)
    certify_accounts(period)
    certify_conditional_investment(period)
    assert any(
        0 < period.firm_accounts[firm.id].investment_value
        < firm.reinvestment_rate * period.firm_accounts[firm.id].gross_operating_surplus
        for firm in firms
    )


@pytest.mark.parametrize("wealthy_nonworker", (False, True))
def test_heterogeneous_cash_constrained_economies_keep_household_and_firm_optimality(
    wealthy_nonworker,
):
    if wealthy_nonworker:
        households = (
            Household("h1", "H1", money=100.0, leisure_priority=100.0),
            Household("h2", "H2", money=0.0, consumption_target=2.0),
        )
        firms = (
            Firm("f1", "F1", money=.01, productivity=3.0,
                 investment_policy="user_cost", required_return=.8),
            Firm("f2", "F2", money=.99, investment_policy="percentage"),
        )
    else:
        households = (
            Household("h1", "H1", money=0.0, consumption_target=2.0),
            Household("h2", "H2", money=2.0, consumption_target=.1),
        )
        firms = (
            Firm("f1", "F1", investment_policy="user_cost", required_return=.8),
            Firm("f2", "F2", money=.1, investment_policy="user_cost"),
        )
    previous = None
    for _ in range(5):
        period = advance_period(households, firms, previous)
        certify_household_choices(period, check_grid=previous is None)
        certify_accounts(period, previous)
        certify_conditional_investment(period)
        previous = period
    assert any(account.funding_binding for account in period.firm_accounts.values())
    if wealthy_nonworker:
        assert period.work["h1"] == 0


def test_zero_user_cost_with_limited_budget_has_a_funded_clearing_outcome():
    households, firms = setup(target=0.0)
    firms = tuple(replace(firm, depreciation_rate=0.0, required_return=0.0)
                  for firm in firms)
    period = advance_period(households, firms)
    certify_household_choices(period)
    certify_accounts(period)
    certify_conditional_investment(period)
    for account in period.firm_accounts.values():
        assert account.investment_value == pytest.approx(.4 * account.gross_operating_surplus)
        assert account.sales_received > account.wage_bill


def test_zero_budget_forward_policy_matches_no_investment_benchmark():
    households, firms = setup(target=0.0)
    forward = tuple(replace(firm, reinvestment_rate=0.0) for firm in firms)
    benchmark = tuple(replace(firm, investment_policy="percentage") for firm in forward)
    actual = advance_period(households, forward)
    reference = advance_period(households, benchmark)
    assert actual.price == pytest.approx(reference.price, rel=3e-9)
    assert actual.wage == pytest.approx(reference.wage, rel=3e-9)
    assert actual.investment_value == reference.investment_value == 0
    for household in households:
        key = household.id
        assert actual.consumption[key] == pytest.approx(reference.consumption[key], rel=3e-9)
        assert actual.work[key] == pytest.approx(reference.work[key], rel=3e-9)


@pytest.mark.parametrize("factor", (.001, 1000.0))
def test_forward_equilibrium_is_invariant_to_currency_units(factor):
    households, firms = setup(mixed=True, target=1.0)
    reference = advance_period(households, firms)
    changed = advance_period(
        tuple(replace(household, money=household.money * factor) for household in households),
        tuple(replace(firm, money=firm.money * factor) for firm in firms),
    )
    assert changed.price / factor == pytest.approx(reference.price, rel=3e-8)
    assert changed.wage / factor == pytest.approx(reference.wage, rel=3e-8)
    for household in households:
        key = household.id
        assert changed.work[key] == pytest.approx(reference.work[key], rel=3e-8)
        assert changed.consumption[key] == pytest.approx(reference.consumption[key], rel=3e-8)
    for firm in firms:
        actual, expected = changed.firm_accounts[firm.id], reference.firm_accounts[firm.id]
        assert actual.investment_quantity == pytest.approx(expected.investment_quantity,
                                                            rel=3e-8, abs=1e-12)


def test_reordering_and_duplicate_labels_do_not_change_forward_allocations():
    households, firms = setup(mixed=True, target=1.0)
    households = tuple(replace(household, name="Same") for household in households)
    firms = tuple(replace(firm, name="Same") for firm in firms)
    period = advance_period(households, firms)
    reversed_period = advance_period(households[::-1], firms[::-1])
    assert period.transfers == reversed_period.transfers
    assert period.firm_accounts == reversed_period.firm_accounts


@pytest.mark.parametrize("factor", (.01, 100.0))
def test_forward_equilibrium_is_invariant_to_physical_goods_units(factor):
    households, firms = setup(mixed=True, target=.5)
    reference = advance_period(households, firms)
    changed = advance_period(
        tuple(replace(household, consumption_target=household.consumption_target * factor)
              for household in households),
        tuple(replace(firm, productivity=firm.productivity * sqrt(factor),
                      capital=firm.capital * factor) for firm in firms),
    )
    assert changed.price * factor == pytest.approx(reference.price, rel=3e-8)
    assert changed.wage == pytest.approx(reference.wage, rel=3e-8)
    assert changed.output / factor == pytest.approx(reference.output, rel=3e-8)
    assert changed.capital_close / factor == pytest.approx(reference.capital_close, rel=3e-8)
    for household in households:
        key = household.id
        assert changed.work[key] == pytest.approx(reference.work[key], rel=3e-8)
        assert changed.consumption[key] / factor == pytest.approx(reference.consumption[key],
                                                                 rel=3e-8)
    for firm in firms:
        actual, expected = changed.firm_accounts[firm.id], reference.firm_accounts[firm.id]
        assert actual.investment_quantity / factor == pytest.approx(expected.investment_quantity,
                                                                    rel=3e-8, abs=1e-12)


def test_explicit_percentage_settings_preserve_published_first_period_anchor():
    households, firms = setup(target=0.0)
    firms = tuple(replace(firm, investment_policy="percentage") for firm in firms)
    period = advance_period(households, firms)
    assert period.price == 1.036523113726489
    assert period.wage == 1.1818181818181817
    assert period.consumption["h1"] == pytest.approx(.8 * sqrt(10 / 13))


@pytest.mark.parametrize("change", (
    {"investment_policy": "percentage"},
    {"required_return": .8},
    {"reinvestment_rate": .8},
))
def test_investment_policy_change_requires_restart_and_preserves_prior_snapshot(change):
    households, firms = setup()
    period = advance_period(households, firms)
    original = dict(period.closing_cash)
    with pytest.raises(ValueError, match="Restart"):
        advance_period(
            households,
            (replace(firms[0], **change), firms[1]), period,
        )
    assert dict(period.closing_cash) == original
