"""Repeated production, trade and consumption with a fixed stock of money."""

from dataclasses import asdict, dataclass, replace
from functools import cached_property
from math import fsum

from econ_agent_sim.economy_0_5 import (
    ASSETS,
    MoneyAgent,
    MoneyResult,
    MoneyRun,
    matches,
    run_money_economy,
)
from econ_agent_sim.numerics import require_finite


@dataclass(frozen=True)
class ProductionAgent:
    name: str
    x: float = 0.0
    money: float = 1.0
    alpha: float = .5
    production: float = 1.0

    def __post_init__(self):
        MoneyAgent(self.name, self.x, self.money, self.alpha)
        require_finite("Production", self.production)
        if self.production < 0:
            raise ValueError("Production must be non-negative.")


def default_production_agents(count=2):
    return [asdict(ProductionAgent(f"Agent {i + 1}")) for i in range(count)]


@dataclass(frozen=True)
class ProductionPeriod:
    number: int
    population: tuple[ProductionAgent, ...]
    opening_stocks: dict
    produced: dict
    market: MoneyResult
    consumed: dict
    closing_stocks: dict
    checks: dict


def advance_period(population: tuple[ProductionAgent, ...],
                   previous: ProductionPeriod | None = None) -> ProductionPeriod:
    """Advance unchanged specifications; only closing balances carry forward."""
    if not population or len({a.name for a in population}) != len(population):
        raise ValueError("Provide agents with unique names.")
    if previous is not None and population != previous.population:
        raise ValueError("Restart the economy before changing agent settings.")
    opening = ({name: dict(stocks) for name, stocks in previous.closing_stocks.items()}
               if previous is not None else
               {a.name: {"X": a.x, "Money": a.money} for a in population})
    produced = {a.name: a.production for a in population}
    market_population = tuple(
        MoneyAgent(a.name, opening[a.name]["X"] + a.production,
                   opening[a.name]["Money"], a.alpha)
        for a in population
    )
    if fsum(a.x for a in market_population) <= 0:
        raise ValueError("There is no X to consume this period. Restart with positive production or initial X.")
    number = 1 if previous is None else previous.number + 1
    market = run_money_economy(market_population)
    market = replace(market,
                     trades=tuple(replace(t, period=number) for t in market.trades),
                     transactions=tuple(replace(t, period=number) for t in market.transactions))
    consumed = {a.name: market.closing_stocks[a.name]["X"] for a in population}
    closing = {a.name: {"X": 0.0, "Money": market.closing_stocks[a.name]["Money"]}
               for a in population}
    # Reconstruct period flows from the actual transfer ledger, not target bundles.
    flows = {a.name: {asset: {"received": [], "sent": []} for asset in ASSETS}
             for a in population}
    for transfer in market.transactions:
        flows[transfer.sender][transfer.asset]["sent"].append(transfer.quantity)
        flows[transfer.receiver][transfer.asset]["received"].append(transfer.quantity)
    # Compare positive sources and uses so the relative tolerance follows the
    # scale of the activity, rather than testing cancellation dust against zero.
    accounts = all(
        matches(fsum([opening[a.name][asset], produced[a.name] if asset == "X" else 0.0,
                      *flows[a.name][asset]["received"]]),
                fsum([closing[a.name][asset], consumed[a.name] if asset == "X" else 0.0,
                      *flows[a.name][asset]["sent"]]))
        for a in population for asset in ASSETS
    )
    total_open = {asset: fsum(s[asset] for s in opening.values()) for asset in ASSETS}
    total_close = {asset: fsum(s[asset] for s in closing.values()) for asset in ASSETS}
    checks = {
        "goods": matches(total_open["X"] + fsum(produced.values()),
                         fsum(consumed.values()) + total_close["X"]),
        "money": matches(total_open["Money"], total_close["Money"]),
        "accounts": accounts,
        "no_borrowing": all(s[asset] >= 0 for s in closing.values() for asset in ASSETS),
        "consumption": all(matches(consumed[a.name], market.closing_stocks[a.name]["X"])
                           and closing[a.name]["X"] == 0 for a in population),
        "continuity": previous is None or opening == previous.closing_stocks,
    }
    if not all(checks.values()):
        raise ValueError("Period accounting did not reconcile; no period was completed.")
    return ProductionPeriod(number,
                            population, opening, produced, market, consumed, closing, checks)


@dataclass(frozen=True)
class ProductionRun:
    current: ProductionPeriod
    previous: ProductionPeriod | None
    revision: int

    @property
    def period(self):
        return self.current.market

    @cached_property
    def data(self):
        current, previous = self.current, self.previous
        data = dict(MoneyRun(current.market, previous.market if previous else None,
                             current.number, self.revision).data)
        data.update({
            "model": "production_consumption", "label": f"Period {current.number}",
            "settings": {"agent_count": len(current.population),
                         "agents": [asdict(a) for a in current.population]},
            "setup_changes": (["Money carried forward; fixed production added; all post-trade X consumed."]
                              if previous else ["First period · initial balances plus this period's production."]),
            "period_opening": current.opening_stocks,
            "produced": current.produced,
            "consumed": current.consumed,
            "period_closing": current.closing_stocks,
            "period_totals": {
                "opening": {asset: fsum(s[asset] for s in current.opening_stocks.values()) for asset in ASSETS},
                "produced": {"X": fsum(current.produced.values()), "Money": 0.0},
                "consumed": {"X": fsum(current.consumed.values()), "Money": 0.0},
                "closing": {asset: fsum(s[asset] for s in current.closing_stocks.values()) for asset in ASSETS},
            },
            "period_checks": current.checks,
            "run_rule": "Linked periods. Fixed production, trade, then consumption of all X. Money carries forward; no borrowing or money creation.",
        })
        return data

    def context(self, trade_index=None):
        trades = self.data["trades"]
        selected = trades[trade_index] if type(trade_index) is int and 0 <= trade_index < len(trades) else None
        return {**self.data, "selected_trade": selected}
