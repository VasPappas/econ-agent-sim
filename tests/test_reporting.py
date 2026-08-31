from types import SimpleNamespace

from econ_agent_sim.ledger import Transaction
from econ_agent_sim.reporting import (
    ECONOMY_03_LEDGER_DISPLAY_EPSILON,
    transaction_rows,
)


def test_economy_03_ledger_rows_hide_trade_id_and_numerical_dust() -> None:
    result = SimpleNamespace(
        transactions=(
            Transaction(1, 1, 1, "X", 1e-10, "Agent 3", "Agent 2"),
            Transaction(2, 1, 1, "X", 1.4, "Agent 1", "Agent 2"),
        )
    )

    rows = transaction_rows(result)

    assert ECONOMY_03_LEDGER_DISPLAY_EPSILON == 1e-8
    assert rows == [
        {
            "transaction_id": 2,
            "period": 1,
            "good": "X",
            "quantity": 1.4,
            "sender": "Agent 1",
            "receiver": "Agent 2",
        }
    ]
    assert "trade_id" not in rows[0]


def test_period_zero_ledgers_keep_internal_trade_id_for_older_economies() -> None:
    result = SimpleNamespace(
        transactions=(Transaction(1, 1, 0, "X", 0.5, "Alice", "Bob"),)
    )

    rows = transaction_rows(result)

    assert rows[0]["trade_id"] == 1
    assert rows[0]["quantity"] == 0.5
