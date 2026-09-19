"""Economic checks for the isolated endogenous-labor growth reference.

The oracles below come from household optimality and resource accounting, not
the transition solver's finite-horizon equations or internal numerical helpers.
"""

from itertools import pairwise
from math import isfinite

import pytest

from econ_agent_sim.textbook_growth import (
    TransitionParameters,
    exact_solution,
    rollout,
    solve_growth,
    solve_transition,
    steady_state,
)


def _stationary_allocation(params):
    capital_per_worker = (
        params.alpha * params.productivity
        / (1 / params.beta - 1 + params.depreciation)
    ) ** (1 / (1 - params.alpha))
    wage = (1 - params.alpha) * params.productivity * capital_per_worker**params.alpha
    consumption_per_worker = (
        params.productivity * capital_per_worker**params.alpha
        - params.depreciation * capital_per_worker
    )
    labor = wage / (wage + params.leisure_weight * consumption_per_worker)
    capital = capital_per_worker * labor
    output = params.productivity * capital**params.alpha * labor**(1 - params.alpha)
    return {
        "capital": capital,
        "labor": labor,
        "output": output,
        "consumption": output - params.depreciation * capital,
        "investment": params.depreciation * capital,
        "real_wage": wage,
    }


def _assert_household_conditions(params, periods):
    for period in periods:
        assert params.leisure_weight / (1 - period.labor) == pytest.approx(
            (1 - params.alpha) * period.output
            / (period.labor * period.consumption),
            rel=2e-8,
        )
    for current, following in pairwise(periods):
        gross_return = (
            1 - params.depreciation
            + params.alpha * following.output / following.capital
        )
        assert following.consumption / current.consumption == pytest.approx(
            params.beta * gross_return, rel=2e-8,
        )


@pytest.mark.parametrize("alpha,beta,productivity,leisure_weight,initial_capital", (
    (.5, .95, 1.0, 1.0, 1.0),
    (.3, .9, 1.4, 2.2, .04),
    (.7, .85, .8, .4, 3.0),
))
def test_full_depreciation_matches_independent_infinite_horizon_policy(
    alpha, beta, productivity, leisure_weight, initial_capital,
):
    params = TransitionParameters(
        alpha=alpha, beta=beta, productivity=productivity,
        depreciation=1.0, leisure_weight=leisure_weight,
    )
    result = solve_transition(params, initial_capital, 24)
    assert result.converged, result.status
    assert len(result.periods) == 24
    labor = (1 - alpha) / ((1 - alpha) + leisure_weight * (1 - alpha * beta))
    capital = initial_capital
    for period in result.periods:
        output = productivity * capital**alpha * labor**(1 - alpha)
        assert period.capital == pytest.approx(capital, rel=2e-7)
        assert period.labor == pytest.approx(labor, rel=2e-7)
        assert period.consumption == pytest.approx((1 - alpha * beta) * output, rel=2e-7)
        assert period.next_capital == pytest.approx(alpha * beta * output, rel=2e-7)
        assert period.investment == pytest.approx(period.next_capital, rel=2e-10)
        capital = alpha * beta * output
    _assert_household_conditions(params, result.periods)


@pytest.mark.parametrize("alpha,beta,productivity,depreciation,leisure_weight", (
    (.5, .95, 1.0, .1, 1.0),
    (.35, .92, 1.6, .4, 2.0),
    (.4, .94, 1.2, 0.0, .8),
))
def test_steady_state_matches_independent_partial_depreciation_formulas(
    alpha, beta, productivity, depreciation, leisure_weight,
):
    params = TransitionParameters(
        alpha=alpha, beta=beta, productivity=productivity,
        depreciation=depreciation, leisure_weight=leisure_weight,
    )
    stationary = steady_state(params)
    for field, expected in _stationary_allocation(params).items():
        assert getattr(stationary, field) == pytest.approx(expected, rel=2e-12)
    assert params.beta * (
        1 - depreciation + alpha * stationary.output / stationary.capital
    ) == pytest.approx(1.0, abs=2e-12)
    _assert_household_conditions(params, (stationary,))


def test_default_steady_state_reproduces_published_reference_values():
    stationary = steady_state(TransitionParameters())
    for field, expected in {
        "capital": 4.5765720081,
        "labor": .4264705882,
        "output": 1.3970588235,
        "consumption": .9394016227,
        "investment": .4576572008,
        "real_wage": 1.6379310345,
    }.items():
        assert getattr(stationary, field) == pytest.approx(expected, abs=6e-11)


