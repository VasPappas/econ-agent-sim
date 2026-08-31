from econ_agent_sim.economy_0_2 import run_economy_0_2
from econ_agent_sim.economy_0_3 import run_economy_0_3
from econ_agent_sim.reporting import transaction_rows


def test_settlement_does_not_record_numerical_dust_as_transactions() -> None:
    result = run_economy_0_2()
    total_x = sum(stocks["X"] for stocks in result.opening_stocks.values())
    settlement_floor = max(result.config.tolerance, 1e-10) * max(1.0, total_x) * 2.0

    assert result.transactions
    assert all(transaction.quantity > settlement_floor for transaction in result.transactions)


def test_economy_0_3_ledger_hides_internal_trade_group_id() -> None:
    result = run_economy_0_3()
    rows = transaction_rows(result)

    assert rows
    assert list(rows[0]) == [
        "transaction_id",
        "period",
        "good",
        "quantity",
        "sender",
        "receiver",
    ]
    assert "trade_id" not in rows[0]

    # The engine still preserves the grouping identifier for future economies where
    # one period may contain multiple settlement events.
    assert all(
        transaction.trade_id == transaction.period for transaction in result.transactions
    )
