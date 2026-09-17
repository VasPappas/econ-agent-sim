"""Independent checks for the isolated log/Cobb--Douglas growth benchmark.

This textbook planning problem is NOT the cash-settling, two-firm app. Reference
values and first-order conditions are derived here rather than calling the
implementation's analytical solver as the only oracle.
"""

from itertools import pairwise
from math import fsum, isfinite, log

import pytest

from econ_agent_sim.textbook_growth import (
    Parameters,
    evaluate_value,
    exact_solution,
    rollout,
    solve_growth,
)


def _reference_coefficients(alpha, beta, productivity):
    """Sum log consumption along the analytically optimal capital recurrence."""
    saving = alpha * beta
    slope = alpha / (1 - saving)
    intercept = (
        log((1 - saving) * productivity)
        + saving * log(saving * productivity) / (1 - saving)
    ) / (1 - beta)
    return intercept, slope, saving


def _direct_discounted_consumption(params, capital, periods=5000):
    # Work in logs so an extreme but positive capital stock need not underflow.
    log_capital = log(capital)
    saving = params.alpha * params.beta
    terms = []
    discount = 1.0
    for _ in range(periods):
        log_output = log(params.productivity) + params.alpha * log_capital
        terms.append(discount * (log(1 - saving) + log_output))
        log_capital = log(saving) + log_output
        discount *= params.beta
    return fsum(terms)


@pytest.mark.parametrize("alpha,beta,productivity", (
    (.5, .95, 1.0),
    (.3, .9, 2.0),
    (.8, .5, .2),
    (.1, .99, 10.0),
    (.95, .95, .5),
))
def test_iteration_and_exact_solver_match_independently_derived_coefficients(
    alpha, beta, productivity,
):
    params = Parameters(alpha=alpha, beta=beta, productivity=productivity)
    intercept, slope, saving = _reference_coefficients(alpha, beta, productivity)
    for solution in (exact_solution(params), solve_growth(params)):
        assert solution.converged
        assert solution.value_intercept == pytest.approx(intercept, abs=2e-8)
        assert solution.value_slope == pytest.approx(slope, abs=2e-9)
        assert solution.saving_share == pytest.approx(saving, abs=2e-10)
        assert isfinite(solution.coefficient_residual)
        assert solution.coefficient_residual >= 0


@pytest.mark.parametrize("capital", (.01, 1.0, 100.0))
def test_value_matches_a_long_independent_discounted_consumption_sum(capital):
    params = Parameters(alpha=.4, beta=.95, productivity=1.7)
    reference = _direct_discounted_consumption(params, capital)
    for solution in (exact_solution(params), solve_growth(params)):
        assert evaluate_value(solution, capital) == pytest.approx(reference, abs=2e-8)


def test_affine_bellman_policy_beats_independent_feasible_action_grid():
    params = Parameters(alpha=.4, beta=.93, productivity=1.7)
    solution = solve_growth(params, tolerance=1e-12)
    a, b = solution.value_intercept, solution.value_slope
    for capital in (.02, .5, 2.0, 40.0):
        output = params.productivity * capital**params.alpha
        investment = solution.saving_share * output
        consumption = output - investment
        # These independently derived conditions concern the interior optimum.
        assert 1 / consumption == pytest.approx(params.beta * b / investment)
        achieved = log(consumption) + params.beta * (a + b * log(investment))
        assert achieved == pytest.approx(a + b * log(capital), abs=2e-10)
        for fraction in (i / 1000 for i in range(1, 1000)):
            other_investment = fraction * output
            alternative = log(output - other_investment) + params.beta * (
                a + b * log(other_investment)
            )
            assert alternative <= achieved + 2e-12


@pytest.mark.parametrize("initial_capital", (.001, .1, 1.0, 100.0))
def test_rollout_independently_satisfies_resources_capital_timing_and_euler_equation(
    initial_capital,
):
    params = Parameters(alpha=.35, beta=.96, productivity=1.2)
    periods = rollout(params, initial_capital, 40)
    assert len(periods) == 40
    opening = initial_capital
    for period in periods:
        assert period.capital == pytest.approx(opening)
        assert period.output == pytest.approx(
            params.productivity * period.capital**params.alpha,
        )
        assert period.consumption > 0 and period.investment > 0
        assert period.output == pytest.approx(period.consumption + period.investment)
        assert period.next_capital == period.investment  # Full depreciation.
        assert period.investment / period.output == pytest.approx(params.alpha * params.beta)
        opening = period.next_capital
    for current, following in pairwise(periods):
        marginal_product = params.alpha * params.productivity * (
            following.capital ** (params.alpha - 1)
        )
        assert 1 / current.consumption == pytest.approx(
            params.beta * marginal_product / following.consumption, rel=2e-9,
        )
    numbers = [period.number for period in periods]
    assert numbers == list(range(numbers[0], numbers[0] + len(periods)))


def test_analytical_steady_state_remains_stationary():
    params = Parameters(alpha=.4, beta=.95, productivity=1.2)
    stationary_capital = (
        params.alpha * params.beta * params.productivity
    ) ** (1 / (1 - params.alpha))
    periods = rollout(params, stationary_capital, 25)
    output = params.productivity * stationary_capital**params.alpha
    for period in periods:
        assert period.capital == pytest.approx(stationary_capital, rel=2e-9)
        assert period.next_capital == pytest.approx(stationary_capital, rel=2e-9)
        assert period.consumption == pytest.approx(output - stationary_capital, rel=2e-9)


