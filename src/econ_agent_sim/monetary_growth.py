"""Isolated symmetric monetary transitions, not the running application.

The original interior solver remains an independent benchmark. The constrained
solver also supports zero investment and distributions, while checking that
opening funding binds optimally. Every accepted path is checked against monetary
budgets and optimality, including its computational tail. See the monetary
transition and boundary documents; neither routine changes the running app.
"""

from dataclasses import dataclass, fields
from itertools import pairwise
from math import fsum, isfinite, sqrt

from .textbook_growth import (
    TransitionParameters,
    TransitionPeriod,
    _boundary_path,
)
from .textbook_growth import (
    steady_state as real_steady_state,
)


def _number(name, value, *, zero=False):
    if (type(value) not in (int, float) or not isfinite(value)
            or (value < 0 if zero else value <= 0)):
        raise ValueError(f"{name} must be finite and {'nonnegative' if zero else 'positive'}.")
    return float(value)


@dataclass(frozen=True)
class Parameters:
    beta: float = .95
    depreciation: float = .1
    leisure_weight: float = 1.
    money_weight: float = .05

    def __post_init__(self):
        for name in ("beta", "depreciation", "leisure_weight", "money_weight"):
            _number(name, getattr(self, name))
        if self.beta >= 1 or self.depreciation > 1:
            raise ValueError("Use 0 < beta < 1 and 0 < depreciation <= 1.")


@dataclass(frozen=True)
class Period:
    number: int
    capital: float
    next_capital: float
    output: float
    consumption: float
    investment: float
    labor: float
    goods_price: float
    money_wage: float
    distribution: float
    household_cash: float
    firm_cash: float
    next_household_cash: float
    next_firm_cash: float
    discount_factor: float
    funding_multiplier: float
    capital_shadow_value: float
    cash_shadow_value: float = 1.
    next_cash_shadow_value: float = 1.
    next_capital_shadow_value: float | None = None


@dataclass(frozen=True)
class SettlementState:
    phase: str
    household_cash: tuple[float, float]
    firm_cash: tuple[float, float]


@dataclass(frozen=True)
class Result:
    parameters: Parameters
    initial_capital: float
    initial_firm_cash_share: float
    periods: tuple[Period, ...]
    converged: bool
    status: str
    horizon: int
    comparison_horizon: int | None
    iterations: int
    residuals: dict[str, float]
    prefix_difference: float | None
    terminal_gap: float | None
    failure_period: int | None

    @property
    def max_equation_residual(self):
        return max(self.residuals.values()) if self.residuals else None


def _auxiliary(p):
    if type(p) is not Parameters:
        raise ValueError("The monetary reference needs monetary Parameters.")
    return TransitionParameters(
        beta=p.beta, depreciation=p.depreciation,
        leisure_weight=p.leisure_weight / p.beta,
    )


def _cash_levels(p):
    denominator = 1 - p.beta + p.money_weight
    spending = .5 * (1 - p.beta) / denominator
    household = .5 * p.money_weight / denominator
    if not all(isfinite(x) and 0 < x < .5 for x in (spending, household)):
        raise ArithmeticError("The stationary cash split is unrepresentable.")
    return spending, household


def _lift(p, allocations, initial_firm_cash):
    spending, closing_household = _cash_levels(p)
    firm, household = initial_firm_cash, .5 - initial_firm_cash
    rows = []
    for number, x in enumerate(allocations, 1):
        price = spending / x.consumption
        wage = p.beta * price * .5 * x.output / x.labor
        row = Period(
            number, x.capital, x.next_capital, x.output, x.consumption,
            x.investment, x.labor, price, wage, firm - wage * x.labor,
            household, firm, closing_household, spending, p.beta, 1 - p.beta,
            p.beta * price * (1 - p.depreciation + .5 * x.output / x.capital),
            1., 1., price,
        )
        if not all(isfinite(getattr(row, f.name)) for f in fields(row)):
            raise ArithmeticError("Monetary quantities exceed numerical range.")
        rows.append(row)
        firm, household = spending, closing_household
    return tuple(rows)


