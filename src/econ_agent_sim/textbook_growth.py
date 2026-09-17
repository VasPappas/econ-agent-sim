"""Isolated textbook optimal-growth benchmark, not the live economy.

Fixed labor, deterministic Cobb-Douglas output, log consumption utility and
full depreciation. Bellman iteration preserves a + b*log(k) exactly, so no
capital grid, terminal-value guess or new runtime dependency is required.
See docs/textbook_foundation.md for sources and the limits of this benchmark.
"""

from dataclasses import dataclass
from math import exp, isfinite, log, log1p


def _positive(name, value):
    if type(value) not in (int, float) or not isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be a finite positive number.")
    return float(value)


@dataclass(frozen=True)
class Parameters:
    alpha: float = 0.5
    beta: float = 0.95
    productivity: float = 1.0

    def __post_init__(self):
        for name in ("alpha", "beta", "productivity"):
            _positive(name, getattr(self, name))
        if self.alpha >= 1 or self.beta >= 1:
            raise ValueError("Alpha and beta must each be strictly between zero and one.")


@dataclass(frozen=True)
class PolicyResult:
    parameters: Parameters
    value_intercept: float
    value_slope: float
    saving_share: float
    iterations: int
    coefficient_residual: float
    converged: bool
    method: str


@dataclass(frozen=True)
class GrowthPeriod:
    number: int
    capital: float
    output: float
    consumption: float
    investment: float
    next_capital: float


def _bellman(parameters, intercept, slope):
    q = parameters.beta * slope
    # x*log(x) tends to zero at zero; this is the first finite-horizon iterate.
    if q == 0:
        investment_term = 0.0
    elif q <= 1:
        investment_term = q * (log(q) - log1p(q))
    else:
        investment_term = -q * log1p(1 / q)
    next_intercept = (
        (1 + q) * log(parameters.productivity) - log1p(q)
        + investment_term + parameters.beta * intercept
    )
    next_slope = parameters.alpha * (1 + q)
    if not all(isfinite(value) for value in (next_intercept, next_slope)):
        raise ArithmeticError("The textbook value function exceeds numerical range.")
    return next_intercept, next_slope


def _result(parameters, intercept, slope, iterations, tolerance, method):
    next_intercept, next_slope = _bellman(parameters, intercept, slope)
    residual = max(abs(next_intercept - intercept), abs(next_slope - slope))
    q = parameters.beta * slope
    share = q / (1 + q)
    if not 0 < share < 1:
        raise ArithmeticError("The saving share is below numerical precision.")
    return PolicyResult(
        parameters, intercept, slope, share, iterations, residual,
        residual <= tolerance, method,
    )


def solve_growth(parameters, *, tolerance=1e-10, max_iterations=10_000):
    """Bellman iteration on exact affine-log coefficients, starting from zero.

    The returned residual is in coefficient space, not a uniform bound on value
    over every positive capital stock. Budget exhaustion returns converged=False.
    Near beta=1 even a converged result can have appreciable coefficient error;
    use the separate analytical solution to assess accuracy for this benchmark.
    """
    _positive("Tolerance", tolerance)
    if type(max_iterations) is not int or max_iterations < 1:
        raise ValueError("Use a positive whole iteration budget.")
    intercept, slope = 0.0, 0.0
    for iteration in range(1, max_iterations + 1):
        intercept, slope = _bellman(parameters, intercept, slope)
        result = _result(
            parameters, intercept, slope, iteration, tolerance,
            "affine_log_bellman_iteration",
        )
        if result.converged:
            return result
    return result


def exact_solution(parameters):
    """Analytical infinite-horizon oracle; independent of iterative stopping."""
    share = parameters.alpha * parameters.beta
    slope = parameters.alpha / (1 - share)
    log_share = log(parameters.alpha) + log(parameters.beta)
    log_productivity = log(parameters.productivity)
    intercept = (
        log1p(-share) + log_productivity
        + parameters.beta * slope * (log_share + log_productivity)
    ) / (1 - parameters.beta)
    if not isfinite(intercept) or not 0 < share < 1:
        raise ArithmeticError("The analytical benchmark exceeds numerical precision.")
    next_intercept, next_slope = _bellman(parameters, intercept, slope)
    return PolicyResult(
        parameters, intercept, slope, share, 0,
        max(abs(next_intercept - intercept), abs(next_slope - slope)),
        True, "analytical_log_full_depreciation",
    )


def evaluate_value(solution, capital):
    _positive("Capital", capital)
    value = solution.value_intercept + solution.value_slope * log(capital)
    if not isfinite(value):
        raise ArithmeticError("The textbook value exceeds numerical range.")
    return value


def rollout(parameters, initial_capital, periods, *, solution=None):
    """Generate reference allocations; never mutate a Tiny Economy workspace."""
    capital = _positive("Initial capital", initial_capital)
    if type(periods) is not int or periods < 1:
        raise ValueError("Use a positive whole number of periods.")
    solution = solve_growth(parameters) if solution is None else solution
    if solution.parameters != parameters:
        raise ValueError("The policy was solved for different textbook parameters.")
    if not solution.converged:
        raise ValueError("The textbook policy has not met its convergence criterion.")
    share = solution.saving_share
    if not isfinite(share) or not 0 < share < 1:
        raise ValueError("The saving share must lie strictly between zero and one.")
    history = []
    for number in range(1, periods + 1):
        try:
            output = exp(log(parameters.productivity) + parameters.alpha * log(capital))
        except OverflowError as error:
            raise ArithmeticError("Textbook output exceeds numerical range.") from error
        investment, consumption = share * output, (1 - share) * output
        if not all(isfinite(value) and value > 0 for value in (output, investment, consumption)):
            raise ArithmeticError("The reference allocation is below numerical precision.")
        history.append(GrowthPeriod(number, capital, output, consumption, investment, investment))
        capital = investment
    return tuple(history)
