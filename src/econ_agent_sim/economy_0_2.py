from __future__ import annotations

from dataclasses import dataclass, field

from econ_agent_sim.economy_0 import GOODS, equilibrium_prices
from econ_agent_sim.ledger import Ledger, Transaction
from econ_agent_sim.model import Agent, CobbDouglasPreferences
from econ_agent_sim.price_discovery import (
    TatonnementSettings,
    TatonnementStep,
    discover_price,
)


@dataclass(frozen=True)
class ExchangeAgentConfig:
    """Immutable description of one pure-exchange agent."""

    name: str
    x: float
    y: float
    alpha: float

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("agent name cannot be empty")
        if self.x < 0 or self.y < 0:
            raise ValueError("agent endowments cannot be negative")
        if not 0.0 < self.alpha < 1.0:
            raise ValueError("Cobb-Douglas alpha must lie strictly between 0 and 1")


def canonical_population() -> tuple[ExchangeAgentConfig, ...]:
    """Return the deterministic ten-agent Economy 0.2 benchmark population."""

    return (
        ExchangeAgentConfig("Agent 1", 1.8, 0.2, 0.20),
        ExchangeAgentConfig("Agent 2", 0.2, 1.8, 0.80),
        ExchangeAgentConfig("Agent 3", 1.5, 0.5, 0.30),
        ExchangeAgentConfig("Agent 4", 0.5, 1.5, 0.70),
        ExchangeAgentConfig("Agent 5", 1.2, 0.8, 0.40),
        ExchangeAgentConfig("Agent 6", 0.8, 1.2, 0.60),
        ExchangeAgentConfig("Agent 7", 1.7, 0.3, 0.35),
        ExchangeAgentConfig("Agent 8", 0.3, 1.7, 0.65),
        ExchangeAgentConfig("Agent 9", 1.4, 0.6, 0.45),
        ExchangeAgentConfig("Agent 10", 0.6, 1.4, 0.55),
    )


@dataclass(frozen=True)
class Economy02Config:
    """Inputs for the many-agent pure-exchange economy."""

    agents: tuple[ExchangeAgentConfig, ...] = field(default_factory=canonical_population)
    initial_price_x: float = 0.5
    adjustment_speed: float = 1.0
    tolerance: float = 1e-10
    max_iterations: int = 5000

    def __post_init__(self) -> None:
        if not self.agents:
            raise ValueError("Economy 0.2 requires at least one agent")

        names = [agent.name for agent in self.agents]
        if len(names) != len(set(names)):
            raise ValueError("agent names must be unique")

        if sum(agent.x for agent in self.agents) <= 0:
            raise ValueError("the economy must contain some X")
        if sum(agent.y for agent in self.agents) <= 0:
            raise ValueError("the economy must contain some Y")

        TatonnementSettings(
            initial_price_x=self.initial_price_x,
            adjustment_speed=self.adjustment_speed,
            tolerance=self.tolerance,
            max_iterations=self.max_iterations,
        )


@dataclass
class _SettlementPosition:
    agent: Agent
    remaining: float


@dataclass(frozen=True)
class Economy02Result:
    config: Economy02Config
    opening_stocks: dict[str, dict[str, float]]
    benchmark_price_x: float
    steps: tuple[TatonnementStep, ...]
    prices: dict[str, float]
    wealths: dict[str, float]
    desired_bundles: dict[str, dict[str, float]]
    transactions: tuple[Transaction, ...]
    flows: dict[str, dict[str, float]]
    closing_stocks: dict[str, dict[str, float]]


def _build_agents(config: Economy02Config) -> list[Agent]:
    return [
        Agent(
            spec.name,
            CobbDouglasPreferences(alpha=spec.alpha),
            {"X": spec.x, "Y": spec.y},
        )
        for spec in config.agents
    ]


def _snapshot(agents: list[Agent]) -> dict[str, dict[str, float]]:
    return {agent.name: dict(agent.snapshot()) for agent in agents}


def _assert_close(a: float, b: float, *, tolerance: float = 1e-8) -> None:
    if abs(a - b) > tolerance:
        raise AssertionError(f"accounting mismatch: {a} != {b}")


def _settle_many_agent_trade(
    agents: list[Agent],
    desired: dict[str, dict[str, float]],
    ledger: Ledger,
    *,
    tolerance: float,
) -> None:
    """Match economically meaningful net sellers to buyers in population order."""

    for good in GOODS:
        total_supply = sum(agent.holdings[good] for agent in agents)
        scale = max(1.0, total_supply)
        settlement_epsilon = tolerance * scale * 2.0

        buyers: list[_SettlementPosition] = []
        sellers: list[_SettlementPosition] = []
        total_net = 0.0

        for agent in agents:
            net = desired[agent.name][good] - agent.holdings[good]
            total_net += net
            if net > settlement_epsilon:
                buyers.append(_SettlementPosition(agent, net))
            elif net < -settlement_epsilon:
                sellers.append(_SettlementPosition(agent, -net))

        _assert_close(total_net, 0.0, tolerance=settlement_epsilon)

        buyer_index = 0
        seller_index = 0
        while buyer_index < len(buyers) and seller_index < len(sellers):
            buyer = buyers[buyer_index]
            seller = sellers[seller_index]
            quantity = min(buyer.remaining, seller.remaining)

            ledger.transfer(
                trade_id=1,
                period=0,
                good=good,
                quantity=quantity,
                sender=seller.agent,
                receiver=buyer.agent,
            )

            buyer.remaining -= quantity
            seller.remaining -= quantity

            if buyer.remaining <= settlement_epsilon:
                buyer_index += 1
            if seller.remaining <= settlement_epsilon:
                seller_index += 1

        unmatched_buy = sum(item.remaining for item in buyers[buyer_index:])
        unmatched_sell = sum(item.remaining for item in sellers[seller_index:])
        if unmatched_buy > settlement_epsilon:
            raise AssertionError("unmatched demand remains after settlement")
        if unmatched_sell > settlement_epsilon:
            raise AssertionError("unmatched supply remains after settlement")


def run_economy_0_2(config: Economy02Config | None = None) -> Economy02Result:
    """Run many-agent price discovery and settle the converged allocation."""

    scenario = config or Economy02Config()
    agents = _build_agents(scenario)
    opening = _snapshot(agents)

    benchmark_price_x = equilibrium_prices(agents)["X"]
    settings = TatonnementSettings(
        initial_price_x=scenario.initial_price_x,
        adjustment_speed=scenario.adjustment_speed,
        tolerance=scenario.tolerance,
        max_iterations=scenario.max_iterations,
    )
    steps, prices = discover_price(agents, settings)

    wealths = {agent.name: agent.wealth(prices) for agent in agents}
    desired = {agent.name: agent.optimal_bundle(prices) for agent in agents}

    ledger = Ledger()
    settlement_tolerance = max(scenario.tolerance, 1e-10)
    _settle_many_agent_trade(
        agents,
        desired,
        ledger,
        tolerance=settlement_tolerance,
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

    return Economy02Result(
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
