"""Independent checks of the conditional user-cost investment problem.

These certify a capital-target rule at given forecast prices and payroll cash;
they do not claim lifetime-dividend or representative-household optimality.
"""

from dataclasses import replace
from itertools import pairwise
from math import sqrt

import pytest

from econ_agent_sim.domain import Firm
from econ_agent_sim.investment import (
    certify_investment,
    investment_bounds,
    investment_value,
)


def market_inputs(firm, capital, *, funding=1.0, price=1.0, wage=1.0):
    labor = min(
        (price * firm.productivity / (2 * wage)) ** 2 * capital,
        funding / wage,
    )
    output = firm.productivity * sqrt(capital * labor)
    return firm, capital, price * output, wage * labor, funding, price, wage


def reference_objective(arguments, investment_money):
    firm, capital, _, _, funding, price, wage = arguments
    real_wage, cash = wage / price, funding / price
    next_capital = (1 - firm.depreciation_rate) * capital + investment_money / price
    # Independently optimize future labor, not the production investment helper.
    future_labor = min(
        (firm.productivity / (2 * real_wage)) ** 2 * next_capital,
        cash / real_wage,
    )
    surplus = firm.productivity * sqrt(next_capital * future_labor) - real_wage * future_labor
    return surplus - (firm.required_return + firm.depreciation_rate) * next_capital


@pytest.fixture
def forward_firm():
    return Firm(
        "f", "Firm", productivity=2.0, reinvestment_rate=.9,
        depreciation_rate=.1, investment_policy="user_cost", required_return=.4,
    )


@pytest.mark.parametrize("capital,expected_investment", (
    (1.0, .9),  # Funding budget, below the desired capital stock.
    (3.0, 1.3),  # Interior expansion to K_next=4.
    (4.0, .4),  # Exactly replace depreciation at the target.
    (6.0, 0.0),  # Cannot sell existing capital to reach a lower target.
))
def test_independently_derived_capital_target_anchors(
    forward_firm, capital, expected_investment,
):
    arguments = market_inputs(forward_firm, capital)
    selected = investment_value(*arguments)
    lower, upper = investment_bounds(*arguments)
    assert selected == pytest.approx(expected_investment, abs=1e-12)
    assert lower == pytest.approx(selected, abs=1e-12)
    assert upper == pytest.approx(selected, abs=1e-12)
    assert certify_investment(*arguments, selected_value=selected)


@pytest.mark.parametrize("capital", (.1, .5, 1.0, 3.0, 10.0))
@pytest.mark.parametrize("required_return", (0.0, .05, .4, .9, 1.0))
def test_selected_capital_beats_independent_feasible_investment_grid(
    forward_firm, capital, required_return,
):
    firm = replace(forward_firm, required_return=required_return)
    arguments = market_inputs(firm, capital)
    selected = investment_value(*arguments)
    budget = firm.reinvestment_rate * (arguments[2] - arguments[3])
    assert -1e-12 <= selected <= budget + 1e-12
    achieved = reference_objective(arguments, selected)
    for index in range(501):
        alternative = reference_objective(arguments, budget * index / 500)
        assert alternative <= achieved + 2e-12 * max(1.0, abs(achieved))


def test_flat_optimum_returns_the_whole_feasible_indifference_interval(forward_firm):
    firm = replace(forward_firm, required_return=.9)  # gamma=cost=1.
    arguments = market_inputs(firm, .8)
    lower, upper = investment_bounds(*arguments)
    assert lower == 0.0
    assert upper == pytest.approx(.28)  # The funding kink is at next K=1.
    assert investment_value(*arguments) == lower
    for selected in (lower, .14, upper):
        assert certify_investment(*arguments, selected_value=selected)
        assert reference_objective(arguments, selected) == pytest.approx(0.0, abs=1e-14)
    assert not certify_investment(*arguments, selected_value=upper + .001)
    assert not certify_investment(*arguments, selected_value=-.001)


