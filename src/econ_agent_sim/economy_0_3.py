from __future__ import annotations

from dataclasses import dataclass, field
from math import isclose

from econ_agent_sim.economy_0_2 import (
    Economy02Config,
    ExchangeAgentConfig,
    canonical_population,
    run_economy_0_2,
)
from econ_agent_sim.ledger import Transaction
from econ_agent_sim.price_discovery import TatonnementStep

LEGACY_CANONICAL_PERIOD_COUNT = 4


def baseline_period_populations() -> tuple[tuple[ExchangeAgentConfig, ...], ...]:
    """Return the one-period Economy 0.3 baseline used by the interactive app."""

    return (canonical_population(),)


def canonical_period_populations() -> tuple[tuple[ExchangeAgentConfig, ...], ...]:
    """Return the original four-period rotating-Y schedule for reproducibility."""

    base = canonical_population()
    y_endowments = tuple(agent.y for agent in base)
    periods: list[tuple[ExchangeAgentConfig, ...]] = []

    for shift in range(LEGACY_CANONICAL_PERIOD_COUNT):
        if shift == 0:
            rotated_y = y_endowments
        else:
            rotated_y = y_endowments[-shift:] + y_endowments[:-shift]

        periods.append(
            tuple(
                ExchangeAgentConfig(
                    name=agent.name,
                    x=agent.x,
                    y=rotated_y[index],
                    alpha=agent.alpha,
                )
                for index, agent in enumerate(base)
            )
        )

    return tuple(periods)


def redistribute_y(
    population: tuple[ExchangeAgentConfig, ...],
    *,
    sender_name: str,
    receiver_name: str,
    amount: float,
) -> tuple[ExchangeAgentConfig, ...]:
    """Create a new period by moving an amount of Y between two existing agents."""

    if amount <= 0:
        raise ValueError("redistribution amount must be strictly positive")
    if sender_name == receiver_name:
        raise ValueError("sender and receiver must be different agents")

    by_name = {agent.name: agent for agent in population}
    if sender_name not in by_name:
        raise ValueError(f"unknown sender: {sender_name}")
    if receiver_name not in by_name:
        raise ValueError(f"unknown receiver: {receiver_name}")

    sender = by_name[sender_name]
    if amount > sender.y + 1e-12:
        raise ValueError(
            f"{sender_name} only has {sender.y:.6g} units of Y available"
        )

    redistributed: list[ExchangeAgentConfig] = []
    for agent in population:
        new_y = agent.y
        if agent.name == sender_name:
            new_y -= amount
        elif agent.name == receiver_name:
            new_y += amount

        redistributed.append(
            ExchangeAgentConfig(
                name=agent.name,
                x=agent.x,
                y=new_y,
                alpha=agent.alpha,
            )
        )

    return tuple(redistributed)


@dataclass(frozen=True)
class Economy03Config:
    """Inputs for repeated pure exchange with fresh exogenous endowments."""

    period_populations: tuple[tuple[ExchangeAgentConfig, ...], ...] = field(
        default_factory=baseline_period_populations
    )
    initial_price_x: float = 0.5
    adjustment_speed: float = 1.0
    tolerance: float = 1e-6
    max_iterations: int = 5000

    def __post_init__(self) -> None:
        if not self.period_populations:
            raise ValueError("Economy 0.3 requires at least one period")

        first = self.period_populations[0]
        reference_names = tuple(agent.name for agent in first)
        reference_alphas = tuple(agent.alpha for agent in first)
        reference_x = sum(agent.x for agent in first)
        reference_y = sum(agent.y for agent in first)

        for period_number, population in enumerate(self.period_populations, start=1):
            Economy02Config(
                agents=population,
                initial_price_x=self.initial_price_x,
                adjustment_speed=self.adjustment_speed,
                tolerance=self.tolerance,
                max_iterations=self.max_iterations,
            )

            names = tuple(agent.name for agent in population)
            if names != reference_names:
                raise ValueError(
                    "agent identities and ordering must remain fixed across periods"
                )

            alphas = tuple(agent.alpha for agent in population)
            if alphas != reference_alphas:
                raise ValueError("agent preferences must remain fixed across periods")

            total_x = sum(agent.x for agent in population)
            total_y = sum(agent.y for agent in population)
            if not isclose(total_x, reference_x, abs_tol=1e-12):
                raise ValueError(
                    f"aggregate X must remain fixed across periods; period "
                    f"{period_number} differs"
                )
            if not isclose(total_y, reference_y, abs_tol=1e-12):
                raise ValueError(
                    f"aggregate Y must remain fixed across periods; period "
                    f"{period_number} differs"
                )


@dataclass(frozen=True)
class Economy03PeriodResult:
    period: int
    population: tuple[ExchangeAgentConfig, ...]
    opening_stocks: dict[str, dict[str, float]]
    benchmark_price_x: float
    steps: tuple[TatonnementStep, ...]
    prices: dict[str, float]
    wealths: dict[str, float]
    desired_bundles: dict[str, dict[str, float]]
    transactions: tuple[Transaction, ...]
    flows: dict[str, dict[str, float]]
    closing_stocks: dict[str, dict[str, float]]


@dataclass(frozen=True)
class Economy03Result:
    config: Economy03Config
    periods: tuple[Economy03PeriodResult, ...]
    transactions: tuple[Transaction, ...]


def _period_transactions(
    local_transactions: tuple[Transaction, ...],
    *,
    period: int,
    first_transaction_id: int,
) -> tuple[Transaction, ...]:
    return tuple(
        Transaction(
            transaction_id=first_transaction_id + offset,
            trade_id=period,
            period=period,
            good=transaction.good,
            quantity=transaction.quantity,
            sender=transaction.sender,
            receiver=transaction.receiver,
        )
        for offset, transaction in enumerate(local_transactions)
    )


def run_economy_0_3(config: Economy03Config | None = None) -> Economy03Result:
    """Run repeated independent exchange periods with explicit period accounting."""

    scenario = config or Economy03Config()
    period_results: list[Economy03PeriodResult] = []
    all_transactions: list[Transaction] = []
    next_transaction_id = 1

    for period_number, population in enumerate(scenario.period_populations, start=1):
        local = run_economy_0_2(
            Economy02Config(
                agents=population,
                initial_price_x=scenario.initial_price_x,
                adjustment_speed=scenario.adjustment_speed,
                tolerance=scenario.tolerance,
                max_iterations=scenario.max_iterations,
            )
        )

        transactions = _period_transactions(
            local.transactions,
            period=period_number,
            first_transaction_id=next_transaction_id,
        )
        next_transaction_id += len(transactions)
        all_transactions.extend(transactions)

        period_results.append(
            Economy03PeriodResult(
                period=period_number,
                population=population,
                opening_stocks=local.opening_stocks,
                benchmark_price_x=local.benchmark_price_x,
                steps=local.steps,
                prices=local.prices,
                wealths=local.wealths,
                desired_bundles=local.desired_bundles,
                transactions=transactions,
                flows=local.flows,
                closing_stocks=local.closing_stocks,
            )
        )

    return Economy03Result(
        config=scenario,
        periods=tuple(period_results),
        transactions=tuple(all_transactions),
    )
