from __future__ import annotations

from dataclasses import dataclass, field

from econ_agent_sim.economy_0_2 import (
    Economy02Config,
    ExchangeAgentConfig,
    run_economy_0_2,
)
from econ_agent_sim.economy_0_3 import (
    Economy03Config,
    baseline_period_populations,
)
from econ_agent_sim.price_discovery import TatonnementStep

GOODS = ("X", "Y")
MONEY = "Money"
ASSETS = (*GOODS, MONEY)


@dataclass(frozen=True)
class MonetaryTransaction:
    """One append-only asset transfer in the monetary settlement ledger."""

    transaction_id: int
    trade_id: int
    period: int
    asset: str
    quantity: float
    sender: str
    receiver: str


@dataclass(frozen=True)
class MonetaryTrade:
    """One goods transfer paired with the money payment that settles it."""

    trade_id: int
    period: int
    good: str
    quantity: float
    unit_price: float
    seller: str
    buyer: str
    payment: float


@dataclass(frozen=True)
class Economy04Config:
    """Inputs for repeated exchange settled through explicit money payments."""

    period_populations: tuple[tuple[ExchangeAgentConfig, ...], ...] = field(
        default_factory=baseline_period_populations
    )
    opening_money_per_agent: float = 10.0
    initial_price_x: float = 0.5
    adjustment_speed: float = 1.0
    tolerance: float = 1e-6
    max_iterations: int = 5000

    def __post_init__(self) -> None:
        if self.opening_money_per_agent <= 0:
            raise ValueError("opening money per agent must be strictly positive")

        Economy03Config(
            period_populations=self.period_populations,
            initial_price_x=self.initial_price_x,
            adjustment_speed=self.adjustment_speed,
            tolerance=self.tolerance,
            max_iterations=self.max_iterations,
        )


@dataclass(frozen=True)
class Economy04PeriodResult:
    period: int
    population: tuple[ExchangeAgentConfig, ...]
    opening_stocks: dict[str, dict[str, float]]
    benchmark_price_x: float
    steps: tuple[TatonnementStep, ...]
    prices: dict[str, float]
    wealths: dict[str, float]
    desired_bundles: dict[str, dict[str, float]]
    trades: tuple[MonetaryTrade, ...]
    transactions: tuple[MonetaryTransaction, ...]
    flows: dict[str, dict[str, float]]
    closing_stocks: dict[str, dict[str, float]]
    gross_money_payments: float


@dataclass(frozen=True)
class Economy04Result:
    config: Economy04Config
    periods: tuple[Economy04PeriodResult, ...]
    trades: tuple[MonetaryTrade, ...]
    transactions: tuple[MonetaryTransaction, ...]


def _assert_close(a: float, b: float, *, tolerance: float = 1e-8) -> None:
    if abs(a - b) > tolerance:
        raise AssertionError(f"accounting mismatch: {a} != {b}")


def _opening_stocks(
    local_opening: dict[str, dict[str, float]],
    *,
    opening_money_per_agent: float,
) -> dict[str, dict[str, float]]:
    return {
        name: {
            "X": stocks["X"],
            "Y": stocks["Y"],
            MONEY: opening_money_per_agent,
        }
        for name, stocks in local_opening.items()
    }


