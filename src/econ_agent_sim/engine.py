"""Run the current monetary model once; reveal its verified prefix over time."""

from dataclasses import dataclass

from .domain import MAX_PERIODS, Settings
from .monetary_growth import Result, solve_constrained_transition


class SimulationError(ValueError):
    """A user-facing failed solve that must not replace existing results."""


@dataclass(frozen=True)
class Run:
    settings: Settings
    solution: Result

    @property
    def periods(self):
        return self.solution.periods


def simulate(settings):
    """Certify all 100 displayable periods before accepting a new run.

    Numerical continuation extends beyond this display limit. Revealing later
    periods uses this same immutable path, so navigation never revises history.
    """
    if type(settings) is not Settings:
        raise ValueError("Use the six current model settings to start a simulation.")
    solution = solve_constrained_transition(
        settings.to_parameters(), settings.initial_capital, MAX_PERIODS,
        initial_firm_cash_share=settings.initial_firm_cash_share,
    )
    if not solution.converged:
        if solution.status == "unsupported_cash_retention":
            raise SimulationError(
                "These starting conditions require firms to keep some opening money "
                "unspent. That case is not supported yet. Try a starting experiment; "
                "your existing results have been kept."
            )
        raise SimulationError(
            "A reliable path could not be verified for these settings. "
            "Try a starting experiment or a smaller change to its settings. "
            "Your existing results have been kept."
        )
    if (len(solution.periods) != MAX_PERIODS
            or solution.parameters != settings.to_parameters()
            or solution.initial_capital != settings.initial_capital
            or solution.initial_firm_cash_share != settings.initial_firm_cash_share):
        raise SimulationError("The returned path does not match this setup. Existing results were kept.")
    return Run(settings, solution)
