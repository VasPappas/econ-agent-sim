"""Boundary-value construction for the monetary reference's funded regime."""

from math import exp, fsum, isfinite, log, sqrt

from ._monetary_numerics import solve_blocks
from .monetary_growth import (
    Parameters,
    Period,
    Result,
    _audit,
    _auxiliary,
    _cash_levels,
    _distance,
    _number,
    _relative,
    steady_state,
)
from .textbook_growth import _boundary_path
from .textbook_growth import steady_state as real_steady_state


def _decode(vector):
    blocks = []
    for offset in range(0, len(vector), 4):
        z, u, v, w = vector[offset:offset + 4]
        labor = 1 / (1 + exp(-u)) if u >= 0 else exp(u) / (1 + exp(u))
        k, b, a = exp(z), exp(v), exp(w)
        if not (0 < labor < 1 and min(k, b, a) > 0
                and all(isfinite(x) for x in (k, b, a))):
            raise ArithmeticError("Boundary variables exceed numerical range.")
        blocks.append((k, labor, b, a))
    return blocks


def _equations(p, initial, opening_cash, target, vector):
    spending, _ = _cash_levels(p)
    blocks = _decode(vector)
    capital, cash = initial, opening_cash
    residuals = []
    for t, (next_capital, labor, b, a) in enumerate(blocks):
        if t + 1 < len(blocks):
            bn, an = blocks[t + 1][2:]
        else:
            bn, an = 1., target.capital_shadow_value
        output = sqrt(capital) * sqrt(labor)
        investment = next_capital - (1 - p.depreciation) * capital
        consumption = fsum((output, -investment))
        if consumption <= 0 or not isfinite(consumption):
            raise ArithmeticError("The boundary candidate has no consumption.")
        price = spending / consumption
        wage = spending * p.leisure_weight / (1 - labor)
        distribution = cash - wage * labor
        # All four equations depend only on neighboring four-variable blocks.
        residuals.extend((
            1 - p.beta * bn * price * .5 * output / (labor * b * wage),
            1 - p.beta * ((1 - p.depreciation) * an
                          + price * bn * .5 * output / capital) / a,
            min(investment / output, 1 - an / (price * bn)),
            min(distribution / cash, b - 1),
        ))
        capital, cash = next_capital, spending
    return residuals


def _initial_vector(p, initial, horizon, max_iterations, tolerance):
    auxiliary = _auxiliary(p)
    real_target = real_steady_state(auxiliary)
    choices, used, status = _boundary_path(
        auxiliary, initial, real_target, horizon, max_iterations, tolerance,
    )
    if status != "equations_converged":
        return None, used, status
    spending, _ = _cash_levels(p)
    vector = []
    for choice in choices:
        row = choice.period
        price = spending / row.consumption
        value = p.beta * price * (1 - p.depreciation + .5 * row.output / row.capital)
        vector.extend((log(row.next_capital), log(row.labor / (1 - row.labor)),
                       0., log(value)))
    return vector, used, "initialized"


def _records(p, initial, opening_cash, target, vector, tolerance):
    """Materialize funded records, canonicalizing only residual-sized corners.

    No material economic violation is repaired. All reconstructed quantities,
    budgets and optimality conditions are independently re-audited afterward.
    """
    spending, household_target = _cash_levels(p)
    blocks = _decode(vector)
    capital, cash, household = initial, opening_cash, .5 - opening_cash
    rows = []
    for t, (trial_next, labor, b, a) in enumerate(blocks):
        bn, an = blocks[t + 1][2:] if t + 1 < len(blocks) else (1., target.capital_shadow_value)
        output = sqrt(capital) * sqrt(labor)
        investment = trial_next - (1 - p.depreciation) * capital
        if abs(investment) <= tolerance * output:
            investment = 0.
        if investment < 0:
            raise ArithmeticError("Materially negative investment after solve.")
        next_capital = (1 - p.depreciation) * capital + investment
        wage = spending * p.leisure_weight / (1 - labor)
        distribution = cash - wage * labor
        if abs(distribution) <= tolerance * cash:
            # Solve the active equality exactly rather than pay a negative
            # dividend. Its roundoff-scale labor adjustment is audited below.
            labor = cash / (cash + spending * p.leisure_weight)
            distribution = 0.
            wage = cash / labor
            output = sqrt(capital) * sqrt(labor)
        if distribution < 0:
            raise ArithmeticError("Materially negative distribution after solve.")
        consumption = output - investment
        if not (consumption > 0 and next_capital > 0):
            raise ArithmeticError("Unfunded reconstructed goods or capital.")
        price = spending / consumption
        rows.append(Period(
            t + 1, capital, next_capital, output, consumption, investment, labor,
            price, wage, distribution, household, cash, household_target, spending,
            p.beta, b - p.beta * bn, a, b, bn, an,
        ))
        capital, cash, household = next_capital, spending, household_target
    return tuple(rows)


