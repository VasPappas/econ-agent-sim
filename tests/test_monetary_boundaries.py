"""Independent budget, Kuhn–Tucker and global deviation oracles at corners."""

from dataclasses import replace
from itertools import pairwise
from math import sqrt

import pytest

from econ_agent_sim import _monetary_boundaries
from econ_agent_sim.monetary_growth import (
    Parameters,
    firm_deviation_gap,
    settle_period,
    solve_constrained_transition,
    solve_transition,
    steady_state,
)


def _check_path(params, rows):
    for row in rows:
        p, w, b = row.goods_price, row.money_wage, row.cash_shadow_value
        bn, an = row.next_cash_shadow_value, row.next_capital_shadow_value
        q = params.beta
        assert row.capital > 0 and row.next_capital > 0
        assert 0 < row.labor < 1 and row.consumption > 0
        assert 0 <= row.investment < row.output
        assert row.distribution >= 0
        assert min(p, w, row.household_cash, row.firm_cash,
                   row.next_household_cash, row.next_firm_cash) > 0
        assert row.output == pytest.approx(sqrt(row.capital * row.labor), rel=2e-9)
        assert row.output == pytest.approx(row.consumption + row.investment, rel=2e-9)
        assert row.next_capital == pytest.approx(
            (1 - params.depreciation) * row.capital + row.investment, rel=2e-9,
        )
        payroll, spending = w * row.labor, p * row.consumption
        assert row.distribution + payroll == pytest.approx(row.firm_cash, abs=2e-10)
        assert row.next_household_cash == pytest.approx(
            row.household_cash + payroll + row.distribution - spending, abs=2e-10,
        )
        assert row.next_firm_cash == pytest.approx(
            row.firm_cash - row.distribution - payroll + p * (row.output - row.investment),
            abs=2e-10,
        )
        assert params.leisure_weight / (1 - row.labor) == pytest.approx(
            w / spending, rel=2e-8,
        )
        mpk, mpl = .5 * row.output / row.capital, .5 * row.output / row.labor
        assert row.capital_shadow_value == pytest.approx(
            q * ((1 - params.depreciation) * an + p * bn * mpk), rel=2e-8,
        )
        assert b * w == pytest.approx(q * bn * p * mpl, rel=2e-8)
        assert row.discount_factor == pytest.approx(q)
        assert row.funding_multiplier == pytest.approx(b - q * bn, abs=2e-10)
        assert b >= 1 - 2e-9
        assert row.funding_multiplier >= -2e-9 * b
        investment_gap = p * bn - an
        assert investment_gap >= -2e-9 * p * bn
        assert row.distribution * (b - 1) == pytest.approx(0, abs=2e-9)
        assert row.investment * investment_gap == pytest.approx(0, abs=2e-9)
        states = settle_period(row)
        assert [s.phase for s in states] == [
            "opening", "owner_distributions", "wages", "goods_purchases",
        ]
        for state in states:
            balances = state.household_cash + state.firm_cash
            assert min(balances) >= -2e-10
            assert sum(balances) == pytest.approx(1, abs=2e-10)
        assert states[-1].household_cash == pytest.approx((row.next_household_cash,) * 2)
        assert states[-1].firm_cash == pytest.approx((row.next_firm_cash,) * 2)
    for row, following in pairwise(rows):
        assert row.next_capital == pytest.approx(following.capital, rel=2e-9)
        assert row.next_firm_cash == pytest.approx(following.firm_cash)
        assert row.next_household_cash == pytest.approx(following.household_cash)
        assert row.next_cash_shadow_value == pytest.approx(following.cash_shadow_value)
        assert row.next_capital_shadow_value == pytest.approx(following.capital_shadow_value)
        marginal_current = 1 / (row.goods_price * row.consumption)
        marginal_next = 1 / (following.goods_price * following.consumption)
        assert marginal_current == pytest.approx(
            params.money_weight / row.next_household_cash + params.beta * marginal_next,
            rel=2e-8,
        )
        assert row.discount_factor == pytest.approx(params.beta * marginal_next / marginal_current)


@pytest.fixture(scope="module")
def corner_paths():
    results = {}
    for capital, share in ((.1, .5), (100., .5), (4.44, .05), (.5, .95)):
        result = solve_constrained_transition(
            Parameters(), capital, 40, initial_firm_cash_share=share,
        )
        assert result.converged, result.status
        results[capital, share] = result
    return results


@pytest.mark.parametrize("capital,share", ((.1, .5), (100., .5), (4.44, .05), (.5, .95)))
def test_corner_paths_satisfy_independent_optimality_and_settlement(corner_paths, capital, share):
    result = corner_paths[capital, share]
    assert result.initial_capital == capital
    assert result.initial_firm_cash_share == share
    assert result.failure_period is None
    assert len(result.periods) == 40
    assert result.periods[0].firm_cash == share / 2
    assert [r.number for r in result.periods] == list(range(1, 41))
    _check_path(result.parameters, result.periods)


