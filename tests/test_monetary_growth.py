"""Independent economic and settlement checks for the interior monetary branch.

These oracles use the household budgets, production function and supporting
plane inequality.  They do not call private numerical/reference helpers.
"""

from dataclasses import replace
from itertools import pairwise
from math import isfinite, sqrt

import pytest

from econ_agent_sim.monetary_growth import (
    Parameters,
    firm_deviation_gap,
    settle_period,
    solve_transition,
    steady_state,
)


def _stationary_values(params):
    marginal_product = 1 / params.beta - 1 + params.depreciation
    capital_per_worker = (.5 / marginal_product) ** 2
    real_wage = params.beta * .5 * sqrt(capital_per_worker)
    consumption_per_worker = (
        sqrt(capital_per_worker) - params.depreciation * capital_per_worker
    )
    labor = real_wage / (
        real_wage + params.leisure_weight * consumption_per_worker
    )
    capital = capital_per_worker * labor
    output = sqrt(capital * labor)
    consumption = output - params.depreciation * capital
    firm_cash = .5 * (1 - params.beta) / (1 - params.beta + params.money_weight)
    price = firm_cash / consumption
    money_wage = price * real_wage
    return {
        "capital": capital,
        "next_capital": capital,
        "output": output,
        "consumption": consumption,
        "investment": params.depreciation * capital,
        "labor": labor,
        "goods_price": price,
        "money_wage": money_wage,
        "distribution": firm_cash - money_wage * labor,
        "household_cash": .5 - firm_cash,
        "next_household_cash": .5 - firm_cash,
        "firm_cash": firm_cash,
        "next_firm_cash": firm_cash,
        "discount_factor": params.beta,
        "funding_multiplier": 1 - params.beta,
        "capital_shadow_value": price,
    }


def _assert_period_equations(params, row):
    assert row.capital > 0 and row.next_capital > 0
    assert 0 < row.labor < 1
    assert row.consumption > 0 and 0 < row.investment < row.output
    assert row.distribution > 0
    assert row.household_cash > 0 and row.firm_cash > 0
    assert row.next_household_cash > 0 and row.next_firm_cash > 0
    assert row.goods_price > 0 and row.money_wage > 0
    payroll = row.money_wage * row.labor
    spending = row.goods_price * row.consumption
    assert row.output == pytest.approx(sqrt(row.capital * row.labor), rel=2e-10)
    assert row.consumption + row.investment == pytest.approx(row.output, rel=2e-9)
    assert row.next_capital == pytest.approx(
        (1 - params.depreciation) * row.capital + row.investment, rel=2e-9,
    )
    assert row.distribution + payroll == pytest.approx(row.firm_cash, abs=2e-10)
    assert row.next_household_cash == pytest.approx(
        row.household_cash + payroll + row.distribution - spending, abs=2e-10,
    )
    assert row.next_firm_cash == pytest.approx(
        row.firm_cash - row.distribution - payroll
        + row.goods_price * (row.output - row.investment), abs=2e-10,
    )
    assert 2 * (row.household_cash + row.firm_cash) == pytest.approx(1.0, abs=2e-10)
    assert 2 * (row.next_household_cash + row.next_firm_cash) == pytest.approx(
        1.0, abs=2e-10,
    )
    # The household trades leisure against after-payment consumption spending.
    assert params.leisure_weight / (1 - row.labor) == pytest.approx(
        row.money_wage / spending, rel=2e-8,
    )
    # The prefunding restriction reduces the wage below the marginal product.
    marginal_labor = .5 * row.output / row.labor
    assert row.money_wage / row.goods_price == pytest.approx(
        params.beta * marginal_labor, rel=2e-8,
    )
    assert row.funding_multiplier >= 0
    assert row.funding_multiplier * (row.firm_cash - row.distribution - payroll) == (
        pytest.approx(0.0, abs=2e-10)
    )
    assert row.discount_factor + row.funding_multiplier == pytest.approx(1.0)
    assert row.discount_factor * (row.goods_price * marginal_labor - row.money_wage) == (
        pytest.approx(row.funding_multiplier * row.money_wage, rel=2e-8)
    )
    assert row.capital_shadow_value == pytest.approx(
        params.beta * row.goods_price
        * (1 - params.depreciation + .5 * row.output / row.capital), rel=2e-8,
    )