@pytest.mark.parametrize("depreciation", (0.0, .1, 1.0))
def test_stationary_initial_capital_keeps_the_entire_allocation_stationary(depreciation):
    params = TransitionParameters(depreciation=depreciation)
    expected = _stationary_allocation(params)
    result = solve_transition(params, expected["capital"], 16)
    assert result.converged, result.status
    assert len(result.periods) == 16
    for period in result.periods:
        for field, value in expected.items():
            assert getattr(period, field) == pytest.approx(value, rel=2e-8, abs=2e-10)
        assert period.next_capital == pytest.approx(expected["capital"], rel=2e-8)


@pytest.mark.parametrize("initial_capital", (.2, 15.0))
def test_partial_depreciation_path_satisfies_resources_timing_and_household_optimality(
    initial_capital,
):
    params = TransitionParameters(alpha=.4, beta=.94, productivity=1.3, leisure_weight=1.2)
    result = solve_transition(params, initial_capital, 48)
    assert result.converged, result.status
    assert result.parameters == params
    assert result.initial_capital == initial_capital
    assert len(result.periods) == 48
    capital = initial_capital
    for period in result.periods:
        assert period.capital == pytest.approx(capital, rel=2e-12)
        assert period.capital > 0 and period.next_capital > 0
        assert period.consumption > 0 and 0 < period.labor < 1
        output = params.productivity * capital**params.alpha * period.labor**(1 - params.alpha)
        assert period.output == pytest.approx(output, rel=2e-10)
        assert period.consumption + period.next_capital == pytest.approx(
            output + (1 - params.depreciation) * capital, rel=2e-10,
        )
        assert period.investment == pytest.approx(output - period.consumption, abs=2e-9)
        assert period.investment == pytest.approx(
            period.next_capital - (1 - params.depreciation) * capital, abs=2e-9,
        )
        assert period.real_wage == pytest.approx(
            (1 - params.alpha) * output / period.labor, rel=2e-10,
        )
        # Competitive factor payments exhaust output and fund the same allocation.
        labor_income = period.real_wage * period.labor
        capital_income = params.alpha * output
        assert labor_income + capital_income == pytest.approx(output, rel=2e-10)
        capital = period.next_capital
    assert [period.number for period in result.periods] == list(range(1, 49))
    _assert_household_conditions(params, result.periods)


@pytest.mark.parametrize("initial_multiple", (.2, 3.0))
def test_partial_depreciation_converges_to_steady_state_from_below_and_above(initial_multiple):
    params = TransitionParameters()
    expected = _stationary_allocation(params)
    result = solve_transition(params, initial_multiple * expected["capital"], 160, horizon=256)
    assert result.converged, result.status
    final = result.periods[-1]
    for field in ("capital", "consumption", "labor"):
        assert getattr(final, field) == pytest.approx(expected[field], rel=2e-5)
    distances = [abs(period.capital - expected["capital"]) for period in result.periods]
    assert all(later <= earlier + 1e-8 for earlier, later in pairwise(distances))
    _assert_household_conditions(params, result.periods)


def test_surviving_capital_can_be_consumed_through_negative_gross_investment():
    params = TransitionParameters()
    initial_capital = 100 * _stationary_allocation(params)["capital"]
    result = solve_transition(params, initial_capital, 12)
    assert result.converged, result.status
    first = result.periods[0]
    assert first.investment < 0
    assert first.consumption > first.output
    assert 0 < first.next_capital < (1 - params.depreciation) * initial_capital
    assert first.consumption + first.next_capital == pytest.approx(
        first.output + (1 - params.depreciation) * initial_capital, rel=2e-10,
    )
    _assert_household_conditions(params, result.periods)


def test_transition_prefix_is_independent_of_starting_continuation_horizon():
    params = TransitionParameters()
    short = solve_transition(params, .15, 12, horizon=32)
    long = solve_transition(params, .15, 12, horizon=128)
    assert short.converged, short.status
    assert long.converged, long.status
    for first, second in zip(short.periods, long.periods, strict=True):
        for field in ("capital", "consumption", "labor", "next_capital"):
            assert getattr(first, field) == pytest.approx(getattr(second, field), rel=2e-7)


