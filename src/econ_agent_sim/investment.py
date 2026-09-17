"""Conditional neoclassical user-cost investment with an internal budget.

Expected real wage and pre-sales payroll funds stay at their current values.
The capital target maximizes forecast operating surplus less user cost, not
lifetime dividends. See docs/forward_investment.md for the textbook mapping.
All public investment amounts here are money values; settlement converts to X.
"""

from math import sqrt

from econ_agent_sim.domain import TOLERANCE
from econ_agent_sim.numerics import require_finite

TIE_TOLERANCE = 1e-12


def _forecast(firm, capital, production_value, wage_bill, funding, price, wage):
    require_finite(
        "Investment inputs", capital, production_value, wage_bill, funding, price, wage
    )
    if min(capital, price, wage) <= 0 or min(funding, wage_bill) < 0:
        raise ValueError("Investment needs positive capital/prices and non-negative cash.")
    gross = production_value - wage_bill
    if gross < 0:
        raise ValueError("An internally financed investment needs non-negative surplus.")
    budget = firm.reinvestment_rate * gross
    base = (1 - firm.depreciation_rate) * capital
    upper = base + budget / price
    gamma = .25 * firm.productivity**2 * (price / wage)
    coefficient = .5 * firm.productivity * sqrt(funding / wage)
    cost = firm.required_return + firm.depreciation_rate
    require_finite("Investment forecast", budget, base, upper, gamma, coefficient, cost)
    if min(base, gamma) <= 0 or (funding > 0 and coefficient <= 0):
        raise ValueError("The investment forecast is below numerical precision.")
    return budget, base, upper, gamma, coefficient, cost


def _marginal(capital, gamma, coefficient):
    return min(gamma, coefficient / sqrt(capital))


def investment_bounds(firm, capital, production_value, wage_bill, funding, price, wage):
    """Money-value interval of optimal investment, including a flat optimum.

    The percentage path deliberately uses exactly the released arithmetic.
    A tiny relative marginal-return tolerance resolves floating-point ties; final
    settlement independently checks the concave objective's KKT conditions.
    """
    if firm.investment_policy == "percentage":
        value = firm.reinvestment_rate * (production_value - wage_bill)
        return value, value
    budget, base, upper, gamma, coefficient, cost = _forecast(
        firm, capital, production_value, wage_bill, funding, price, wage
    )
    if budget == 0 or coefficient == 0:
        return 0.0, 0.0
    if cost == 0:
        return budget, budget
    if abs(gamma - cost) <= TIE_TOLERANCE * max(gamma, cost):
        # g'(k)=gamma on the cash-unconstrained region. Every feasible capital
        # there is an argmax when gamma equals user cost. Do not force I=0 when
        # a different member of this same argmax is needed for goods clearing.
        root_kink = coefficient / gamma
        if root_kink <= sqrt(base):
            return 0.0, 0.0
        if root_kink >= sqrt(upper):
            return 0.0, budget
        return 0.0, min(budget, max(0.0, price * (root_kink**2 - base)))
    if _marginal(base, gamma, coefficient) <= cost:
        return 0.0, 0.0
    if _marginal(upper, gamma, coefficient) >= cost:
        return budget, budget
    # The previous comparisons bound this square within the finite interval.
    target = (coefficient / cost) ** 2
    value = min(budget, max(0.0, price * (target - base)))
    require_finite("Chosen investment", value)
    return value, value


def investment_value(firm, capital, production_value, wage_bill, funding, price, wage):
    """Smallest optimal amount; market clearing may select another flat optimum."""
    return investment_bounds(
        firm, capital, production_value, wage_bill, funding, price, wage
    )[0]


def certify_investment(
    firm, capital, production_value, wage_bill, funding, price, wage, selected_value
):
    """Check funding and the concave objective's first-order conditions directly."""
    require_finite("Selected investment", selected_value)
    if firm.investment_policy == "percentage":
        expected = firm.reinvestment_rate * (production_value - wage_bill)
        return abs(selected_value - expected) <= TOLERANCE * max(
            abs(selected_value), abs(expected)
        )
    budget, base, _, gamma, coefficient, cost = _forecast(
        firm, capital, production_value, wage_bill, funding, price, wage
    )
    value_tolerance = TOLERANCE * max(budget, abs(selected_value))
    if selected_value < -value_tolerance or selected_value > budget + value_tolerance:
        return False
    if budget == 0:
        return selected_value == 0
    marginal = _marginal(base + max(0.0, selected_value) / price, gamma, coefficient)
    tolerance = TOLERANCE * max(marginal, cost)
    if selected_value <= value_tolerance and marginal <= cost + tolerance:
        return True
    if budget - selected_value <= value_tolerance and marginal >= cost - tolerance:
        return True
    return abs(marginal - cost) <= tolerance


def investment_diagnostics(
    firm, capital, production_value, wage_bill, funding, price, wage, selected_value
):
    """Auditable, finite forecast evidence for one completed period's decision."""
    budget, base, _, gamma, coefficient, cost = _forecast(
        firm, capital, production_value, wage_bill, funding, price, wage
    )
    chosen_capital = base + selected_value / price
    marginal = _marginal(chosen_capital, gamma, coefficient)
    real_funding = funding / price
    if gamma <= coefficient / sqrt(chosen_capital):
        expected_surplus = gamma * chosen_capital
    else:
        expected_surplus = 2 * coefficient * sqrt(chosen_capital) - real_funding
    lower, upper = investment_bounds(
        firm, capital, production_value, wage_bill, funding, price, wage
    )
    indifferent = upper > lower
    if indifferent:
        reason = "indifferent"
    elif budget == 0 or selected_value >= budget * (1 - TOLERANCE):
        reason = "budget_limited"
    elif selected_value == 0:
        reason = "returns_below_cost"
    else:
        reason = "interior"
    require_finite("Investment forecast evidence", expected_surplus, marginal, real_funding)
    return {
        "policy": "user_cost",
        "required_return": firm.required_return,
        "user_cost": cost,
        "expected_marginal_return": marginal,
        "investment_budget_quantity": budget / price,
        "investment_quantity": selected_value / price,
        "expected_surplus": expected_surplus,
        "forecast_real_wage": wage / price,
        "forecast_payroll_cash_real": real_funding,
        "reason": reason,
        "tie_selected": indifferent,
    }