def _assert_intertemporal_equations(params, periods):
    for current, following in pairwise(periods):
        assert following.capital == pytest.approx(current.next_capital, rel=2e-10)
        assert following.household_cash == pytest.approx(current.next_household_cash)
        assert following.firm_cash == pytest.approx(current.next_firm_cash)
        current_lambda = 1 / (current.goods_price * current.consumption)
        next_lambda = 1 / (following.goods_price * following.consumption)
        assert current_lambda == pytest.approx(
            params.money_weight / current.next_household_cash
            + params.beta * next_lambda, rel=2e-8,
        )
        assert current.discount_factor == pytest.approx(
            params.beta * next_lambda / current_lambda, rel=2e-8,
        )
        # Interior investment equalizes next-period capital and cash values.
        assert following.capital_shadow_value == pytest.approx(
            current.goods_price, rel=2e-8,
        )


def test_stationary_solution_matches_the_documented_cash_and_real_fixture():
    params = Parameters()
    row = steady_state(params)
    for field, expected in _stationary_values(params).items():
        assert getattr(row, field) == pytest.approx(expected, rel=2e-12)
    for field, expected in {
        "capital": 4.442472602917,
        "labor": .413974455297,
        "output": 1.356123215627,
        "consumption": .911875955336,
        "investment": .444247260292,
        "goods_price": .274160096598,
        "money_wage": .426602564103,
        "distribution": .073397435897,
    }.items():
        assert getattr(row, field) == pytest.approx(expected, abs=6e-13)
    _assert_period_equations(params, row)
    _assert_intertemporal_equations(params, (row, row))


@pytest.mark.parametrize("initial_capital", (1.0, 2.0, 6.0, 10.0))
def test_transition_satisfies_budgets_optimality_and_endogenous_owner_valuation(
    initial_capital,
):
    params = Parameters()
    result = solve_transition(params, initial_capital, 40)
    assert result.converged, result.status
    assert result.parameters == params
    assert result.initial_capital == initial_capital
    assert result.initial_firm_cash_share == .5
    assert result.failure_period is None
    assert len(result.periods) == 40
    assert [row.number for row in result.periods] == list(range(1, 41))
    assert result.periods[0].capital == initial_capital
    assert result.periods[0].firm_cash == .25
    assert result.periods[0].household_cash == .25
    for row in result.periods:
        _assert_period_equations(params, row)
    _assert_intertemporal_equations(params, result.periods)


@pytest.mark.parametrize("beta,depreciation,leisure_weight,money_weight", (
    (.9, .4, 2.0, .12),
    (.8, 1.0, .5, .1),
    (.97, .25, 1.4, .2),
))
def test_nondefault_parameters_have_certified_stationary_and_transition_paths(
    beta, depreciation, leisure_weight, money_weight,
):
    params = Parameters(beta, depreciation, leisure_weight, money_weight)
    expected = _stationary_values(params)
    for field, value in expected.items():
        assert getattr(steady_state(params), field) == pytest.approx(value, rel=2e-12)
    result = solve_transition(
        params, .8 * expected["capital"], 30,
        initial_firm_cash_share=2 * expected["firm_cash"],
    )
    assert result.converged, result.status
    for row in result.periods:
        _assert_period_equations(params, row)
    _assert_intertemporal_equations(params, result.periods)


@pytest.mark.parametrize("beta,leisure_weight", ((.95, 1.0), (.8, 2.2)))
def test_full_depreciation_matches_independently_derived_exact_policy(beta, leisure_weight):
    params = Parameters(beta=beta, depreciation=1.0, leisure_weight=leisure_weight)
    result = solve_transition(
        params, 1.0, 24,
        initial_firm_cash_share=2 * _stationary_values(params)["firm_cash"],
    )
    assert result.converged, result.status
    optimal_labor = .5 / (.5 + leisure_weight / beta * (1 - .5 * beta))
    capital = 1.0
    for row in result.periods:
        output = sqrt(capital * optimal_labor)
        assert row.capital == pytest.approx(capital, rel=2e-7)
        assert row.labor == pytest.approx(optimal_labor, rel=2e-7)
        assert row.consumption == pytest.approx((1 - .5 * beta) * output, rel=2e-7)
        assert row.investment == pytest.approx(.5 * beta * output, rel=2e-7)
        assert row.next_capital == pytest.approx(row.investment, rel=2e-10)
        capital = .5 * beta * output


