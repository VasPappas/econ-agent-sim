"""Check the proposed monetary stationary equilibrium; not a transition solver.

Run directly with Python. This uses only the standard library and never imports
or changes the application engine. See monetary_foundation.md for the model and
the supporting-plane proof, which is stronger than sampled numerical checks.
"""

import json
from math import isclose


def stationary_case(eta):
    """Construct and independently substitute one documented stationary fixture."""
    beta, delta, chi, alpha, productivity, money = .95, .1, 1., .5, 1., 1.
    capital_product = 1 / beta - 1 + delta
    capital_per_labor = (alpha * productivity / capital_product) ** (1 / (1 - alpha))
    labor_product = (1 - alpha) * productivity * capital_per_labor**alpha
    real_wage = beta * labor_product
    consumption_per_labor = (
        productivity * capital_per_labor**alpha - delta * capital_per_labor
    )
    labor = real_wage / (real_wage + chi * consumption_per_labor)
    capital = capital_per_labor * labor
    output = productivity * capital**alpha * labor ** (1 - alpha)
    investment = delta * capital
    consumption = output - investment
    firm_cash = money * (1 - beta) / (2 * (1 - beta + eta))
    household_cash = money * eta / (2 * (1 - beta + eta))
    price = firm_cash / consumption
    wage = price * real_wage
    payroll = wage * labor
    distribution = firm_cash - payroll
    marginal_money = 1 / (price * consumption)
    funding_multiplier = 1 - beta

    # Independent economic equations, evaluated from the constructed quantities.
    residuals = {
        "household_budget": household_cash + distribution + payroll
        - price * consumption - household_cash,
        "firm_cash_budget": firm_cash - distribution - payroll
        + price * (output - investment) - firm_cash,
        "capital_transition": (1 - delta) * capital + investment - capital,
        "goods_clearing": 2 * output - 2 * consumption - 2 * investment,
        "total_money": 2 * household_cash + 2 * firm_cash - money,
        "household_money_euler": marginal_money - eta / household_cash
        - beta * marginal_money,
        "household_labor": chi / (1 - labor) - wage / (price * consumption),
        "capital_euler": 1 - beta * (1 - delta + alpha * output / capital),
        "firm_funding": firm_cash - distribution - payroll,
        "firm_labor": beta * (price * (1 - alpha) * output / labor - wage)
        - funding_multiplier * wage,
        "firm_distribution": 1 - beta - funding_multiplier,
        "stationary_owner_value": distribution / (1 - beta)
        - (firm_cash + price * capital),
    }
    for name, residual in residuals.items():
        if not isclose(residual, 0, abs_tol=1e-11):
            raise ArithmeticError(f"{name} residual: {residual}")
    if not (0 < labor < 1 and 0 < investment < output and distribution > 0):
        raise ArithmeticError("The fixture must have interior labor/investment and payouts.")

    # Execute the nominal cycle separately. There are two equal households and
    # firms: each household receives half of each firm's payment and purchases
    # half its consumption from each firm, giving these per-entity totals.
    f, h = firm_cash, household_cash
    cash_cycle = [{"phase": "opening", "firm": f, "household": h}]
    for phase, change_to_household in (
        ("owner_distributions", distribution),
        ("wages", payroll),
        ("goods_purchases", -price * consumption),
    ):
        f -= change_to_household
        h += change_to_household
        if min(f, h) < -1e-12 or not isclose(2 * (f + h), money, abs_tol=1e-12):
            raise ArithmeticError(f"Unfunded or unbalanced settlement at {phase}")
        cash_cycle.append({"phase": phase, "firm": f, "household": h})
    if not (isclose(f, firm_cash, abs_tol=1e-12)
            and isclose(h, household_cash, abs_tol=1e-12)):
        raise ArithmeticError("Cash cycle did not return to its stationary state.")

    # Check the algebraic bound at a few feasible deviations, including corners.
    # These samples check its implementation; the document proves the inequality
    # for every feasible choice at the stationary prices.
    full_payroll_labor = firm_cash / wage
    full_payroll_output = productivity * capital**alpha * full_payroll_labor ** (1 - alpha)
    alternatives = (
        ("stationary", distribution, labor, investment),
        ("inactive", 0., 0., 0.),
        ("pay_all_cash", firm_cash, 0., 0.),
        ("retain_all_cash_income", 0., labor, 0.),
        ("retain_all_output", 0., full_payroll_labor, full_payroll_output),
    )
    gaps = {}
    for name, payout, work, retained in alternatives:
        produced = productivity * capital**alpha * work ** (1 - alpha)
        opening_slack = firm_cash - payout - wage * work
        if opening_slack < -1e-12 or not 0 <= retained <= produced + 1e-12:
            raise ArithmeticError(f"Infeasible deviation: {name}")
        next_cash = opening_slack + price * (produced - retained)
        next_capital = (1 - delta) * capital + retained
        direct_gap = payout + beta * (next_cash + price * next_capital)
        direct_gap -= firm_cash + price * capital
        bound_gap = -(1 - beta) * opening_slack + beta * price * (
            produced - capital_product * capital - labor_product * work
        )
        if direct_gap > 1e-11 or not isclose(direct_gap, bound_gap, abs_tol=1e-11):
            raise ArithmeticError(f"Supporting-plane bound failed: {name}")
        gaps[name] = direct_gap

    return {
        "parameters": {"beta": beta, "delta": delta, "chi": chi, "eta": eta,
                       "alpha": alpha, "productivity": productivity, "total_money": money},
        "stationary_quantities_per_entity": {
            "capital": capital, "labor": labor, "output": output,
            "investment": investment, "consumption": consumption,
            "household_cash": household_cash, "firm_cash": firm_cash,
            "goods_price": price, "money_wage": wage,
            "owner_distribution": distribution, "payroll": payroll,
        },
        "max_absolute_equation_residual": max(abs(x) for x in residuals.values()),
        "equation_residuals": residuals,
        "cash_cycle_per_entity": cash_cycle,
        "firm_deviation_bound_gaps": gaps,
    }


if __name__ == "__main__":
    print(json.dumps({
        "scope": "Analytical stationary fixtures for the proposed monetary model",
        "limitation": "Does not solve or establish convergence of transition paths.",
        "cases": [stationary_case(.05), stationary_case(1.)],
    }, indent=2, allow_nan=False))
