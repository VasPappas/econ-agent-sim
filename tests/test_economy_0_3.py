from math import isclose

import pytest

from econ_agent_sim.economy_0_2 import ExchangeAgentConfig
from econ_agent_sim.economy_0_3 import (
    Economy03Config,
    canonical_period_populations,
    run_economy_0_3,
)


def test_canonical_schedule_has_four_periods_with_fixed_agents_and_totals() -> None:
    periods = canonical_period_populations()

    assert len(periods) == 4
    reference_names = tuple(agent.name for agent in periods[0])
    reference_alphas = tuple(agent.alpha for agent in periods[0])

    for population in periods:
        assert tuple(agent.name for agent in population) == reference_names
        assert tuple(agent.alpha for agent in population) == reference_alphas
        assert isclose(sum(agent.x for agent in population), 10.0, abs_tol=1e-12)
        assert isclose(sum(agent.y for agent in population), 10.0, abs_tol=1e-12)

    assert tuple(agent.y for agent in periods[1]) != tuple(
        agent.y for agent in periods[0]
    )


def test_each_period_converges_to_its_analytic_benchmark() -> None:
    result = run_economy_0_3()

    for period in result.periods:
        assert isclose(
            period.prices["X"],
            period.benchmark_price_x,
            abs_tol=1e-8,
        )
        assert period.steps[-1].market_error <= result.config.tolerance

    prices = [period.prices["X"] for period in result.periods]
    assert isclose(prices[0], 1.0, abs_tol=1e-8)
    assert len({round(price, 6) for price in prices}) > 1


def test_configured_initial_price_starts_every_period_tatonnement() -> None:
    config = Economy03Config(initial_price_x=2.0)
    result = run_economy_0_3(config)

    for period in result.periods:
        assert isclose(period.steps[0].price_x, 2.0, abs_tol=1e-12)
        assert isclose(
            period.prices["X"],
            period.benchmark_price_x,
            abs_tol=1e-8,
        )

    assert result.periods[0].steps[-1].iteration > 0


def test_next_period_uses_fresh_endowments_not_previous_closing_stocks() -> None:
    result = run_economy_0_3()
    first, second = result.periods[:2]

    assert second.opening_stocks["Agent 1"]["X"] == 1.8
    assert second.opening_stocks["Agent 1"]["Y"] == 1.4
    assert not isclose(
        first.closing_stocks["Agent 1"]["Y"],
        second.opening_stocks["Agent 1"]["Y"],
        abs_tol=1e-10,
    )


def test_combined_ledger_has_unique_ids_and_explicit_periods() -> None:
    result = run_economy_0_3()

    ids = [transaction.transaction_id for transaction in result.transactions]
    assert ids == list(range(1, len(ids) + 1))
    assert {transaction.period for transaction in result.transactions} == {1, 2, 3, 4}
    assert all(
        transaction.trade_id == transaction.period
        for transaction in result.transactions
    )
    assert all(transaction.quantity > 0 for transaction in result.transactions)


def test_stock_flow_identity_and_conservation_hold_in_every_period() -> None:
    result = run_economy_0_3()

    for period in result.periods:
        for agent, opening in period.opening_stocks.items():
            for good, opening_quantity in opening.items():
                assert isclose(
                    opening_quantity + period.flows[agent][good],
                    period.closing_stocks[agent][good],
                    abs_tol=1e-10,
                )

        for good in ("X", "Y"):
            opening_total = sum(
                stocks[good] for stocks in period.opening_stocks.values()
            )
            closing_total = sum(
                stocks[good] for stocks in period.closing_stocks.values()
            )
            net_flow = sum(flows[good] for flows in period.flows.values())
            assert isclose(opening_total, closing_total, abs_tol=1e-10)
            assert isclose(net_flow, 0.0, abs_tol=1e-10)


def test_config_requires_fixed_agent_identity_preferences_and_aggregate_goods() -> None:
    period_one = (
        ExchangeAgentConfig("A", 1.0, 0.0, 0.4),
        ExchangeAgentConfig("B", 0.0, 1.0, 0.6),
    )

    with pytest.raises(ValueError, match="identities"):
        Economy03Config(
            period_populations=(
                period_one,
                (
                    ExchangeAgentConfig("B", 1.0, 0.0, 0.6),
                    ExchangeAgentConfig("A", 0.0, 1.0, 0.4),
                ),
            )
        )

    with pytest.raises(ValueError, match="preferences"):
        Economy03Config(
            period_populations=(
                period_one,
                (
                    ExchangeAgentConfig("A", 1.0, 0.0, 0.5),
                    ExchangeAgentConfig("B", 0.0, 1.0, 0.6),
                ),
            )
        )

    with pytest.raises(ValueError, match="aggregate X"):
        Economy03Config(
            period_populations=(
                period_one,
                (
                    ExchangeAgentConfig("A", 1.1, 0.0, 0.4),
                    ExchangeAgentConfig("B", 0.0, 1.0, 0.6),
                ),
            )
        )


def test_config_requires_at_least_one_period() -> None:
    with pytest.raises(ValueError, match="at least one period"):
        Economy03Config(period_populations=())