def test_low_capital_suspends_distributions_then_resumes_them(corner_paths):
    rows = corner_paths[.1, .5].periods
    assert all(r.distribution == 0 and r.cash_shadow_value > 1 for r in rows[:4])
    assert all(r.distribution > 0 for r in rows[4:])
    assert all(r.investment > 0 for r in rows)
    assert all(r.labor == pytest.approx(.5) for r in rows[:4])


def test_high_capital_does_not_scrap_capital_to_finance_consumption(corner_paths):
    rows = corner_paths[100., .5].periods
    assert all(r.investment == 0 for r in rows[:18])
    assert rows[18].investment > 0
    for row in rows[:18]:
        assert row.next_capital == pytest.approx(.9 * row.capital)
        assert row.consumption == pytest.approx(row.output)
        assert row.next_capital_shadow_value < row.goods_price * row.next_cash_shadow_value


def test_opening_cash_shortage_can_bind_both_boundaries(corner_paths):
    row = corner_paths[4.44, .05].periods[0]
    assert row.investment == row.distribution == 0
    assert row.cash_shadow_value > 1
    assert row.funding_multiplier > 0
    assert row.next_capital_shadow_value < row.goods_price * row.next_cash_shadow_value


def test_forward_looking_cash_values_can_rise_after_positive_distribution(corner_paths):
    first, second = corner_paths[.5, .95].periods[:2]
    assert first.distribution > 0 and first.cash_shadow_value == pytest.approx(1)
    assert second.distribution == 0 and second.cash_shadow_value > 1
    assert 0 < first.funding_multiplier < 1 - .95


@pytest.mark.parametrize("capital", (1., 2., 6., 10.))
def test_constrained_reference_recovers_independent_interior_solver(capital):
    params = Parameters()
    interior = solve_transition(params, capital, 24)
    constrained = solve_constrained_transition(params, capital, 24)
    assert interior.converged and constrained.converged
    for expected, actual in zip(interior.periods, constrained.periods, strict=True):
        for field in ("capital", "next_capital", "labor", "consumption", "investment",
                      "distribution", "goods_price", "money_wage", "capital_shadow_value"):
            assert getattr(actual, field) == pytest.approx(getattr(expected, field), rel=2e-7)
        assert actual.cash_shadow_value == pytest.approx(1, abs=2e-9)


@pytest.mark.parametrize("params", (Parameters(), Parameters(.8, 1., .5, .1),
                                     Parameters(.97, .25, 1.4, .2)))
def test_stationary_path_matches_independently_calculated_levels(params):
    mpk = 1 / params.beta - 1 + params.depreciation
    ratio = (.5 / mpk) ** 2
    wage = params.beta * .5 * sqrt(ratio)
    labor = wage / (wage + params.leisure_weight * (sqrt(ratio) - params.depreciation * ratio))
    capital = ratio * labor
    spending = .5 * (1 - params.beta) / (1 - params.beta + params.money_weight)
    result = solve_constrained_transition(
        params, capital, 24, initial_firm_cash_share=2 * spending,
    )
    assert result.converged, result.status
    for row in result.periods:
        assert row.capital == pytest.approx(capital, rel=2e-8)
        assert row.labor == pytest.approx(labor, rel=2e-8)
        assert row.investment == pytest.approx(params.depreciation * capital, rel=2e-8)
        assert row.firm_cash == pytest.approx(spending)
    _check_path(params, result.periods)


@pytest.mark.parametrize("beta,chi", ((.95, 1.), (.8, 2.2)))
def test_full_depreciation_exact_policy(beta, chi):
    params = Parameters(beta=beta, depreciation=1., leisure_weight=chi)
    cash = .5 * (1 - beta) / (1 - beta + params.money_weight)
    result = solve_constrained_transition(params, 1., 24, initial_firm_cash_share=2 * cash)
    assert result.converged, result.status
    labor = .5 / (.5 + chi / beta * (1 - .5 * beta))
    capital = 1.
    for row in result.periods:
        output = sqrt(capital * labor)
        assert row.labor == pytest.approx(labor, rel=2e-7)
        assert row.consumption == pytest.approx((1 - .5 * beta) * output, rel=2e-7)
        assert row.next_capital == pytest.approx(.5 * beta * output, rel=2e-7)
        capital = .5 * beta * output


