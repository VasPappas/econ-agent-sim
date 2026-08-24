from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from econ_agent_sim.ledger import Ledger, Transaction
from econ_agent_sim.model import Agent, CobbDouglasPreferences

GOODS = ("X", "Y")


@dataclass(frozen=True)
class Economy0Config:
    """Inputs for a two-agent, two-good pure-exchange economy."""

    alice_x: float = 1.0
    alice_y: float = 0.0
    alice_alpha: float = 0.5
    bob_x: float = 0.0
    bob_y: float = 1.0
    bob_alpha: float = 0.5

    def __post_init__(self) -> None:
        endowments = (self.alice_x, self.alice_y, self.bob_x, self.bob_y)
        if any(quantity < 0 for quantity in endowments):
            raise ValueError("endowments cannot be negative")
        if self.alice_x + self.bob_x <= 0:
            raise ValueError("the economy must contain some X")
        if self.alice_y + self.bob_y <= 0:
            raise ValueError("the economy must contain some Y")
        for alpha in (self.alice_alpha, self.bob_alpha):
            if not 0.0 < alpha < 1.0:
                raise ValueError("Cobb-Douglas alpha must lie strictly between 0 and 1")


@dataclass(frozen=True)
class Economy0Result:
    config: Economy0Config
    opening_stocks: dict[str, dict[str, float]]
    prices: dict[str, float]
    wealths: dict[str, float]
    desired_bundles: dict[str, dict[str, float]]
    transactions: tuple[Transaction, ...]
    flows: dict[str, dict[str, float]]
    closing_stocks: dict[str, dict[str, float]]


def equilibrium_prices(agents: list[Agent]) -> dict[str, float]:
    """Return the analytic Walrasian equilibrium, normalizing p_Y = 1."""

    total_x = sum(agent.holdings["X"] for agent in agents)
    alpha_x_endowment = sum(
        agent.preferences.alpha * agent.holdings["X"] for agent in agents
    )
    alpha_y_endowment = sum(
        agent.preferences.alpha * agent.holdings["Y"] for agent in agents
    )
    denominator = total_x - alpha_x_endowment
    if denominator <= 0 or alpha_y_endowment <= 0:
        raise ValueError("endowments/preferences do not imply an interior equilibrium")

    return {"X": alpha_y_endowment / denominator, "Y": 1.0}


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


def _assert_close(a: float, b: float, *, tolerance: float = 1e-10) -> None:
    if abs(a - b) > tolerance:
        raise AssertionError(f"accounting mismatch: {a} != {b}")


def _settle_two_agent_trade(
    agents: list[Agent], targets: Mapping[str, Mapping[str, float]], ledger: Ledger
) -> None:
    if len(agents) != 2:
        raise ValueError("Economy 0 is intentionally limited to exactly two agents")

    first, second = agents
    trade_id = 1
    for good in GOODS:
        first_net = targets[first.name][good] - first.holdings[good]
        second_net = targets[second.name][good] - second.holdings[good]
        _assert_close(first_net + second_net, 0.0)

        if first_net > 1e-12:
            ledger.transfer(
                trade_id=trade_id,
                period=0,
                good=good,
                quantity=first_net,
                sender=second,
                receiver=first,
            )
        elif first_net < -1e-12:
            ledger.transfer(
                trade_id=trade_id,
                period=0,
                good=good,
                quantity=-first_net,
                sender=first,
                receiver=second,
            )


def run_economy_0(config: Economy0Config | None = None) -> Economy0Result:
    """Run Economy 0 using the canonical textbook inputs unless configured."""

    scenario = config or Economy0Config()
    agents = _build_agents(scenario)
    opening = _snapshot(agents)
    prices = equilibrium_prices(agents)
    wealths = {agent.name: agent.wealth(prices) for agent in agents}
    desired = {agent.name: agent.optimal_bundle(prices) for agent in agents}

    ledger = Ledger()
    _settle_two_agent_trade(agents, desired, ledger)

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
        _assert_close(
            sum(desired[name][good] for name in desired),
            sum(opening[name][good] for name in opening),
        )

    return Economy0Result(
        config=scenario,
        opening_stocks=opening,
        prices=prices,
        wealths=wealths,
        desired_bundles=desired,
        transactions=ledger.transactions,
        flows=flows,
        closing_stocks=closing,
    )