def steady_state(parameters):
    """Return the documented positive stationary equilibrium, per entity."""
    auxiliary = _auxiliary(parameters)
    target = real_steady_state(auxiliary)
    # The stationary real record lacks next_capital; use the same numerical
    # period constructor as the transition kernel to supply the complete state.
    allocation = TransitionPeriod(
        1, target.capital, target.output, target.consumption, target.investment,
        target.capital, target.labor, target.real_wage,
    )
    spending, _ = _cash_levels(parameters)
    row = _lift(parameters, (allocation,), spending)[0]
    if _regime_failure(row) is not None:
        raise ArithmeticError("The stationary monetary regime is unrepresentable.")
    return row


def _regime_failure(row):
    if row.distribution <= 0:
        return "unsupported_nonpositive_distribution"
    if not 0 < row.investment < row.output:
        return "unsupported_investment_boundary"
    if not (0 < row.labor < 1 and row.consumption > 0
            and min(row.goods_price, row.money_wage, row.household_cash,
                    row.firm_cash, row.next_household_cash, row.next_firm_cash) > 0):
        return "unsupported_nonpositive_state"
    return None


def settle_period(row, *, tolerance=1e-10):
    """Execute all two-household/two-firm payments without borrowing or mutation.

    Each household owns half of each firm, works half its hours at each firm,
    and buys half its consumption from each firm. Tiny rounding residuals are
    checked, not clipped or used to create money.
    """
    _number("Settlement tolerance", tolerance)
    for name in ("household_cash", "firm_cash", "next_household_cash", "next_firm_cash",
                 "distribution", "labor", "consumption"):
        _number(name, getattr(row, name), zero=True)
    for name in ("goods_price", "money_wage"):
        _number(name, getattr(row, name))
    households, firms = [row.household_cash] * 2, [row.firm_cash] * 2
    snapshots = []

    def snapshot(phase):
        amounts = households + firms
        if (not all(isfinite(x) for x in amounts) or min(amounts) < -tolerance
                or abs(fsum(amounts) - 1) > tolerance):
            raise ArithmeticError(f"Unfunded or unbalanced settlement at {phase}.")
        snapshots.append(SettlementState(phase, tuple(households), tuple(firms)))

    snapshot("opening")
    for phase, amount, reverse in (
        ("owner_distributions", row.distribution / 2, False),
        ("wages", row.money_wage * row.labor / 2, False),
        ("goods_purchases", row.goods_price * row.consumption / 2, True),
    ):
        for j in range(2):
            for i in range(2):
                if reverse:
                    households[i] -= amount
                    firms[j] += amount
                else:
                    firms[j] -= amount
                    households[i] += amount
                if min(households + firms) < -tolerance:
                    raise ArithmeticError(f"Unfunded transfer at {phase}.")
        snapshot(phase)
    if (max(abs(x - row.next_firm_cash) for x in firms) > tolerance
            or max(abs(x - row.next_household_cash) for x in households) > tolerance):
        raise ArithmeticError("Settlement does not reproduce the closing states.")
    return tuple(snapshots)


def firm_deviation_gap(
    parameters, row, *, capital, firm_cash, distribution, labor, investment,
):
    """One-period supporting-plane gap, including inactive/corner deviations.

    The supplied dated cash/capital shadow values determine the supporting bound.
    A missing next capital value preserves the original interior price convention.
    The path auditor separately checks adjacent valuations. This function alone
    does not assert an arbitrary supplied row is an equilibrium.
    """
    if type(parameters) is not Parameters:
        raise ValueError("The monetary reference needs monetary Parameters.")
    for name, value in (("Capital", capital), ("Firm cash", firm_cash),
                        ("Distribution", distribution), ("Labor", labor),
                        ("Investment", investment)):
        _number(name, value, zero=True)
    output = sqrt(capital) * sqrt(labor)
    slack = fsum((firm_cash, -distribution, -row.money_wage * labor))
    if slack < -1e-12 * max(firm_cash, 1e-300) or investment > output:
        raise ValueError("The proposed firm deviation is not feasible.")
    next_cash = slack + row.goods_price * (output - investment)
    next_capital = (1 - parameters.depreciation) * capital + investment
    next_value = _next_capital_value(row)
    gap = fsum((distribution, row.discount_factor * row.next_cash_shadow_value * next_cash,
                row.discount_factor * next_value * next_capital,
                -row.cash_shadow_value * firm_cash, -row.capital_shadow_value * capital))
    if not isfinite(gap):
        raise ArithmeticError("The deviation bound exceeds numerical range.")
    return gap


