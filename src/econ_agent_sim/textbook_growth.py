"""Isolated textbook optimal-growth references, not the live economy.

Fixed labor, deterministic Cobb-Douglas output, log consumption utility and
full depreciation. Bellman iteration preserves a + b*log(k) exactly, so no
capital grid, terminal-value guess or new runtime dependency is required.
The transition reference adds partial depreciation and log leisure using a
boundary-value solve with explicit horizon-extension checks. See
docs/growth_transition.md for the numerical method and its limits.
"""

from dataclasses import dataclass
from itertools import pairwise
from math import exp, fsum, hypot, isfinite, log, log1p, sqrt


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
    if type(parameters) is not Parameters:
        raise ValueError("The fixed-labor/full-depreciation solver needs Parameters.")
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
    if type(parameters) is not Parameters:
        raise ValueError("The fixed-labor/full-depreciation oracle needs Parameters.")
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
    if type(parameters) is not Parameters:
        raise ValueError("The fixed-labor/full-depreciation rollout needs Parameters.")
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


@dataclass(frozen=True)
class TransitionParameters(Parameters):
    """Infinite-horizon log consumption/leisure and reversible capital."""

    depreciation: float = 0.1
    leisure_weight: float = 1.0

    def __post_init__(self):
        super().__post_init__()
        _positive("Leisure weight", self.leisure_weight)
        if (type(self.depreciation) not in (int, float)
                or not isfinite(self.depreciation)
                or not 0 <= self.depreciation <= 1):
            raise ValueError("Depreciation must be between zero and one.")


@dataclass(frozen=True)
class SteadyState:
    capital: float
    labor: float
    output: float
    consumption: float
    investment: float
    real_wage: float


@dataclass(frozen=True)
class TransitionPeriod:
    number: int
    capital: float
    output: float
    consumption: float
    investment: float
    next_capital: float
    labor: float
    real_wage: float


@dataclass(frozen=True)
class TransitionResult:
    parameters: TransitionParameters
    initial_capital: float
    periods: tuple[TransitionPeriod, ...]
    converged: bool
    status: str
    horizon: int
    comparison_horizon: int | None
    iterations: int
    max_euler_residual: float | None
    max_labor_residual: float | None
    max_resource_residual: float | None
    prefix_difference: float | None
    terminal_gap: float | None


def steady_state(parameters):
    """Analytical stationary allocation for the reversible-capital reference."""
    if type(parameters) is not TransitionParameters:
        raise ValueError("The labor-choice reference needs TransitionParameters.")
    a, b, A = parameters.alpha, parameters.beta, parameters.productivity
    delta, chi = parameters.depreciation, parameters.leisure_weight
    r = (1 - b) / b
    try:
        x = exp((log(a) + log(A) - log(r + delta)) / (1 - a))
        wage = (1 - a) * A * x**a
        consumption_per_labor = x * (r + (1 - a) * delta) / a
        labor = wage / (wage + chi * consumption_per_labor)
        capital = x * labor
        output = A * capital**a * labor ** (1 - a)
        consumption = consumption_per_labor * labor
        values = (capital, labor, output, consumption, wage)
        if not all(isfinite(v) and v > 0 for v in values) or labor >= 1:
            raise ArithmeticError("Stationary allocation exceeds numerical precision.")
        return SteadyState(capital, labor, output, consumption, delta * capital, wage)
    except (OverflowError, ZeroDivisionError) as error:
        raise ArithmeticError("Stationary allocation exceeds numerical precision.") from error


@dataclass(frozen=True)
class _PeriodChoice:
    period: TransitionPeriod
    v1: float
    v2: float
    v11: float
    v12: float
    v22: float


