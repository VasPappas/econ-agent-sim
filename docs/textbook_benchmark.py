"""Reproduce the isolated textbook reference; this does not run the app."""

import json
from dataclasses import asdict
from itertools import pairwise
from math import nextafter
from time import perf_counter

from econ_agent_sim.textbook_growth import (
    Parameters,
    TransitionParameters,
    exact_solution,
    rollout,
    solve_growth,
    solve_transition,
    steady_state,
)


def compare(parameters):
    started = perf_counter()
    numerical = solve_growth(parameters)
    elapsed = perf_counter() - started
    analytical = exact_solution(parameters)
    report = {
        "parameters": asdict(parameters),
        "converged_residual_criterion": numerical.converged,
        "iterations": numerical.iterations,
        "seconds": elapsed,
        "coefficient_residual": numerical.coefficient_residual,
        "intercept_error_vs_analytical": abs(
            numerical.value_intercept - analytical.value_intercept
        ),
        "slope_error_vs_analytical": abs(numerical.value_slope - analytical.value_slope),
        "saving_share": numerical.saving_share,
        "saving_share_error_vs_analytical": abs(
            numerical.saving_share - analytical.saving_share
        ),
    }
    if numerical.converged:
        path = rollout(parameters, 1.0, 30, solution=numerical)
        report["max_resource_residual"] = max(
            abs(row.output - row.consumption - row.investment) for row in path
        )
        report["max_relative_euler_residual"] = max(
            abs(1 - parameters.beta * parameters.alpha * later.output
                * earlier.consumption / (later.capital * later.consumption))
            for earlier, later in pairwise(path)
        )
    return report


def compare_transition(parameters, initial_capital, *, max_horizon=2048):
    """Report continuation evidence, not an infinite-horizon error guarantee."""
    started = perf_counter()
    result = solve_transition(parameters, initial_capital, 40, max_horizon=max_horizon)
    report = asdict(result)
    report.pop("periods")
    report["seconds"] = perf_counter() - started
    report["stationary_allocation"] = asdict(steady_state(parameters))
    if result.converged:
        report["first_period"] = asdict(result.periods[0])
        report["last_displayed_period"] = asdict(result.periods[-1])
        if parameters.depreciation == 1:
            alpha, beta, chi = parameters.alpha, parameters.beta, parameters.leisure_weight
            labor = (1 - alpha) / ((1 - alpha) + chi * (1 - alpha * beta))
            report["exact_policy_saving_share_error"] = max(
                abs(row.investment / row.output - alpha * beta) for row in result.periods
            )
            report["exact_policy_labor_error"] = max(
                abs(row.labor - labor) for row in result.periods
            )
    return report


if __name__ == "__main__":
    cases = (
        Parameters(),
        Parameters(alpha=.3, beta=.9, productivity=2),
        Parameters(alpha=.8, beta=.5, productivity=.2),
        Parameters(beta=.9999),
        Parameters(beta=nextafter(1.0, 0.0), productivity=2),
    )
    print(json.dumps({
        "scope": "Isolated deterministic optimal-growth references; not the monetary app",
        "caution": "Residual convergence is not a value-error bound; compare with the analytical reference.",
        "cases": [compare(parameters) for parameters in cases],
        "transition_cases": [
            compare_transition(TransitionParameters(), 1.0),
            compare_transition(TransitionParameters(), 100.0),
            compare_transition(TransitionParameters(depreciation=1), 1.0),
            compare_transition(TransitionParameters(), .05, max_horizon=64),
        ],
    }, indent=2, allow_nan=False))