def _relative(left, right):
    scale = max(abs(left), abs(right))
    return abs(left - right) / scale if scale else 0.


def _next_capital_value(row):
    return (row.goods_price if row.next_capital_shadow_value is None
            else row.next_capital_shadow_value)


def _distance(left, right):
    differences = []
    for field in fields(Period):
        name = field.name
        if name == "number":
            continue
        if name == "next_capital_shadow_value":
            differences.append(_relative(_next_capital_value(left), _next_capital_value(right)))
        elif name in ("investment", "distribution", "funding_multiplier"):
            scale_name = {"investment": "output", "distribution": "firm_cash",
                          "funding_multiplier": "cash_shadow_value"}[name]
            scale = max(getattr(left, scale_name), getattr(right, scale_name))
            differences.append(abs(getattr(left, name) - getattr(right, name)) / scale)
        else:
            differences.append(_relative(getattr(left, name), getattr(right, name)))
    differences.append(_relative(1 - left.labor, 1 - right.labor))
    return max(differences)


def _audit(p, rows, tolerance):
    errors = {}

    def record(name, value):
        if not isfinite(value):
            raise ArithmeticError("An economic residual is not finite.")
        errors[name] = max(errors.get(name, 0.), abs(value))

    for row in rows:
        k, y, c, labor = row.capital, row.output, row.consumption, row.labor
        price, wage, q = row.goods_price, row.money_wage, row.discount_factor
        spending, payroll = price * c, wage * labor
        record("production", _relative(y, sqrt(k) * sqrt(labor)))
        record("goods_clearing", (y - c - row.investment) / y)
        record("capital_transition", _relative(
            row.next_capital, (1 - p.depreciation) * k + row.investment,
        ))
        record("household_labor", 1 - wage * (1 - labor) / (price * p.leisure_weight * c))
        b, bn, an = row.cash_shadow_value, row.next_cash_shadow_value, _next_capital_value(row)
        record("firm_labor", 1 - q * bn * price * .5 * y / (labor * b * wage))
        slack = fsum((row.firm_cash, -row.distribution, -payroll))
        record("opening_funding", slack / row.firm_cash)
        record("cash_adjoint", (b - q * bn - row.funding_multiplier) / b)
        record("cash_value_inequality", min(0., b - 1) / b)
        record("funding_inequality", min(0., row.funding_multiplier) / b)
        record("distribution_complementarity", row.distribution / row.firm_cash * (b - 1) / b)
        record("funding_complementarity", row.funding_multiplier * slack / row.firm_cash)
        capital_gap = 1 - an / (price * bn)
        record("investment_inequality", min(0., capital_gap))
        record("investment_complementarity", row.investment / y * capital_gap)
        record("capital_adjoint", _relative(
            row.capital_shadow_value,
            q * ((1 - p.depreciation) * an + price * bn * .5 * y / k),
        ))
        record("household_budget", fsum((row.household_cash, row.distribution,
                                        payroll, -spending, -row.next_household_cash)) / .5)
        record("firm_budget", fsum((slack, price * (y - row.investment),
                                   -row.next_firm_cash)) / .5)
        record("money_conservation", 2 * (row.firm_cash + row.household_cash) - 1)
        record("closing_money", 2 * (row.next_firm_cash + row.next_household_cash) - 1)
        record("firm_supporting_bound", firm_deviation_gap(
            p, row, capital=k, firm_cash=row.firm_cash, distribution=row.distribution,
            labor=labor, investment=row.investment,
        ) / (b * row.firm_cash + row.capital_shadow_value * k))
        # Execute each bilateral transfer, not merely the consolidated budgets.
        settle_period(row, tolerance=tolerance)
    for row, following in pairwise(rows):
        spending = row.goods_price * row.consumption
        next_spending = following.goods_price * following.consumption
        record("household_money", 1 - p.money_weight * spending / row.next_household_cash
               - p.beta * spending / next_spending)
        record("owner_discount", _relative(row.discount_factor, p.beta * spending / next_spending))
        record("firm_capital", _relative(_next_capital_value(row), following.capital_shadow_value))
        record("firm_cash_value", _relative(row.next_cash_shadow_value, following.cash_shadow_value))
        record("state_continuity", max(
            _relative(row.next_capital, following.capital),
            _relative(row.next_firm_cash, following.firm_cash),
            _relative(row.next_household_cash, following.household_cash),
        ))
    return errors


