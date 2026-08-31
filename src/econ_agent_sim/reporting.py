from __future__ import annotations

from dataclasses import asdict
from typing import Any

from econ_agent_sim.economy_0 import GOODS, Economy0Result

ECONOMY_03_LEDGER_DISPLAY_EPSILON = 1e-8


def accounting_rows(
    result: Economy0Result, transaction_count: int | None = None
) -> list[dict[str, Any]]:
    """Return opening stocks, cumulative flows, and current stocks."""

    count = len(result.transactions) if transaction_count is None else transaction_count
    if not 0 <= count <= len(result.transactions):
        raise ValueError("transaction_count is outside the ledger")

    flows = {
        agent: {good: 0.0 for good in GOODS} for agent in result.opening_stocks
    }
    for transaction in result.transactions[:count]:
        flows[transaction.sender][transaction.good] -= transaction.quantity
        flows[transaction.receiver][transaction.good] += transaction.quantity

    rows: list[dict[str, Any]] = []
    for agent, opening in result.opening_stocks.items():
        for good in GOODS:
            current = opening[good] + flows[agent][good]
            rows.append(
                {
                    "agent": agent,
                    "good": good,
                    "opening_stock": opening[good],
                    "net_flow_so_far": flows[agent][good],
                    "current_stock": current,
                    "check": opening[good] + flows[agent][good] - current,
                }
            )
    return rows


def stock_flow_rows(result: Economy0Result) -> list[dict[str, Any]]:
    rows = accounting_rows(result)
    return [
        {
            "agent": row["agent"],
            "good": row["good"],
            "opening_stock": row["opening_stock"],
            "net_flow": row["net_flow_so_far"],
            "closing_stock": row["current_stock"],
            "check": row["check"],
        }
        for row in rows
    ]


def transaction_rows(
    result: Economy0Result, transaction_count: int | None = None
) -> list[dict[str, Any]]:
    """Return readable ledger rows while preserving raw transactions internally."""

    count = len(result.transactions) if transaction_count is None else transaction_count
    if not 0 <= count <= len(result.transactions):
        raise ValueError("transaction_count is outside the ledger")

    rows = [asdict(transaction) for transaction in result.transactions[:count]]
    if rows and all(row["period"] > 0 for row in rows):
        return [
            {
                "transaction": row["transaction_id"],
                "period": row["period"],
                "good": row["good"],
                "quantity": round(row["quantity"], 10),
                "from": row["sender"],
                "to": row["receiver"],
            }
            for row in rows
            if row["quantity"] > ECONOMY_03_LEDGER_DISPLAY_EPSILON
        ]
    return rows