def test_stationary_initial_allocation_stays_stationary_and_uses_owner_shadow_values():
    params = Parameters(money_weight=.2)
    expected = _stationary_values(params)
    result = solve_transition(
        params, expected["capital"], 24,
        initial_firm_cash_share=2 * expected["firm_cash"],
    )
    assert result.converged, result.status
    for row in result.periods:
        for field, value in expected.items():
            assert getattr(row, field) == pytest.approx(value, rel=2e-8)


def test_money_services_change_cash_and_prices_but_not_real_path_on_this_branch():
    low = solve_transition(Parameters(), 2.0, 24)
    high = solve_transition(Parameters(money_weight=.5), 2.0, 24)
    assert low.converged, low.status
    assert high.converged, high.status
    for first, second in zip(low.periods, high.periods, strict=True):
        for field in ("capital", "next_capital", "labor", "consumption", "investment"):
            assert getattr(first, field) == pytest.approx(getattr(second, field), rel=2e-8)
        assert second.next_household_cash > first.next_household_cash
        assert second.next_firm_cash < first.next_firm_cash
        assert second.goods_price < first.goods_price


def test_transition_prices_adjust_while_nominal_consumption_spending_is_constant():
    params = Parameters()
    result = solve_transition(params, 1.0, 40)
    assert result.converged, result.status
    assert result.periods[-1].consumption > result.periods[0].consumption
    assert result.periods[-1].goods_price < result.periods[0].goods_price
    expected_spending = .5 * (1 - params.beta) / (1 - params.beta + params.money_weight)
    for row in result.periods:
        assert row.goods_price * row.consumption == pytest.approx(expected_spending)
    assert result.periods[0].capital_shadow_value != pytest.approx(
        result.periods[0].goods_price, rel=1e-3,
    )


def test_initial_money_distribution_changes_opening_payout_without_creating_resources():
    first = solve_transition(Parameters(), 2.0, 8, initial_firm_cash_share=.5)
    second = solve_transition(Parameters(), 2.0, 8, initial_firm_cash_share=.8)
    assert first.converged, first.status
    assert second.converged, second.status
    assert second.periods[0].distribution - first.periods[0].distribution == pytest.approx(.15)
    assert second.periods[0].household_cash - first.periods[0].household_cash == (
        pytest.approx(-.15)
    )
    for left, right in zip(first.periods, second.periods, strict=True):
        for field in (
            "capital", "next_capital", "consumption", "investment", "labor",
            "goods_price", "money_wage", "next_household_cash", "next_firm_cash",
        ):
            assert getattr(left, field) == pytest.approx(getattr(right, field), rel=2e-8)
    for left, right in zip(first.periods[1:], second.periods[1:], strict=True):
        assert left.distribution == pytest.approx(right.distribution)


def test_explicit_two_household_two_firm_settlement_conserves_money_at_every_phase():
    params = Parameters(money_weight=.2)
    result = solve_transition(params, 2.0, 16, initial_firm_cash_share=.7)
    assert result.converged, result.status
    for row in result.periods:
        states = settle_period(row)
        assert [state.phase for state in states] == [
            "opening", "owner_distributions", "wages", "goods_purchases",
        ]
        payroll = row.money_wage * row.labor
        expected_pairs = (
            (row.household_cash, row.firm_cash),
            (row.household_cash + row.distribution, row.firm_cash - row.distribution),
            (row.household_cash + row.distribution + payroll, 0.0),
            (row.next_household_cash, row.next_firm_cash),
        )
        for state, (household_cash, firm_cash) in zip(states, expected_pairs, strict=True):
            assert len(state.household_cash) == len(state.firm_cash) == 2
            assert state.household_cash == pytest.approx((household_cash, household_cash))
            assert state.firm_cash == pytest.approx((firm_cash, firm_cash), abs=2e-10)
            assert all(value >= -2e-10 for value in (*state.household_cash, *state.firm_cash))
            assert sum(state.household_cash) + sum(state.firm_cash) == pytest.approx(
                1.0, abs=2e-10,
            )