def test_global_firm_deviations_include_inactivity_and_off_path_capital_and_cash(corner_paths):
    params = Parameters()
    for result in corner_paths.values():
        for row in result.periods[:5]:
            p, w = row.goods_price, row.money_wage
            b, bn = row.cash_shadow_value, row.next_cash_shadow_value
            a, an, q = row.capital_shadow_value, row.next_capital_shadow_value, params.beta
            mpk, mpl = .5 * row.output / row.capital, .5 * row.output / row.labor
            candidate = firm_deviation_gap(
                params, row, capital=row.capital, firm_cash=row.firm_cash,
                distribution=row.distribution, labor=row.labor, investment=row.investment,
            )
            assert candidate == pytest.approx(0, abs=2e-9)
            for capital in (0., row.capital * .3, row.capital * 2):
                for cash in (0., row.firm_cash * .3, row.firm_cash * 2):
                    for hours in (0., .4 * cash / w, cash / w):
                        # The exact all-output boundary must use the public
                        # production evaluation's rounding convention.
                        output = sqrt(capital) * sqrt(hours)
                        for payout_share in (0., .5, 1.):
                            distribution = max(0., cash - w * hours) * payout_share
                            slack = cash - distribution - w * hours
                            for investment in (0., .4 * output, output):
                                next_cash = slack + p * (output - investment)
                                next_capital = (1 - params.depreciation) * capital + investment
                                direct = distribution + q * (bn * next_cash + an * next_capital)
                                direct -= b * cash + a * capital
                                support = -(b - 1) * distribution - (b - q * bn) * slack
                                support -= q * (p * bn - an) * investment
                                support += q * bn * p * (output - mpk * capital - mpl * hours)
                                actual = firm_deviation_gap(
                                    params, row, capital=capital, firm_cash=cash,
                                    distribution=distribution, labor=hours, investment=investment,
                                )
                                assert actual == pytest.approx(direct, abs=2e-10)
                                assert actual == pytest.approx(support, abs=2e-9)
                                assert actual <= 2e-9


def test_display_and_starting_horizon_do_not_materially_change_corner_prefix():
    first = solve_constrained_transition(Parameters(), .1, 12)
    second = solve_constrained_transition(Parameters(), .1, 45, horizon=80)
    assert first.converged and second.converged
    assert first.comparison_horizon < first.horizon
    assert first.prefix_difference <= 1e-8 and first.terminal_gap <= 1e-8
    for a, b in zip(first.periods, second.periods):
        for field in ("capital", "consumption", "labor", "investment", "distribution",
                      "cash_shadow_value", "capital_shadow_value"):
            assert getattr(a, field) == pytest.approx(getattr(b, field), rel=2e-7, abs=2e-10)


@pytest.mark.parametrize("controls", ({"max_horizon": 32}, {"max_horizon": 64},
                                      {"max_iterations": 1}))
def test_exhausted_numerical_budgets_never_return_usable_history(controls):
    result = solve_constrained_transition(Parameters(), .1, 12, **controls)
    assert not result.converged
    assert result.periods == ()
    assert "budget" in result.status


def test_cash_retention_candidate_is_rejected_not_repaired():
    result = solve_constrained_transition(
        Parameters(), .1, 24, initial_firm_cash_share=.99,
    )
    assert not result.converged and result.periods == ()
    assert result.status == "unsupported_cash_retention"
    assert result.failure_period == 1


def test_audit_checks_undisplayed_tail_shadow_signs(monkeypatch):
    original = _monetary_boundaries._records

    def corrupt(*args, **kwargs):
        rows = list(original(*args, **kwargs))
        rows[-2] = replace(rows[-2], cash_shadow_value=.8)
        return tuple(rows)

    monkeypatch.setattr(_monetary_boundaries, "_records", corrupt)
    result = solve_constrained_transition(Parameters(), 2., 1)
    assert not result.converged and result.periods == ()
    assert result.status == "choice_conditions_not_met"


def test_unrepresentable_stationary_allocation_returns_no_history():
    result = solve_constrained_transition(Parameters(money_weight=1e-320), 1., 12)
    assert not result.converged and result.periods == ()
    assert result.status == "stationary_allocation_unrepresentable"


@pytest.mark.parametrize("kwargs", (
    {"initial_capital": 0}, {"initial_capital": float("inf")},
    {"initial_capital": True}, {"periods": 0}, {"periods": 2.5},
    {"initial_firm_cash_share": 0}, {"initial_firm_cash_share": 1},
    {"initial_firm_cash_share": float("nan")}, {"horizon": 1},
    {"max_horizon": False}, {"max_iterations": 0}, {"tolerance": 0},
    {"continuation_tolerance": -1}, {"parameters": object()},
))
def test_invalid_inputs_are_rejected(kwargs):
    arguments = {"parameters": Parameters(), "initial_capital": 1., "periods": 12}
    arguments.update(kwargs)
    with pytest.raises(ValueError):
        solve_constrained_transition(**arguments)


def test_original_interior_solver_retains_its_explicit_regime_boundary():
    result = solve_transition(Parameters(), 100., 12)
    assert not result.converged and result.periods == ()
    assert result.status == "unsupported_investment_boundary"
    assert steady_state(Parameters()).cash_shadow_value == 1
