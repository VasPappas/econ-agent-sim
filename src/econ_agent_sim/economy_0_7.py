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


def work_report(periods: tuple["WorkPeriod", ...], cumulative=False):
    """Return stock-and-flow reports through the selected period.

    Stocks use the first opening and final closing balances. Flows are summed;
    work and leisure are both summed and averaged. Prices are deliberately not
    aggregated across periods.
    """
    if not periods:
        raise ValueError("A report needs at least one completed period.")
    selected = periods if cumulative else periods[-1:]
    first, last = selected[0], selected[-1]
    population = last.population
    names = tuple(agent.name for agent in population)
    if any(period.population != population for period in selected):
        raise ValueError("A cumulative report needs one unchanged population.")

    def flows(name):
        trades = tuple(trade for period in selected for trade in period.market.trades)
        sold_x = fsum(t.quantity for t in trades if t.seller == name)
        bought_x = fsum(t.quantity for t in trades if t.buyer == name)
        sales = fsum(t.payment for t in trades if t.seller == name)
        purchases = fsum(t.payment for t in trades if t.buyer == name)
        return sold_x, bought_x, sales, purchases

    agents = []
    for agent in population:
        sold_x, bought_x, sales, purchases = flows(agent.name)
        total_work = fsum(period.effort[agent.name] for period in selected)
        agents.append({
            "name": agent.name,
            "opening": dict(first.opening_stocks[agent.name]),
            "closing": dict(last.closing_stocks[agent.name]),
            "produced": fsum(period.produced[agent.name] for period in selected),
            "consumed": fsum(period.consumed[agent.name] for period in selected),
            "sold_x": sold_x,
            "bought_x": bought_x,
            "sales_received": sales,
            "purchases_paid": purchases,
            "net_trade_cash": sales - purchases,
            "transaction_count": sum(
                t.seller == agent.name or t.buyer == agent.name
                for period in selected for t in period.market.trades
            ),
            "total_work": total_work,
            "average_work": total_work / len(selected),
            "average_leisure": 1 - total_work / len(selected),
            "parameters": {
                "alpha": agent.alpha,
                "leisure": agent.leisure,
                "productivity": agent.productivity,
                "weights": {
                    "consumption": (1 - agent.leisure) * agent.alpha,
                    "money": (1 - agent.leisure) * (1 - agent.alpha),
                    "leisure": agent.leisure,
                },
            },
        })
    opening = {asset: fsum(first.opening_stocks[name][asset] for name in names)
               for asset in ("X", "Money")}
    closing = {asset: fsum(last.closing_stocks[name][asset] for name in names)
               for asset in ("X", "Money")}
    gross_payments = fsum(
        trade.payment for period in selected for trade in period.market.trades
    )
    total_work = fsum(agent["total_work"] for agent in agents)
    goods_identity = isclose(opening["X"] + fsum(a["produced"] for a in agents),
                             closing["X"] + fsum(a["consumed"] for a in agents),
                             rel_tol=1e-9, abs_tol=1e-10)
    money_identity = isclose(opening["Money"], closing["Money"],
                             rel_tol=1e-9, abs_tol=1e-10)
    rows = []
    for period in selected:
        for agent in population:
            name = agent.name
            for asset in ("X", "Money"):
                received = fsum(t.quantity for t in period.market.transactions
                                if t.receiver == name and t.asset == asset)
                sent = fsum(t.quantity for t in period.market.transactions
                            if t.sender == name and t.asset == asset)
                rows.append({
                    "period": period.number, "agent": name, "asset": asset,
                    "opening": period.opening_stocks[name][asset],
                    "produced": period.produced[name] if asset == "X" else 0,
                    "received": received, "sent": sent,
                    "consumed": period.consumed[name] if asset == "X" else 0,
                    "closing": period.closing_stocks[name][asset],
                    "work_fraction": period.effort[name],
                    "leisure_fraction": period.leisure_time[name],
                    "productivity": agent.productivity,
                })
    scope = "cumulative" if cumulative else "period"
    return {
        "scope": scope,
        "label": (f"Periods {first.number}–{last.number}" if cumulative and len(selected) > 1
                  else f"Period {last.number}"),
        "period_count": len(selected),
        "through_period": last.number,
        "opening": opening,
        "closing": closing,
        "produced": fsum(agent["produced"] for agent in agents),
        "consumed": fsum(agent["consumed"] for agent in agents),
        "gross_x_exchanged": fsum(
            trade.quantity for period in selected for trade in period.market.trades
        ),
        "gross_money_exchanged": gross_payments,
        "net_trade_cash": 0.0,
        "total_work": total_work,
        "average_work": total_work / (len(selected) * len(population)),
        "average_leisure": 1 - total_work / (len(selected) * len(population)),
        "checks": {
            "goods_identity": goods_identity,
            "money_identity": money_identity,
            "periods": all(all(period.checks.values()) for period in selected),
            "work": all(all(period.work_checks.values()) for period in selected),
        },
        "agents": agents,
        "trades": [dict(asdict(trade), ordinal=i + 1)
                   for period in selected for i, trade in enumerate(period.market.trades)],
        "rows": rows,
    }


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
