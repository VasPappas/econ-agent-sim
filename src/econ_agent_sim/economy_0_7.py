"""Competitive work, consumption and real-money choices with a leisure endowment."""

from dataclasses import asdict, dataclass, replace
from functools import cached_property
from math import fsum, isclose

from econ_agent_sim.economy_0_5 import MoneyAgent
from econ_agent_sim.economy_0_6 import (
    ProductionAgent,
    ProductionPeriod,
    ProductionRun,
    advance_period,
)
from econ_agent_sim.numerics import require_finite


@dataclass(frozen=True)
class WorkAgent:
    name: str
    x: float = 0.0
    money: float = 1.0
    alpha: float = .5
    productivity: float = 2.0
    leisure: float = 1 / 3

    def __post_init__(self):
        MoneyAgent(self.name, self.x, self.money, self.alpha)
        require_finite("Productivity and leisure preference", self.productivity, self.leisure)
        if self.productivity <= 0:
            raise ValueError("Productivity must be positive.")
        if not 0 < self.leisure < 1:
            raise ValueError("Leisure preference must lie strictly between 0 and 1.")


def default_work_agents(count=2):
    return [asdict(WorkAgent(f"Agent {i + 1}")) for i in range(count)]


@dataclass(frozen=True)
class WorkPeriod(ProductionPeriod):
    population: tuple[WorkAgent, ...]
    effort: dict
    leisure_time: dict
    work_checks: dict
    solution: dict


def _solve_work(population, opening):
    """Solve in s=1/p; excess goods demand is continuous and piecewise linear.

    Starting at s=0, remove workers whose unconstrained choice becomes negative.
    Each removal can only raise the root, so no removed worker re-enters and at
    most N+1 exact linear solves are needed. There is no price search grid.
    """
    working = {a.name for a in population
               if (1 - a.leisure) * a.productivity > a.leisure * opening[a.name]["X"]}
    for iteration in range(1, len(population) + 2):
        intercept = fsum(
            (1 - a.alpha) * ((1 - a.leisure) * (opening[a.name]["X"] + a.productivity)
                             if a.name in working else opening[a.name]["X"])
            for a in population
        )
        slope = fsum(
            opening[a.name]["Money"] *
            (a.alpha + (1 - a.alpha) * a.leisure if a.name in working else a.alpha)
            for a in population
        )
        require_finite("Market coefficients", intercept, slope)
        if intercept <= 0 or slope <= 0:
            raise ValueError("The economy needs positive money and resources for a finite price.")
        inverse_price = intercept / slope
        require_finite("Purchasing power of money", inverse_price)
        if inverse_price <= 0:
            raise ValueError("Starting balances are too small for a finite positive price.")
        unconstrained = {
            a.name: (1 - a.leisure) - a.leisure *
            (opening[a.name]["X"] + opening[a.name]["Money"] * inverse_price) / a.productivity
            for a in population
        }
        require_finite("Chosen work", *unconstrained.values())
        remaining = {name for name in working if unconstrained[name] > 0}
        if remaining == working:
            effort = {a.name: max(0.0, unconstrained[a.name]) for a in population}
            price = 1 / inverse_price
            require_finite("Price", price)
            if price <= 0:
                raise ValueError("Price must be positive.")
            return price, effort, iteration
        working = remaining
    raise ValueError("Work and the market price could not be reconciled.")


def advance_work_period(population: tuple[WorkAgent, ...],
                        previous: WorkPeriod | None = None) -> WorkPeriod:
    """Optimize work and clear the market jointly, then consume X and carry cash."""
    if not population or len({a.name for a in population}) != len(population):
        raise ValueError("Provide agents with unique names.")
    if previous is not None and population != previous.population:
        raise ValueError("Restart the economy before changing agent settings.")
    opening = ({name: dict(stocks) for name, stocks in previous.closing_stocks.items()}
               if previous is not None else
               {a.name: {"X": a.x, "Money": a.money} for a in population})
    price, effort, iterations = _solve_work(population, opening)
    produced = {a.name: a.productivity * effort[a.name] for a in population}
    # Reuse the independently checked transfer ledger and consumption accounting.
    # This market price must agree with the price used when choosing work below.
    period = advance_period(tuple(
        ProductionAgent(a.name, opening[a.name]["X"], opening[a.name]["Money"],
                        a.alpha, produced[a.name]) for a in population
    ))
    number = previous.number + 1 if previous else 1
    market = replace(period.market,
                     trades=tuple(replace(t, period=number) for t in period.market.trades),
                     transactions=tuple(replace(t, period=number) for t in period.market.transactions))
    leisure_time = {name: 1 - value for name, value in effort.items()}
    marginal_checks = []
    for a in population:
        resource = (opening[a.name]["X"] + opening[a.name]["Money"] / market.prices["X"]
                    + produced[a.name])
        benefit = (1 - a.leisure) * a.productivity / resource
        cost = a.leisure / leisure_time[a.name]
        require_finite("Marginal work values", resource, benefit, cost)
        marginal_checks.append(
            isclose(benefit, cost, rel_tol=1e-8, abs_tol=1e-10) if effort[a.name] > 0
            else benefit <= cost + 1e-10 * max(1.0, cost)
        )
    work_checks = {
        "effort_bounds": all(0 <= value < 1 for value in effort.values()),
        "time_budget": all(isclose(effort[name] + leisure_time[name], 1.0)
                           for name in effort),
        "optimal_work": all(marginal_checks),
        "joint_price": isclose(price, market.prices["X"], rel_tol=1e-9, abs_tol=0.0),
    }
    if not all(work_checks.values()):
        raise ValueError("Work choices and the market did not reconcile; no period was completed.")
    checks = {**period.checks, "continuity": previous is None or opening == previous.closing_stocks}
    return WorkPeriod(number, population, opening, produced, market, period.consumed,
                      period.closing_stocks, checks, effort, leisure_time, work_checks,
                      {"method": "piecewise_linear", "active_set_passes": iterations,
                       "joint_price": price,
                       "working_agents": sum(value > 0 for value in effort.values()),
                       "resting_agents": sum(value == 0 for value in effort.values())})


@dataclass(frozen=True)
class WorkRun(ProductionRun):
    current: WorkPeriod
    previous: WorkPeriod | None

    @cached_property
    def data(self):
        current = self.current
        data = dict(ProductionRun(current, self.previous, self.revision).data)
        data.update({
            "model": "work_leisure",
            "effort": current.effort,
            "leisure_time": current.leisure_time,
            "work_checks": current.work_checks,
            "solution": current.solution,
            "setup_changes": (["Money carried forward; work and price chosen together; all post-trade X consumed."]
                              if self.previous else ["First period · initial balances and chosen production."]),
            "run_rule": "Linked periods. Agents choose work, trade, then consume all X. Money carries forward; no borrowing or money creation.",
        })
        return data
