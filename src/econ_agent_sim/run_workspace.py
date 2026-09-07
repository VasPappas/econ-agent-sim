"""Independent runs: editable setups never mutate a calculated result."""

from dataclasses import asdict, dataclass
from functools import cached_property
from math import isfinite

from econ_agent_sim.economy_0_2 import ExchangeAgentConfig
from econ_agent_sim.economy_0_4 import (
    ASSETS,
    MONEY,
    Economy04Config,
    Economy04Result,
    ledger_flows,
)
from econ_agent_sim.numerics import balances_match


def default_agents(count=2):
    return [{"name": f"Agent {i + 1}", "x": 1.0, "y": 1.0, "alpha": .5} for i in range(count)]


def setup_config(agents, money=10.0):
    if not 2 <= len(agents) <= 20:
        raise ValueError("Choose between 2 and 20 agents.")
    if not isfinite(money) or money <= 0:
        raise ValueError("Opening money must be positive and finite.")
    for a in agents:
        if any(not isfinite(a[k]) for k in ("x", "y", "alpha")):
            raise ValueError("Use finite quantities and preferences.")
    if any(sum(a[k] for a in agents) <= 0 for k in ("x", "y")):
        raise ValueError("The economy needs a positive total of both X and Y.")
    return Economy04Config(
        period_populations=(tuple(ExchangeAgentConfig(**a) for a in agents),),
        opening_money_per_agent=money, initial_price_x=1.0, tolerance=1e-10,
    )


def _setup_changes(result, previous):
    if previous is None:
        return ["First run · no previous result to compare."]
    before = {a.name: a for a in previous.periods[0].population}
    after = {a.name: a for a in result.periods[0].population}
    changes = []
    for name, a in after.items():
        if name not in before:
            changes.append(f"{name} added · {a.x:g} X · {a.y:g} Y · {a.alpha:.0%} to X")
            continue
        b = before[name]
        for key, label in (("x", "X"), ("y", "Y"), ("alpha", "spending share on X")):
            old, new = getattr(b, key), getattr(a, key)
            if old != new:
                values = f"{old:.0%} → {new:.0%}" if key == "alpha" else f"{old:g} → {new:g}"
                changes.append(f"{name} · {label}: {values}")
    changes.extend(f"{name} removed" for name in before if name not in after)
    old, new = previous.config.opening_money_per_agent, result.config.opening_money_per_agent
    if old != new:
        changes.append(f"Opening money per agent: {old:g} → {new:g}")
    return changes or ["Same setup as the previous run."]



@dataclass(frozen=True)
class SubmittedRun:
    """One submitted outcome, shared by Results, evidence, and explanations."""

    result: Economy04Result
    previous: Economy04Result | None
    number: int
    revision: int

    def __post_init__(self):
        if any(len(r.periods) != 1 for r in (self.result, self.previous) if r is not None):
            raise ValueError("A submitted run must contain exactly one independent outcome.")

    @property
    def period(self):
        return self.result.periods[0]

    @cached_property
    def accounting_rows(self):
        p = self.period
        flows = ledger_flows(tuple(p.opening_stocks), p.transactions)
        return [
            {"agent": name, "asset": asset, "opening": opening[asset],
             "net flow": flows[name][asset], "closing": p.closing_stocks[name][asset],
             "check": opening[asset] + flows[name][asset] - p.closing_stocks[name][asset]}
            for name, opening in p.opening_stocks.items() for asset in ASSETS
        ]

    @cached_property
    def data(self):
        p, config = self.period, self.result.config
        prior = self.previous.periods[0] if self.previous else None
        totals = {
            snapshot: {asset: sum(s[asset] for s in stocks.values()) for asset in ASSETS}
            for snapshot, stocks in (("opening", p.opening_stocks), ("closing", p.closing_stocks))
        }
        return {
            "label": f"Run {self.number}",
            "run_number": self.number,
            "revision": self.revision,
            "settings": {
                "agent_count": len(p.population),
                "opening_money_per_agent": config.opening_money_per_agent,
                "initial_trial_price_x": config.initial_price_x,
                "adjustment_speed": config.adjustment_speed,
            },
            "prices": dict(p.prices),
            "previous_run": (
                {"number": self.number - 1, "prices": dict(prior.prices),
                 "agents": [asdict(a) for a in prior.population],
                 "opening_money_per_agent": self.previous.config.opening_money_per_agent}
                if prior else None
            ),
            "price_x_change_percent": (
                100 * (p.prices["X"] / prior.prices["X"] - 1) if prior else None
            ),
            "setup_changes": _setup_changes(self.result, self.previous),
            "agents": [
                {"name": a.name, "alpha": a.alpha,
                 "opening": dict(p.opening_stocks[a.name]),
                 "closing": dict(p.closing_stocks[a.name]),
                 "desired": dict(p.desired_bundles[a.name])}
                for a in p.population
            ],
            "trades": [dict(ordinal=i + 1, **asdict(t)) for i, t in enumerate(p.trades)],
            "totals": totals,
            "market_error": p.steps[-1].market_error,
            "clearing_tolerance": config.tolerance,
            "gross_money_payments": p.gross_money_payments,
            "checks": {
                "market": p.steps[-1].market_error <= config.tolerance,
                "money": balances_match(totals["opening"][MONEY], totals["closing"][MONEY]),
                "accounts": all(balances_match(row["check"], 0.0) for row in self.accounting_rows),
            },
            "run_rule": (
                "Independent submitted setups. Quantities, preferences, and agent count can all change. "
                "No balances carry forward. Ledger trade IDs restart within each run."
            ),
        }

    def context(self, trade_index=None):
        trades = self.data["trades"]
        selected = (trades[trade_index]
                    if type(trade_index) is int and 0 <= trade_index < len(trades) else None)
        return {**self.data, "selected_trade": selected}