@pytest.mark.parametrize("initial_capital", (.001, 100.0))
def test_capital_path_converges_to_independently_derived_steady_state(initial_capital):
    params = Parameters(alpha=.5, beta=.95, productivity=1.0)
    stationary_capital = (.5 * .95) ** 2
    periods = rollout(params, initial_capital, 50)
    assert periods[-1].next_capital == pytest.approx(stationary_capital, rel=2e-9)
    distances = [abs(log(period.capital / stationary_capital)) for period in periods[:20]]
    assert all(later <= earlier + 1e-12 for earlier, later in pairwise(distances))


def test_iteration_budget_exhaustion_is_explicit_and_cannot_drive_a_rollout():
    params = Parameters()
    result = solve_growth(params, tolerance=1e-12, max_iterations=1)
    assert not result.converged
    assert result.iterations == 1
    assert result.coefficient_residual > 1e-12
    with pytest.raises(ValueError):
        rollout(params, 1.0, 2, solution=result)


def test_declared_convergence_tolerance_is_not_a_hidden_fixed_iteration_count():
    params = Parameters(alpha=.45, beta=.9, productivity=1.5)
    coarse = solve_growth(params, tolerance=1e-5)
    fine = solve_growth(params, tolerance=1e-11)
    assert coarse.converged and fine.converged
    assert coarse.coefficient_residual <= 1e-5
    assert fine.coefficient_residual <= 1e-11
    assert fine.iterations >= coarse.iterations
    intercept, slope, _ = _reference_coefficients(.45, .9, 1.5)
    coarse_error = max(abs(coarse.value_intercept - intercept), abs(coarse.value_slope - slope))
    fine_error = max(abs(fine.value_intercept - intercept), abs(fine.value_slope - slope))
    assert fine_error <= coarse_error


def test_reported_residual_is_the_final_coefficients_bellman_residual():
    params = Parameters(alpha=.45, beta=.9, productivity=1.5)
    result = solve_growth(params, tolerance=1e-12, max_iterations=7)
    a, b = result.value_intercept, result.value_slope
    continuation_weight = params.beta * b
    saving = continuation_weight / (1 + continuation_weight)
    next_intercept = (
        log((1 - saving) * params.productivity)
        + continuation_weight * log(saving * params.productivity)
        + params.beta * a
    )
    next_slope = params.alpha * (1 + continuation_weight)
    independent_residual = max(abs(next_intercept - a), abs(next_slope - b))
    assert result.coefficient_residual == pytest.approx(independent_residual, abs=1e-13)
    assert result.saving_share == pytest.approx(saving)


def test_bellman_iteration_does_not_call_the_analytical_oracle(monkeypatch):
    def unavailable_oracle(*args, **kwargs):
        raise AssertionError("An independent iterative solver cannot call its oracle.")

    monkeypatch.setattr(
        "econ_agent_sim.textbook_growth.exact_solution", unavailable_oracle,
    )
    params = Parameters()
    result = solve_growth(params)
    assert result.converged
    assert result.iterations > 1
    assert result.saving_share == pytest.approx(.5 * .95)


def test_rollout_rejects_a_policy_for_different_model_parameters():
    with pytest.raises(ValueError, match="different"):
        rollout(
            Parameters(alpha=.4), 1.0, 3,
            solution=exact_solution(Parameters(alpha=.5)),
        )


@pytest.mark.parametrize("field,value", (
    ("alpha", 0.0), ("alpha", 1.0), ("alpha", -1.0),
    ("alpha", float("nan")), ("alpha", float("inf")),
    ("beta", 0.0), ("beta", 1.0), ("beta", -1.0),
    ("beta", float("nan")), ("beta", float("inf")),
    ("productivity", 0.0), ("productivity", -1.0),
    ("productivity", float("nan")), ("productivity", float("inf")),
))
def test_invalid_model_parameters_are_rejected(field, value):
    with pytest.raises(ValueError):
        Parameters(**{field: value})


@pytest.mark.parametrize("capital", (0.0, -1.0, float("nan"), float("inf")))
def test_nonpositive_or_nonfinite_capital_is_rejected(capital):
    params = Parameters()
    solution = exact_solution(params)
    with pytest.raises(ValueError):
        evaluate_value(solution, capital)
    with pytest.raises(ValueError):
        rollout(params, capital, 2)


@pytest.mark.parametrize("tolerance", (0.0, -1.0, float("nan"), float("inf")))
def test_invalid_convergence_tolerance_is_rejected(tolerance):
    with pytest.raises(ValueError):
        solve_growth(Parameters(), tolerance=tolerance)


@pytest.mark.parametrize("budget", (0, -1, 1.5, True))
def test_invalid_iteration_budgets_are_rejected(budget):
    with pytest.raises(ValueError):
        solve_growth(Parameters(), max_iterations=budget)


@pytest.mark.parametrize("periods", (0, -1, 1.5, True))
def test_invalid_rollout_lengths_are_rejected(periods):
    with pytest.raises(ValueError):
        rollout(Parameters(), 1.0, periods)
