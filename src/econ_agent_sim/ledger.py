from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from econ_agent_sim.model import Agent


@dataclass(frozen=True)
class Transaction:
    transaction_id: int
    trade_id: int
    period: int
    good: str
    quantity: float
    sender: str
    receiver: str


class Ledger:
    """Append-only record of every physical transfer in the economy."""

    def __init__(self) -> None:
        self._transactions: list[Transaction] = []

    @property
    def transactions(self) -> tuple[Transaction, ...]:
        return tuple(self._transactions)

    def transfer(
        self,
        *,
        trade_id: int,
        period: int,
        good: str,
        quantity: float,
        sender: Agent,
        receiver: Agent,
    ) -> Transaction:
        if quantity <= 0:
            raise ValueError("transfer quantity must be strictly positive")
        if sender.holdings[good] + 1e-12 < quantity:
            raise ValueError(f"{sender.name} does not have enough {good}")

        sender.holdings[good] -= quantity
        receiver.holdings[good] += quantity
        transaction = Transaction(
            transaction_id=len(self._transactions) + 1,
            trade_id=trade_id,
            period=period,
            good=good,
            quantity=quantity,
            sender=sender.name,
            receiver=receiver.name,
        )
        self._transactions.append(transaction)
        return transaction

    def net_flows(self, agent_name: str, goods: Iterable[str]) -> dict[str, float]:
        result = {good: 0.0 for good in goods}
        for transaction in self._transactions:
            if transaction.receiver == agent_name:
                result[transaction.good] += transaction.quantity
            if transaction.sender == agent_name:
                result[transaction.good] -= transaction.quantity
        return result