def solve(
    parameters, initial_capital, periods, *, initial_firm_cash_share,
    horizon, max_horizon, max_iterations, tolerance, continuation_tolerance,
):
    if type(parameters) is not Parameters:
        raise ValueError("The monetary reference needs monetary Parameters.")
    initial = _number("Initial capital", initial_capital)
    share = _number("Initial firm cash share", initial_firm_cash_share)
    if share >= 1:
        raise ValueError("Initial firm cash share must be strictly below one.")
    _number("Equation tolerance", tolerance)
    _number("Continuation tolerance", continuation_tolerance)
    for name, value, minimum in (("Periods", periods, 1), ("Horizon", horizon, 2),
                                 ("Maximum horizon", max_horizon, 2),
                                 ("Iteration budget", max_iterations, 1)):
        if type(value) is not int or value < minimum:
            raise ValueError(f"{name} must be a whole number at least {minimum}.")
    size, attempted, iterations = max(horizon, periods + 16), 0, 0
    previous, previous_horizon, comparison = None, None, None
    residuals, difference, terminal, failure_period = {}, None, None, None
    status = "horizon_budget_exhausted"

    def result(rows=()):
        return Result(parameters, initial, share, tuple(rows), status == "converged",
                      status, attempted, comparison, iterations, residuals,
                      difference, terminal, failure_period)

    try:
        target = steady_state(parameters)
    except (ArithmeticError, ValueError):
        status = "stationary_allocation_unrepresentable"
        return result()
    while size <= max_horizon:
        attempted, comparison = size, previous_horizon
        difference, terminal, residuals = None, None, {}
        try:
            guess, initialized, state = _initial_vector(
                parameters, initial, size, max_iterations, tolerance,
            )
            iterations += initialized
            if guess is None:
                status = "initialization_" + state
                return result()

            def evaluate(vector):
                return _equations(parameters, initial, share / 2, target, vector)

            vector, used, state = solve_blocks(evaluate, guess, max_iterations, tolerance / 10)
            iterations += used
            if state != "equations_converged":
                status = state
                return result()
            rows = _records(parameters, initial, share / 2, target, vector, tolerance)
            residuals = _audit(parameters, rows, tolerance)
            for row in rows:
                if row.funding_multiplier < -tolerance * row.cash_shadow_value:
                    status, failure_period = "unsupported_cash_retention", row.number
                    return result()
            terminal = max(_distance(rows[-1], target),
                           _relative(rows[-1].next_capital, target.capital))
        except (ArithmeticError, ValueError):
            status = "numerical_failure"
            previous, previous_horizon, comparison = None, None, None
            residuals, terminal = {}, None
            size *= 2
            continue
        if max(residuals.values()) > tolerance:
            status = "choice_conditions_not_met"
            return result()
        difference = (max(_distance(old, new) for old, new in
                          zip(previous[:periods], rows[:periods]))
                      if previous is not None else None)
        if (difference is not None and difference <= continuation_tolerance
                and terminal <= continuation_tolerance):
            status = "converged"
            return result(rows[:periods])
        previous, previous_horizon = rows, size
        status = "horizon_budget_exhausted"
        size *= 2
    return result()
