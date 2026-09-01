from math import isclose

import pytest

from econ_agent_sim.economy_0_2 import canonical_population
from econ_agent_sim.economy_0_3 import baseline_period_populations, redistribute_y
from econ_agent_sim.economy_0_4 import (
    ASSETS,
    MONEY,
    Economy04Config,
    run_economy_0_4,
)


def test_default_economy_0_4_preserves_the_ten_agent_baseline() -> None:
    result = run_economy_0_4()

    assert len(result.periods) == 1
    period = result.periods[0]
    assert len(period.population) == 10
    assert set(period.opening_stocks) == {f"Agent {index}" for index in range(1, 11)}
    assert all(
        isclose(stocks[MONEY], 10.0, abs_tol=1e-12)
        for stocks in period.opening_stocks.values()
    )
    assert isclose(period.prices["Y"], 1.0, abs_tol=1e-12)
    assert isclose(period.prices["X"], 1.0, abs_tol=1e-5)


def test_economy_0_4_supports_even_mirrored_population_sizes() -> None:
    for agent_count in (2, 6, 10, 20):
        population = canonical_population(agent_count)
        result = run_economy_0_4(
            Economy04Config(period_populations=(population,))
        )
        period = result.periods[0]

        assert len(period.population) == agent_count
        assert len(period.opening_stocks) == agent_count
        assert isclose(period.prices["X"], 1.0, abs_tol=1e-5)
        assert isclose(
            sum(row[MONEY] for row in period.opening_stocks.values()),
            10.0 * agent_count,
            abs_tol=1e-10,
        )


def test_opening_money_does_not_change_preferences_prices_or_real_allocation() -> None:
    low_money = run_economy_0_4(Economy04Config(opening_money_per_agent=1.0))
    high_money = run_economy_0_4(Economy04Config(opening_money_per_agent=1000.0))

    low_period = low_money.periods[0]
    high_period = high_money.periods[0]

    assert low_period.prices == high_period.prices
    assert low_period.wealths == high_period.wealths
    assert low_period.desired_bundles == high_period.desired_bundles
    for name in low_period.closing_stocks:
        for good in ("X", "Y"):
            assert isclose(
                low_period.closing_stocks[name][good],
                high_period.closing_stocks[name][good],
                abs_tol=1e-12,
            )


def test_every_goods_trade_has_one_reverse_money_payment_leg() -> None:
    period = run_economy_0_4().periods[0]

    assert period.trades
    assert len(period.transactions) == 2 * len(period.trades)

    by_trade: dict[int, list] = {}
    for transaction in period.transactions:
        by_trade.setdefault(transaction.trade_id, []).append(transaction)

    for trade in period.trades:
        legs = by_trade[trade.trade_id]
        assert len(legs) == 2
        goods_leg = next(leg for leg in legs if leg.asset == trade.good)
        money_leg = next(leg for leg in legs if leg.asset == MONEY)

        assert goods_leg.sender == trade.seller
        assert goods_leg.receiver == trade.buyer
        assert isclose(goods_leg.quantity, trade.quantity, abs_tol=1e-12)

        assert money_leg.sender == trade.buyer
        assert money_leg.receiver == trade.seller
        assert isclose(money_leg.quantity, trade.payment, abs_tol=1e-12)
        assert isclose(
            trade.payment,
            trade.quantity * trade.unit_price,
            abs_tol=1e-12,
        )


def test_money_flow_exactly_offsets_value_of_each_agents_real_net_trade() -> None:
    period = run_economy_0_4().periods[0]

    for name, flows in period.flows.items():
        real_trade_value = (
            period.prices["X"] * flows["X"] + period.prices["Y"] * flows["Y"]
        )
        assert isclose(
            flows[MONEY] + real_trade_value,
            0.0,
            abs_tol=1e-10,
        ), name


def test_stock_flow_identity_and_conservation_include_money() -> None:
    period = run_economy_0_4().periods[0]

    for name, opening in period.opening_stocks.items():
        for asset in ASSETS:
            assert isclose(
                opening[asset] + period.flows[name][asset],
                period.closing_stocks[name][asset],
                abs_tol=1e-10,
            )

    for asset in ASSETS:
        opening_total = sum(row[asset] for row in period.opening_stocks.values())
        closing_total = sum(row[asset] for row in period.closing_stocks.values())
        aggregate_flow = sum(row[asset] for row in period.flows.values())
        assert isclose(opening_total, closing_total, abs_tol=1e-10)
        assert isclose(aggregate_flow, 0.0, abs_tol=1e-10)


def test_repeated_redistribution_periods_are_preserved_with_monetary_settlement() -> None:
    baseline = baseline_period_populations()[0]
    redistributed = redistribute_y(
        baseline,
        sender_name="Agent 1",
        receiver_name="Agent 2",
        amount=0.1,
    )
    result = run_economy_0_4(
        Economy04Config(period_populations=(baseline, redistributed))
    )

    assert len(result.periods) == 2
    assert result.periods[0].period == 1
    assert result.periods[1].period == 2
    assert result.periods[1].prices["X"] > result.periods[0].prices["X"]
    assert len({trade.trade_id for trade in result.trades}) == len(result.trades)
    assert len({row.transaction_id for row in result.transactions}) == len(
        result.transactions
    )
    assert {row.period for row in result.transactions} == {1, 2}


def test_gross_money_payments_equal_sum_of_payment_legs() -> None:
    period = run_economy_0_4().periods[0]

    payment_total = sum(
        transaction.quantity
        for transaction in period.transactions
        if transaction.asset == MONEY
    )
    assert isclose(period.gross_money_payments, payment_total, abs_tol=1e-12)
    assert period.gross_money_payments > 0.0


def test_opening_money_must_be_positive() -> None:
    with pytest.raises(ValueError, match="strictly positive"):
        Economy04Config(opening_money_per_agent=0.0)