def test_settlement_rejects_unfunded_distribution_and_inconsistent_closing_cash():
    row = steady_state(Parameters())
    with pytest.raises((ArithmeticError, ValueError)):
        settle_period(replace(row, distribution=2 * row.firm_cash))
    with pytest.raises((ArithmeticError, ValueError)):
        settle_period(replace(row, next_household_cash=row.next_household_cash + .01))


@pytest.mark.parametrize("field", ("next_household_cash", "next_firm_cash"))
def test_settlement_rejects_nonfinite_proposed_closing_cash(field):
    row = steady_state(Parameters())
    with pytest.raises((ArithmeticError, ValueError)):
        settle_period(replace(row, **{field: float("nan")}))


def test_global_firm_bound_holds_for_interior_and_corner_deviations():
    params = Parameters()
    result = solve_transition(params, 2.0, 8)
    assert result.converged, result.status
    row = result.periods[0]
    marginal_capital = .5 * row.output / row.capital
    marginal_labor = .5 * row.output / row.labor
    choices = (
        (0.0, 0.0, 0.0, 0.0, 0.0),
        (0.0, .3, .3, 0.0, 0.0),
        (0.0, .3, .1, .1, 0.0),
        (row.capital, 0.0, 0.0, 0.0, 0.0),
        (row.capital, .4, .1, .2, 0.0),
        (row.capital, .4, .1, .2, sqrt(row.capital * .2)),
        (row.capital * 2, 1.0, .2, row.labor * .5, .1),
    )
    for capital, cash, distribution, labor, investment in choices:
        output = sqrt(capital * labor)
        slack = cash - distribution - row.money_wage * labor
        assert slack >= 0
        gap = firm_deviation_gap(
            params, row, capital=capital, firm_cash=cash,
            distribution=distribution, labor=labor, investment=investment,
        )
        next_capital = (1 - params.depreciation) * capital + investment
        next_cash = slack + row.goods_price * (output - investment)
        direct_gap = distribution + params.beta * (
            next_cash + row.goods_price * next_capital
        ) - (cash + row.capital_shadow_value * capital)
        support_gap = -(1 - params.beta) * slack + params.beta * row.goods_price * (
            output - marginal_capital * capital - marginal_labor * labor
        )
        assert gap == pytest.approx(direct_gap, abs=2e-12)
        assert gap == pytest.approx(support_gap, abs=2e-12)
        assert gap <= 2e-12
    assert firm_deviation_gap(
        params, row, capital=row.capital, firm_cash=row.firm_cash,
        distribution=row.distribution, labor=row.labor, investment=row.investment,
    ) == pytest.approx(0.0, abs=2e-12)


@pytest.mark.parametrize("changes", (
    {"capital": -1.0}, {"firm_cash": -1.0}, {"distribution": -1.0},
    {"labor": -1.0}, {"investment": -1.0}, {"investment": 100.0},
    {"distribution": 100.0}, {"labor": 100.0}, {"capital": float("nan")},
))
def test_firm_deviation_checker_rejects_infeasible_choices(changes):
    params = Parameters()
    row = steady_state(params)
    choices = {
        "capital": row.capital, "firm_cash": row.firm_cash,
        "distribution": row.distribution, "labor": row.labor,
        "investment": row.investment,
    }
    choices.update(changes)
    with pytest.raises(ValueError):
        firm_deviation_gap(params, row, **choices)


@pytest.mark.parametrize("initial_capital,initial_share", ((.1, .5), (100.0, .5), (4.4, .05)))
def test_outside_interior_branch_is_reported_without_a_misleading_history(
    initial_capital, initial_share,
):
    result = solve_transition(
        Parameters(), initial_capital, 16, initial_firm_cash_share=initial_share,
    )
    assert not result.converged
    assert result.periods == ()
    assert isinstance(result.status, str) and result.status
    assert result.failure_period == 1