def _monetize_transactions(
    *,
    period: int,
    local_transactions,
    prices: dict[str, float],
    first_trade_id: int,
    first_transaction_id: int,
) -> tuple[
    tuple[MonetaryTrade, ...],
    tuple[MonetaryTransaction, ...],
]:
    trades: list[MonetaryTrade] = []
    transactions: list[MonetaryTransaction] = []

    next_trade_id = first_trade_id
    next_transaction_id = first_transaction_id

    for local_transaction in local_transactions:
        unit_price = prices[local_transaction.good]
        payment = local_transaction.quantity * unit_price
        trade = MonetaryTrade(
            trade_id=next_trade_id,
            period=period,
            good=local_transaction.good,
            quantity=local_transaction.quantity,
            unit_price=unit_price,
            seller=local_transaction.sender,
            buyer=local_transaction.receiver,
            payment=payment,
        )
        trades.append(trade)

        transactions.extend(
            (
                MonetaryTransaction(
                    transaction_id=next_transaction_id,
                    trade_id=next_trade_id,
                    period=period,
                    asset=local_transaction.good,
                    quantity=local_transaction.quantity,
                    sender=local_transaction.sender,
                    receiver=local_transaction.receiver,
                ),
                MonetaryTransaction(
                    transaction_id=next_transaction_id + 1,
                    trade_id=next_trade_id,
                    period=period,
                    asset=MONEY,
                    quantity=payment,
                    sender=local_transaction.receiver,
                    receiver=local_transaction.sender,
                ),
            )
        )

        next_trade_id += 1
        next_transaction_id += 2

    return tuple(trades), tuple(transactions)


def _flows_from_transactions(
    names: tuple[str, ...],
    transactions: tuple[MonetaryTransaction, ...],
) -> dict[str, dict[str, float]]:
    flows = {name: {asset: 0.0 for asset in ASSETS} for name in names}
    for transaction in transactions:
        flows[transaction.sender][transaction.asset] -= transaction.quantity
        flows[transaction.receiver][transaction.asset] += transaction.quantity
    return flows


def _closing_stocks(
    opening: dict[str, dict[str, float]],
    flows: dict[str, dict[str, float]],
) -> dict[str, dict[str, float]]:
    return {
        name: {
            asset: opening[name][asset] + flows[name][asset]
            for asset in ASSETS
        }
        for name in opening
    }


def _check_accounting(
    opening: dict[str, dict[str, float]],
    flows: dict[str, dict[str, float]],
    closing: dict[str, dict[str, float]],
) -> None:
    for name in opening:
        for asset in ASSETS:
            _assert_close(
                opening[name][asset] + flows[name][asset],
                closing[name][asset],
            )

    for asset in ASSETS:
        _assert_close(
            sum(opening[name][asset] for name in opening),
            sum(closing[name][asset] for name in closing),
        )
        _assert_close(sum(flows[name][asset] for name in flows), 0.0)


def run_economy_0_4(config: Economy04Config | None = None) -> Economy04Result:
    """Run Economy 0.3 markets and settle every goods transfer through money."""

    scenario = config or Economy04Config()
    period_results: list[Economy04PeriodResult] = []
    all_trades: list[MonetaryTrade] = []
    all_transactions: list[MonetaryTransaction] = []
    next_trade_id = 1
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

        opening = _opening_stocks(
            local.opening_stocks,
            opening_money_per_agent=scenario.opening_money_per_agent,
        )
        trades, transactions = _monetize_transactions(
            period=period_number,
            local_transactions=local.transactions,
            prices=local.prices,
            first_trade_id=next_trade_id,
            first_transaction_id=next_transaction_id,
        )
        names = tuple(opening)
        flows = _flows_from_transactions(names, transactions)
        closing = _closing_stocks(opening, flows)

        for name in names:
            for good in GOODS:
                _assert_close(closing[name][good], local.closing_stocks[name][good])
                _assert_close(flows[name][good], local.flows[name][good])

        _check_accounting(opening, flows, closing)

        gross_money_payments = sum(trade.payment for trade in trades)
        period_results.append(
            Economy04PeriodResult(
                period=period_number,
                population=population,
                opening_stocks=opening,
                benchmark_price_x=local.benchmark_price_x,
                steps=local.steps,
                prices=local.prices,
                wealths=local.wealths,
                desired_bundles=local.desired_bundles,
                trades=trades,
                transactions=transactions,
                flows=flows,
                closing_stocks=closing,
                gross_money_payments=gross_money_payments,
            )
        )
        all_trades.extend(trades)
        all_transactions.extend(transactions)
        next_trade_id += len(trades)
        next_transaction_id += len(transactions)

    return Economy04Result(
        config=scenario,
        periods=tuple(period_results),
        trades=tuple(all_trades),
        transactions=tuple(all_transactions),
    )