def test_flat_optimum_is_limited_by_both_the_budget_and_capital_kink(forward_firm):
    firm = replace(forward_firm, required_return=.9)
    arguments = market_inputs(firm, .5)
    assert investment_bounds(*arguments) == pytest.approx((0.0, .45))
    arguments = market_inputs(firm, 2.0)
    assert investment_bounds(*arguments) == pytest.approx((0.0, 0.0))


def test_nearby_nonflat_cases_are_not_mistaken_for_exact_indifference(forward_firm):
    for required_return, should_invest in ((.9 - 1e-6, True), (.9 + 1e-6, False)):
        arguments = market_inputs(replace(forward_firm, required_return=required_return), .8)
        lower, upper = investment_bounds(*arguments)
        assert upper == pytest.approx(lower, abs=1e-12)
        assert (lower > 0) is should_invest


def test_zero_user_cost_uses_the_precommitted_budget_not_all_surplus(forward_firm):
    firm = replace(forward_firm, depreciation_rate=0.0, required_return=0.0,
                   reinvestment_rate=.4)
    arguments = market_inputs(firm, 3.0)
    surplus = arguments[2] - arguments[3]
    selected = investment_value(*arguments)
    assert selected == pytest.approx(.4 * surplus)
    assert selected < surplus
    assert investment_bounds(*arguments) == pytest.approx((selected, selected))


def test_zero_budget_allows_only_zero_investment(forward_firm):
    arguments = market_inputs(replace(forward_firm, reinvestment_rate=0.0), 3.0)
    assert investment_value(*arguments) == 0
    assert investment_bounds(*arguments) == (0.0, 0.0)
    assert certify_investment(*arguments, selected_value=0.0)
    assert not certify_investment(*arguments, selected_value=.001)


def test_required_return_reduces_investment_at_fixed_forecast_prices(forward_firm):
    choices = [
        investment_value(*market_inputs(replace(forward_firm, required_return=rate), 3.0))
        for rate in (0.0, .1, .2, .4, .6, .8, 1.0)
    ]
    assert all(right <= left + 1e-12 for left, right in pairwise(choices))


@pytest.mark.parametrize("factor", (1e-9, 1e9))
def test_currency_rescaling_preserves_real_investment(forward_firm, factor):
    reference = investment_value(*market_inputs(forward_firm, 3.0))
    arguments = market_inputs(
        replace(forward_firm, money=forward_firm.money * factor), 3.0,
        funding=factor, price=factor, wage=factor,
    )
    assert investment_value(*arguments) / factor == pytest.approx(reference, rel=2e-9)


@pytest.mark.parametrize("factor", (.001, 1000.0))
def test_goods_rescaling_preserves_nominal_investment(forward_firm, factor):
    reference = investment_value(*market_inputs(forward_firm, 3.0))
    firm = replace(forward_firm, productivity=forward_firm.productivity * sqrt(factor),
                   capital=forward_firm.capital * factor)
    arguments = market_inputs(firm, 3.0 * factor, price=1 / factor)
    assert investment_value(*arguments) == pytest.approx(reference, rel=2e-9)


def test_percentage_policy_retains_its_exact_existing_formula(forward_firm):
    firm = replace(forward_firm, investment_policy="percentage", reinvestment_rate=.4)
    arguments = market_inputs(firm, 3.0)
    expected = firm.reinvestment_rate * (arguments[2] - arguments[3])
    assert investment_value(*arguments) == expected
    assert investment_bounds(*arguments) == (expected, expected)
    assert certify_investment(*arguments, selected_value=expected)
    assert not certify_investment(*arguments, selected_value=expected / 2)


@pytest.mark.parametrize("required_return", (-.1, 1.1, float("inf"), float("nan")))
def test_invalid_required_return_is_rejected(required_return):
    with pytest.raises(ValueError):
        Firm("f", "F", investment_policy="user_cost", required_return=required_return)


def test_unknown_investment_policy_is_rejected():
    with pytest.raises(ValueError):
        Firm("f", "F", investment_policy="lifetime_optimal")