def test_unsupported_computational_tail_is_rejected_even_beyond_the_displayed_run():
    # Extra opening firm cash funds period 1, but cannot keep period 2 interior.
    result = solve_transition(
        Parameters(), .1, 1, initial_firm_cash_share=.99,
    )
    assert not result.converged
    assert result.periods == ()
    assert result.status == "unsupported_nonpositive_distribution"
    assert result.failure_period == 2


def test_numerical_failure_does_not_return_an_uncertified_monetary_path():
    result = solve_transition(Parameters(), 1.0, 8, max_horizon=64)
    assert not result.converged
    assert result.periods == ()
    assert "horizon" in result.status
    assert result.comparison_horizon is None


def test_exhausted_iteration_budget_returns_no_path():
    result = solve_transition(Parameters(), 2.0, 8, max_iterations=1)
    assert not result.converged
    assert result.periods == ()
    assert "iteration" in result.status


@pytest.mark.parametrize("money_weight", (1e-300, 1e308))
def test_unrepresentable_cash_split_is_a_reported_failure(money_weight):
    result = solve_transition(Parameters(money_weight=money_weight), 2.0, 8)
    assert not result.converged
    assert result.periods == ()
    assert result.status == "stationary_allocation_unrepresentable"
    assert result.max_equation_residual is None


def test_accepted_path_reports_certification_and_horizon_invariance():
    params = Parameters()
    short = solve_transition(params, 2.0, 8, horizon=32)
    long = solve_transition(params, 2.0, 32, horizon=128)
    assert short.converged, short.status
    assert long.converged, long.status
    for result in (short, long):
        assert result.horizon > result.comparison_horizon >= len(result.periods)
        assert result.iterations > 0
        assert result.residuals
        assert all(isfinite(value) and 0 <= value < 2e-8 for value in result.residuals.values())
        assert result.max_equation_residual == max(result.residuals.values())
        assert isfinite(result.prefix_difference) and 0 <= result.prefix_difference <= 1e-8
        assert isfinite(result.terminal_gap) and 0 <= result.terminal_gap <= 1e-8
    for first, second in zip(short.periods, long.periods[:8], strict=True):
        for field in (
            "capital", "next_capital", "consumption", "labor", "goods_price",
            "money_wage", "distribution", "capital_shadow_value",
        ):
            assert getattr(first, field) == pytest.approx(getattr(second, field), rel=2e-7)


@pytest.mark.parametrize("field,value", (
    ("beta", 0.0), ("beta", 1.0), ("beta", -1.0), ("beta", float("nan")),
    ("depreciation", 0.0), ("depreciation", -1.0), ("depreciation", 1.1),
    ("depreciation", float("inf")), ("leisure_weight", 0.0),
    ("leisure_weight", -1.0), ("money_weight", 0.0),
    ("money_weight", -1.0), ("money_weight", float("nan")),
))
def test_invalid_economic_parameters_are_rejected(field, value):
    with pytest.raises((TypeError, ValueError)):
        Parameters(**{field: value})


@pytest.mark.parametrize("capital", (0.0, -1.0, float("inf"), float("nan")))
def test_invalid_initial_capital_is_rejected(capital):
    with pytest.raises((TypeError, ValueError)):
        solve_transition(Parameters(), capital, 8)


@pytest.mark.parametrize("share", (0.0, 1.0, -.1, 1.1, float("nan")))
def test_invalid_initial_money_shares_are_rejected(share):
    with pytest.raises((TypeError, ValueError)):
        solve_transition(Parameters(), 1.0, 8, initial_firm_cash_share=share)


@pytest.mark.parametrize("periods", (0, -1, 1.5, True))
def test_invalid_display_lengths_are_rejected(periods):
    with pytest.raises((TypeError, ValueError)):
        solve_transition(Parameters(), 1.0, periods)


@pytest.mark.parametrize("kwargs", (
    {"horizon": 0}, {"max_horizon": 0}, {"max_iterations": 0},
    {"tolerance": 0.0}, {"continuation_tolerance": 0.0},
    {"tolerance": float("nan")},
))
def test_invalid_numerical_controls_are_rejected(kwargs):
    with pytest.raises((TypeError, ValueError)):
        solve_transition(Parameters(), 1.0, 8, **kwargs)