def _transition_choice(p, capital, next_capital, number):
    """Solve static labor at two given capital stocks and form the value Hessian."""
    a, chi, carry = p.alpha, p.leisure_weight, 1 - p.depreciation
    scale = p.productivity * capital**a
    offset = carry * capital - next_capital
    if next_capital <= 0 or not isfinite(scale) or next_capital >= scale + carry * capital:
        raise ArithmeticError("The boundary path cannot fund positive consumption.")
    coefficient = chi * (offset / scale)
    if a == .5:
        # The positive root in sqrt(labor), written to avoid cancellation.
        linear = chi + 1 - a
        radical = hypot(coefficient, 2 * sqrt(linear * (1 - a)))
        root = (2 * (1 - a) / (radical + coefficient) if coefficient >= 0
                else (radical - coefficient) / (2 * linear))
        labor = root * root
    else:
        # With a negative coefficient F need not be increasing everywhere,
        # but F(0)<0, F(1)>0 and its unique positive root is safely bracketed.
        low, high = 0., 1.
        for _ in range(100):
            labor = (low + high) / 2
            if labor == low or labor == high:
                break
            value = (chi + 1 - a) * labor + coefficient * labor**a - (1 - a)
            if value > 0:
                high = labor
            else:
                low = labor
    if not 0 < labor < 1:
        raise ArithmeticError("Labor is outside the representable interior.")
    output = scale * labor ** (1 - a)
    consumption = fsum((output, carry * capital, -next_capital))
    if not isfinite(consumption) or consumption <= 0:
        raise ArithmeticError("Consumption is outside the representable interior.")
    fk, fl = a * output / capital, (1 - a) * output / labor
    fkk, fll = (a - 1) * fk / capital, -a * fl / labor
    fkl = (1 - a) * fk / labor
    inv_c, q = 1 / consumption, carry + fk
    u11 = fkk * inv_c - (q * inv_c)**2
    u12, u22 = q * inv_c**2, -inv_c**2
    u1l = fkl * inv_c - q * fl * inv_c**2
    u2l = fl * inv_c**2
    ull = fll * inv_c - (fl * inv_c)**2 - chi / (1 - labor)**2
    v11 = u11 - (u1l / ull) * u1l
    v12 = u12 - (u1l / ull) * u2l
    v22 = u22 - (u2l / ull) * u2l
    if not all(isfinite(v) for v in (q * inv_c, inv_c, v11, v12, v22)):
        raise ArithmeticError("Choice derivatives exceed numerical precision.")
    record = TransitionPeriod(
        number, capital, output, consumption, next_capital - carry * capital,
        next_capital, labor, fl,
    )
    return _PeriodChoice(record, q * inv_c, -inv_c, v11, v12, v22)


def _path_choices(p, capital):
    return tuple(_transition_choice(p, k, following, t + 1)
                 for t, (k, following) in enumerate(pairwise(capital)))


def _gradients(p, choices):
    return [previous.v2 + p.beta * following.v1
            for previous, following in pairwise(choices)]


def _tridiagonal(lower, diagonal, upper, rhs):
    """Thomas elimination; report loss of a finite negative Hessian pivot."""
    diagonal, rhs = list(diagonal), list(rhs)
    for i in range(len(diagonal)):
        if not isfinite(diagonal[i]) or diagonal[i] >= 0:
            raise ArithmeticError("The transition Hessian lost a negative pivot.")
        if i + 1 < len(diagonal):
            factor = lower[i] / diagonal[i]
            diagonal[i + 1] -= factor * upper[i]
            rhs[i + 1] -= factor * rhs[i]
    direction = [0.] * len(diagonal)
    for i in range(len(diagonal) - 1, -1, -1):
        numerator = rhs[i] - (upper[i] * direction[i + 1] if i + 1 < len(rhs) else 0)
        direction[i] = numerator / diagonal[i]
    if not all(isfinite(x) for x in direction):
        raise ArithmeticError("The Newton step is not finite.")
    return direction


def _boundary_path(p, initial, target, horizon, max_iterations, tolerance):
    # A feasible saving rule supplies a starting guess, not the solved policy.
    share = target.capital / (target.output + (1 - p.depreciation) * target.capital)
    capital = [initial]
    for _ in range(horizon - 1):
        k = capital[-1]
        y = p.productivity * k**p.alpha * target.labor ** (1 - p.alpha)
        capital.append(share * (y + (1 - p.depreciation) * k))
    capital.append(target.capital)
    choices = _path_choices(p, capital)
    for iteration in range(max_iterations + 1):
        gradients = _gradients(p, choices)
        weights = [x.period.consumption for x in choices[:-1]]
        error = max(abs(g * c) for g, c in zip(gradients, weights))
        if error <= tolerance:
            return choices, iteration, "equations_converged"
        if iteration == max_iterations:
            return choices, iteration, "iteration_budget_exhausted"
        diagonal = [capital[i] * (choices[i - 1].v22 + p.beta * choices[i].v11)
                    for i in range(1, horizon)]
        lower = [capital[i - 1] * choices[i - 1].v12 for i in range(2, horizon)]
        upper = [capital[i + 1] * p.beta * choices[i].v12 for i in range(1, horizon - 1)]
        direction = _tridiagonal(lower, diagonal, upper, [-g for g in gradients])
        step = min(1., 2. / max(2., max(abs(x) for x in direction)))
        for _ in range(45):
            try:
                trial = [initial] + [k * exp(step * change)
                                     for k, change in zip(capital[1:-1], direction)]
                trial.append(target.capital)
                candidate = _path_choices(p, trial)
                # Keep row scales fixed within the line search so this Newton
                # direction is a descent direction for its merit function.
                merit = max(abs(g * c) for g, c in zip(_gradients(p, candidate), weights))
                if merit <= error * (1 - 1e-4 * step) or merit <= tolerance:
                    capital, choices = trial, candidate
                    break
            except (ArithmeticError, ValueError):
                pass
            step /= 2
        else:
            return choices, iteration, "line_search_failed"
    raise AssertionError("Unreachable iteration state")


