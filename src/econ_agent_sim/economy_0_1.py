from __future__ import annotations

from dataclasses import dataclass, field

from econ_agent_sim.economy_0 import GOODS, Economy0Config, equilibrium_prices
from econ_agent_sim.ledger import Ledger, Transaction
from econ_agent_sim.model import Agent, CobbDouglasPreferences


@dataclass(frozen=True)
class Economy01Config:
    """Inputs for Economy 0.1: pure exchange plus Walrasian tatonnement."""

    exchange: Economy0Config = field(default_factory=Economy0Config)
    initial_price_x: float = 0.5
    adjustment_speed: float = 1.0
    tolerance: float = 1e-10
    max_iterations: int = 5000

    def __post_init__(self) -> None:
        if self.initial_price_x <= 0:
            raise ValueError("initial_price_x must be strictly positive")
        if not 0.0 < self.adjustment_speed <= 1.0:
            raise ValueError("adjustment_speed must lie in (0, 1]")
        if self.tolerance <= 0:
            raise ValueError("tolerance must be strictly positive")
        if self.max_iterations < 1:
            raise ValueError("max_iterations must be at least 1")


@dataclass(frozen=True)
class TatonnementStep:
    iteration: int
    price_x: float
    supply_x: float
    demand_x: float
    excess_demand_x: float
    normalized_excess_demand_x: float
    next_price_x: float | None


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
    """Discover the relative price using discrete proportional tatonnement.

    The textbook rule is that a price rises under excess demand and falls under
    excess supply. We normalize X excess demand by total X so the adjustment
    speed is dimensionless:

        p_X(t+1) = p_X(t) * [1 + lambda * z_X(t) / X_bar]

    No benchmark/equilibrium price enters this iteration.
    """

    total_x = sum(agent.holdings["X"] for agent in agents)
    price_x = config.initial_price_x
    steps: list[TatonnementStep] = []

    for iteration in range(config.max_iterations + 1):
        prices = {"X": price_x, "Y": 1.0}
        demand_x = sum(agent.optimal_bundle(prices)["X"] for agent in agents)
        excess_demand_x = demand_x - total_x
        normalized_excess = excess_demand_x / total_x

        if abs(normalized_excess) <= config.tolerance:
            steps.append(
                TatonnementStep(
                    iteration=iteration,
                    price_x=price_x,
                    supply_x=total_x,
                    demand_x=demand_x,
                    excess_demand_x=excess_demand_x,
                    normalized_excess_demand_x=normalized_excess,
                    next_price_x=None,
                )
            )
            return tuple(steps), prices

        next_price_x = price_x * (
            1.0 + config.adjustment_speed * normalized_excess
        )
        if next_price_x <= 0:
            raise AssertionError("tatonnement produced a non-positive price")

        steps.append(
            TatonnementStep(
                iteration=iteration,
                price_x=price_x,
                supply_x=total_x,
                demand_x=demand_x,
                excess_demand_x=excess_demand_x,
                normalized_excess_demand_x=normalized_excess,
                next_price_x=next_price_x,
            )
        )
        price_x = next_price_x

    raise RuntimeError("tatonnement did not converge within max_iterations")


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
        quantity_scale = max(
            1.0,
            first.holdings[good] + second.holdings[good],
        )
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
