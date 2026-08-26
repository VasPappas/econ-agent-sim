from __future__ import annotations

from dataclasses import dataclass, field

from econ_agent_sim.economy_0 import GOODS, Economy0Config, equilibrium_prices
from econ_agent_sim.ledger import Ledger, Transaction
from econ_agent_sim.model import Agent, CobbDouglasPreferences
from econ_agent_sim.price_discovery import TatonnementSettings, TatonnementStep
from econ_agent_sim.price_discovery import (
    discover_price as discover_tatonnement_price,
)


@dataclass(frozen=True)
class Economy01Config:
    """Inputs for Economy 0.1: pure exchange plus Walrasian tatonnement."""

    exchange: Economy0Config = field(default_factory=Economy0Config)
    initial_price_x: float = 0.5
    adjustment_speed: float = 1.0
    tolerance: float = 1e-10
    max_iterations: int = 5000

    def __post_init__(self) -> None:
        TatonnementSettings(
            initial_price_x=self.initial_price_x,
            adjustment_speed=self.adjustment_speed,
            tolerance=self.tolerance,
            max_iterations=self.max_iterations,
        )


@dataclass(frozen=True)
class Economy01Result:
    config: Economy01Config
    opening_stocks: dict[str, dict[str, float]]
    benchmark_price_x: float
    steps: tuple[TatonnementStep, ...]
    prices: dict[str, float]
    wealths: dict[str, float]
    desired_bundles: dict[str, dict[str, float]]
    transactions: tuple[Transaction, ...]
    flows: dict[str, dict[str, float]]
    closing_stocks: dict[str, dict[str, float]]


def _build_agents(config: Economy0Config) -> list[Agent]:
    return [
        Agent(
            "Alice",
            CobbDouglasPreferences(alpha=config.alice_alpha),
            {"X": config.alice_x, "Y": config.alice_y},
        ),
        Agent(
            "Bob",
            CobbDouglasPreferences(alpha=config.bob_alpha),
            {"X": config.bob_x, "Y": config.bob_y},
        ),
    ]


def _snapshot(agents: list[Agent]) -> dict[str, dict[str, float]]:
    return {agent.name: dict(agent.snapshot()) for agent in agents}


def _assert_close(a: float, b: float, *, tolerance: float = 1e-8) -> None:
    if abs(a - b) > tolerance:
        raise AssertionError(f"accounting mismatch: {a} != {b}")


def discover_price(
    agents: list[Agent], config: Economy01Config
) -> tuple[tuple[TatonnementStep, ...], dict[str, float]]:
    """Preserve the Economy 0.1 API while using the shared price-discovery core."""

    settings = TatonnementSettings(
        initial_price_x=config.initial_price_x,
        adjustment_speed=config.adjustment_speed,
        tolerance=config.tolerance,
        max_iterations=config.max_iterations,
    )
    return discover_tatonnement_price(agents, settings)


def _settle_trade(
    agents: list[Agent],
    desired: dict[str, dict[str, float]],
    ledger: Ledger,
    *,
    tolerance: float,
) -> None:
    first, second = agents
    for good in GOODS:
        first_net = desired[first.name][good] - first.holdings[good]
        second_net = desired[second.name][good] - second.holdings[good]
        quantity_scale = max(1.0, first.holdings[good] + second.holdings[good])
        _assert_close(
            first_net + second_net,
            0.0,
            tolerance=tolerance * quantity_scale * 2.0,
        )

        if first_net > tolerance:
            ledger.transfer(
                trade_id=1,
                period=0,
                good=good,
                quantity=first_net,
                sender=second,
                receiver=first,
            )
        elif first_net < -tolerance:
            ledger.transfer(
                trade_id=1,
                period=0,
                good=good,
                quantity=-first_net,
                sender=first,
                receiver=second,
            )


def run_economy_0_1(config: Economy01Config | None = None) -> Economy01Result:
    """Run Economy 0.1 and settle only after tatonnement converges."""

    scenario = config or Economy01Config()
    agents = _build_agents(scenario.exchange)
    opening = _snapshot(agents)

    # This benchmark is recorded for validation only. discover_price() never sees it.
    benchmark_price_x = equilibrium_prices(agents)["X"]
    steps, prices = discover_price(agents, scenario)

    wealths = {agent.name: agent.wealth(prices) for agent in agents}
    desired = {agent.name: agent.optimal_bundle(prices) for agent in agents}

    ledger = Ledger()
    _settle_trade(
        agents,
        desired,
        ledger,
        tolerance=max(scenario.tolerance, 1e-10),
    )

    flows = {agent.name: ledger.net_flows(agent.name, GOODS) for agent in agents}
    closing = _snapshot(agents)

    for agent in agents:
        for good in GOODS:
            _assert_close(
                opening[agent.name][good] + flows[agent.name][good],
                closing[agent.name][good],
            )

    for good in GOODS:
        _assert_close(
            sum(opening[name][good] for name in opening),
            sum(closing[name][good] for name in closing),
        )
        _assert_close(sum(flows[name][good] for name in flows), 0.0)

    return Economy01Result(
        config=scenario,
        opening_stocks=opening,
        benchmark_price_x=benchmark_price_x,
        steps=steps,
        prices=prices,
        wealths=wealths,
        desired_bundles=desired,
        transactions=ledger.transactions,
        flows=flows,
        closing_stocks=closing,
    )