def solve_transition(
    parameters, initial_capital, periods, *, initial_firm_cash_share=.5,
    horizon=64, max_horizon=2048, max_iterations=80,
    tolerance=1e-10, continuation_tolerance=1e-8,
):
    """Find a checked path in the disclosed interior monetary regime.

    Unsupported corners and unverified numerical paths return no history. Such
    failure does not establish nonexistence of equilibrium in other regimes.
    Horizon extension supplies evidence, not an infinite-horizon error bound.
    """
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
    previous, previous_horizon, comparison_horizon = None, None, None
    residuals, difference, terminal, failure_period = {}, None, None, None
    status = "horizon_budget_exhausted"

    def result(rows=()):
        return Result(parameters, initial, share, tuple(rows), status == "converged",
                      status, attempted, comparison_horizon, iterations, residuals,
                      difference, terminal, failure_period)

    try:
        auxiliary = _auxiliary(parameters)
        target_real = real_steady_state(auxiliary)
        target = steady_state(parameters)
    except (ArithmeticError, ValueError):
        status = "stationary_allocation_unrepresentable"
        return result()
    while size <= max_horizon:
        attempted, comparison_horizon = size, previous_horizon
        difference, terminal, residuals = None, None, {}
        try:
            choices, used, state = _boundary_path(
                auxiliary, initial, target_real, size, max_iterations, tolerance,
            )
            iterations += used
            if state != "equations_converged":
                status = state
                return result()
            rows = _lift(parameters, (x.period for x in choices), share / 2)
            for row in rows:
                reason = _regime_failure(row)
                if reason:
                    status, failure_period = reason, row.number
                    return result()
            residuals = _audit(parameters, rows, tolerance)
            terminal = max(_distance(rows[-1], target),
                           _relative(rows[-1].goods_price, target.capital_shadow_value))
        except (ArithmeticError, ValueError):
            status = "numerical_failure"
            previous, previous_horizon, comparison_horizon = None, None, None
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


def solve_constrained_transition(
    parameters, initial_capital, periods, *, initial_firm_cash_share=.5,
    horizon=64, max_horizon=2048, max_iterations=80,
    tolerance=1e-10, continuation_tolerance=1e-8,
):
    """Monetary transitions with zero-I/zero-D corners and binding opening funding.

    Firm cash/capital shadow values and complementarity are solved jointly.
    Cash-retention regimes are not imposed away: a negative funding multiplier
    rejects the candidate as unsupported. No failed solve returns usable history.
    """
    from ._monetary_boundaries import solve

    return solve(
        parameters, initial_capital, periods,
        initial_firm_cash_share=initial_firm_cash_share, horizon=horizon,
        max_horizon=max_horizon, max_iterations=max_iterations,
        tolerance=tolerance, continuation_tolerance=continuation_tolerance,
    )