def _relative(left, right):
    return abs(left - right) / max(abs(left), abs(right))


def _transition_diagnostics(p, choices, target):
    rows = [choice.period for choice in choices]
    euler = max(abs(1 - p.beta * first.consumption * following.v1)
                for first, following in zip(rows, choices[1:]))
    terminal_euler = abs(1 - p.beta * rows[-1].consumption / target.consumption
                         * (1 - p.depreciation + p.alpha * target.output / target.capital))
    labor = max(abs(1 - row.real_wage * (1 - row.labor)
                    / (p.leisure_weight * row.consumption)) for row in rows)
    resources = max(abs(fsum((row.consumption, row.next_capital, -row.output,
                              -(1 - p.depreciation) * row.capital)))
                    / (row.consumption + row.next_capital + row.output)
                    for row in rows)
    terminal = max(terminal_euler, _relative(rows[-1].capital, target.capital),
                   _relative(rows[-1].consumption, target.consumption),
                   _relative(rows[-1].labor, target.labor),
                   _relative(1 - rows[-1].labor, 1 - target.labor))
    return max(euler, terminal_euler), labor, resources, terminal


def _prefix_difference(left, right, periods):
    errors = []
    for old, new in zip(left[:periods], right[:periods]):
        for name in ("capital", "next_capital", "consumption", "labor"):
            errors.append(_relative(getattr(old.period, name), getattr(new.period, name)))
        errors.append(_relative(1 - old.period.labor, 1 - new.period.labor))
    return max(errors)


def solve_transition(
    parameters, initial_capital, periods, *, horizon=64, max_horizon=2048,
    max_iterations=80, tolerance=1e-10, continuation_tolerance=1e-8,
):
    """Approximate the infinite-horizon reference with checked finite boundaries.

    Fix distant capital at its stationary value, solve the concave allocation
    problem, then double the horizon. Acceptance requires economic residuals,
    agreement of the displayed prefix and proximity of the tail to stationarity.
    This is numerical evidence, not a global infinite-horizon error bound or a
    monetary equilibrium. Failed attempts return no usable period history.
    """
    if type(parameters) is not TransitionParameters:
        raise ValueError("The transition solver needs TransitionParameters.")
    initial = _positive("Initial capital", initial_capital)
    _positive("Equation tolerance", tolerance)
    _positive("Continuation tolerance", continuation_tolerance)
    for name, value, minimum in (("Periods", periods, 1), ("Horizon", horizon, 2),
                                 ("Maximum horizon", max_horizon, 2),
                                 ("Iteration budget", max_iterations, 1)):
        if type(value) is not int or value < minimum:
            raise ValueError(f"{name} must be a whole number at least {minimum}.")
    try:
        target = steady_state(parameters)
    except ArithmeticError:
        return TransitionResult(
            parameters, initial, (), False, "stationary_allocation_unrepresentable",
            0, None, 0, None, None, None, None, None,
        )
    size = max(horizon, periods + 16)
    previous, previous_horizon, comparison_horizon = None, None, None
    attempted, iterations, difference = 0, 0, None
    diagnostics = (None, None, None, None)
    status = "horizon_budget_exhausted"
    while size <= max_horizon:
        attempted = size
        comparison_horizon = previous_horizon
        difference = None
        try:
            choices, used, state = _boundary_path(
                parameters, initial, target, size, max_iterations, tolerance,
            )
            iterations += used
            diagnostics = _transition_diagnostics(parameters, choices, target)
        except (ArithmeticError, ValueError):
            previous, previous_horizon, comparison_horizon = None, None, None
            diagnostics = (None, None, None, None)
            status = "numerical_failure"
            size *= 2
            continue
        if state != "equations_converged":
            status = state
            break
        euler, labor, resources, terminal = diagnostics
        interior_euler = max(
            abs(1 - parameters.beta * old.period.consumption
                * (1 - parameters.depreciation
                   + parameters.alpha * new.period.output / new.period.capital)
                / new.period.consumption)
            for old, new in pairwise(choices)
        )
        if max(interior_euler, labor, resources) > tolerance:
            status = "choice_conditions_not_met"
            break
        difference = (_prefix_difference(previous, choices, periods)
                      if previous is not None else None)
        if (difference is not None and difference <= continuation_tolerance
                and terminal <= continuation_tolerance):
            return TransitionResult(
                parameters, initial, tuple(x.period for x in choices[:periods]),
                True, "converged", size, comparison_horizon, iterations,
                euler, labor, resources, difference, terminal,
            )
        previous, previous_horizon = choices, size
        status = "horizon_budget_exhausted"
        size *= 2
    return TransitionResult(
        parameters, initial, (), False, status, attempted, comparison_horizon,
        iterations, *diagnostics[:3], difference, diagnostics[3],
    )
