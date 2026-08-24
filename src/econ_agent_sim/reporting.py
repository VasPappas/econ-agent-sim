from __future__ import annotations

from dataclasses import asdict
from typing import Any

from econ_agent_sim.economy_0 import GOODS, Economy0Result


def stock_flow_rows(result: Economy0Result) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for agent in result.opening_stocks:
        for good in GOODS:
            opening = result.opening_stocks[agent][good]
            flow = result.flows[agent][good]
            closing = result.closing_stocks[agent][good]
            rows.append(
                {
                    "agent": agent,
                    "good": good,
                    "opening_stock": opening,
                    "net_flow": flow,
                    "closing_stock": closing,
                    "check": opening + flow - closing,
                }
            )
    return rows


def transaction_rows(result: Economy0Result) -> list[dict[str, Any]]:
    return [asdict(transaction) for transaction in result.transactions]