def test_extending_displayed_run_does_not_change_earlier_household_decisions():
    params = TransitionParameters()
    short = solve_transition(params, 1.0, 5)
    long = solve_transition(params, 1.0, 32)
    assert short.converged, short.status
    assert long.converged, long.status
    for first, second in zip(short.periods, long.periods[:5], strict=True):
        for field in ("consumption", "labor", "next_capital"):
            assert getattr(first, field) == pytest.approx(getattr(second, field), rel=2e-7)
    assert short.periods[-1].next_capital > 0


def test_success_reports_finite_numerical_and_continuation_diagnostics():
    params = TransitionParameters()
    result = solve_transition(params, 1.0, 8, continuation_tolerance=1e-9)
    assert result.converged, result.status
    assert isinstance(result.status, str) and result.status
    assert result.horizon > result.comparison_horizon >= len(result.periods)
    assert result.iterations > 0
    for field in (
        "max_euler_residual", "max_labor_residual", "max_resource_residual",
        "prefix_difference", "terminal_gap",
    ):
        value = getattr(result, field)
        assert isfinite(value) and value >= 0
    assert result.prefix_difference <= 1e-9
    assert result.max_euler_residual < 1e-8
    assert result.max_labor_residual < 1e-8
    assert result.max_resource_residual < 1e-8


def test_iteration_budget_exhaustion_returns_no_apparently_usable_path():
    result = solve_transition(
        TransitionParameters(), .05, 4, max_iterations=1, tolerance=1e-12,
    )
    assert not result.converged
    assert result.periods == ()
    assert result.iterations >= 1
    assert isinstance(result.status, str) and result.status


def test_horizon_budget_exhaustion_returns_no_apparently_usable_path():
    result = solve_transition(
        TransitionParameters(), .05, 4,
        horizon=24, max_horizon=48, continuation_tolerance=1e-12,
    )
    assert not result.converged
    assert result.periods == ()
    assert result.horizon == 48
    assert result.comparison_horizon == 24
    assert isinstance(result.status, str) and result.status


def test_unrepresentable_stationary_allocation_returns_explicit_transition_failure():
    # Admissible preferences and technology can imply capital beyond float range.
    params = TransitionParameters(alpha=.999, beta=.9999999999999999)
    with pytest.raises(ArithmeticError):
        steady_state(params)
    result = solve_transition(params, 1.0, 4)
    assert not result.converged
    assert result.periods == ()
    assert result.status == "stationary_allocation_unrepresentable"
    assert result.iterations == 0


def test_fixed_labor_apis_reject_parameters_that_include_leisure_and_depreciation():
    params = TransitionParameters(depreciation=.1, leisure_weight=2.0)
    for solver in (solve_growth, exact_solution):
        with pytest.raises(ValueError):
            solver(params)
    with pytest.raises(ValueError):
        rollout(params, 1.0, 4)


@pytest.mark.parametrize("field,value", (
    ("depreciation", -.01), ("depreciation", 1.01),
    ("depreciation", float("nan")), ("depreciation", float("inf")),
    ("depreciation", True),
    ("leisure_weight", 0), ("leisure_weight", -1),
    ("leisure_weight", float("nan")), ("leisure_weight", float("inf")),
    ("leisure_weight", True),
))
def test_invalid_transition_preferences_and_technology_are_rejected(field, value):
    with pytest.raises(ValueError):
        TransitionParameters(**{field: value})


@pytest.mark.parametrize("capital", (0.0, -1.0, float("nan"), float("inf"), True))
def test_transition_rejects_nonpositive_or_nonfinite_initial_capital(capital):
    with pytest.raises(ValueError):
        solve_transition(TransitionParameters(), capital, 2)


@pytest.mark.parametrize("periods,controls", (
    (0, {}), (-1, {}), (1.5, {}), (True, {}),
    (2, {"horizon": 0}), (2, {"horizon": 2.5}),
    (2, {"max_horizon": 0}), (2, {"max_horizon": True}),
    (2, {"max_iterations": 0}), (2, {"max_iterations": 1.5}),
    (2, {"tolerance": 0.0}), (2, {"tolerance": float("nan")}),
    (2, {"continuation_tolerance": -1.0}),
    (2, {"continuation_tolerance": float("inf")}),
))
def test_transition_rejects_invalid_numerical_controls(periods, controls):
    with pytest.raises(ValueError):
        solve_transition(TransitionParameters(), 1.0, periods, **controls)
