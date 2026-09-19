"""Reproduce accepted and unsupported monetary reference cases; no app changes."""

import json
from dataclasses import asdict

from econ_agent_sim.monetary_growth import (
    Parameters,
    settle_period,
    solve_transition,
    steady_state,
)


def compare(name, parameters, initial_capital, **controls):
    result = solve_transition(parameters, initial_capital, 40, **controls)
    report = asdict(result)
    report.pop("periods")
    report["case"] = name
    report["max_equation_residual"] = result.max_equation_residual
    if result.converged:
        report["first_period"] = asdict(result.periods[0])
        report["last_displayed_period"] = asdict(result.periods[-1])
        report["first_settlement"] = [asdict(x) for x in settle_period(result.periods[0])]
    return report


if __name__ == "__main__":
    parameters = Parameters()
    stationary = steady_state(parameters)
    print(json.dumps({
        "scope": "Isolated symmetric monetary reference; positive distributions and investment",
        "limitation": "Unsupported candidates are not evidence of equilibrium nonexistence.",
        "cases": [
            compare("stationary", parameters, stationary.capital),
            compare("capital_below_stationary", parameters, 1.),
            compare("capital_above_stationary", parameters, 10.),
            compare("greater_money_preference", Parameters(money_weight=1.), 1.),
            compare("insufficient_initial_firm_cash", parameters, stationary.capital,
                    initial_firm_cash_share=.05),
            compare("later_distribution_boundary", parameters, .5,
                    initial_firm_cash_share=.95),
            compare("irreversible_investment_boundary", parameters, 20.),
            compare("insufficient_numerical_horizon", parameters, 1., max_horizon=64),
        ],
    }, indent=2, allow_nan=False))
