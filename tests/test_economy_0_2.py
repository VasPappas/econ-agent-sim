from math import isclose

import pytest

from econ_agent_sim.economy_0_2 import (
    Economy02Config,
    ExchangeAgentConfig,
    canonical_population,
    run_economy_0_2,
)


def test_canonical_population_has_ten_heterogeneous_agents() -> None:
    population = canonical_population()

    assert len(population) == 10
    assert len({agent.name for agent in population}) == 10
    assert len({agent.alpha for agent in population}) > 2
    assert len({(agent.x, agent.y) for agent in population}) > 2


def test_canonical_many_agent_tatonnement_converges_to_one() -> None:
    result = run_economy_0_2()

    assert isclose(result.benchmark_price_x, 1.0, abs_tol=1e-12)
    assert isclose(result.prices["X"], 1.0, abs_tol=1e-8)
    assert isclose(result.prices["X"], result.benchmark_price_x, abs_tol=1e-8)
    assert result.steps[-1].market_error <= result.config.tolerance


def test_engine_accepts_arbitrary_named_population() -> None:
    config = Economy02Config(
        agents=(
            ExchangeAgentConfig("Household A", 2.0, 0.5, 0.25),
            ExchangeAgentConfig("Household B", 0.5, 1.0, 0.50),
            ExchangeAgentConfig("Household C", 0.5, 1.5, 0.75),
        ),
        initial_price_x=0.4,
        adjustment_speed=0.8,
    )

    result = run_economy_0_2(config)

    assert set(result.opening_stocks) == {
        "Household A",
        "Household B",
        "Household C",
    }
    assert isclose(result.prices["X"], result.benchmark_price_x, abs_tol=1e-8)


def test_many_agent_settlement_reaches_desired_allocation_within_tolerance() -> None:
    result = run_economy_0_2()

    for agent, bundle in result.desired_bundles.items():
        for good, target in bundle.items():
            assert isclose(
                result.closing_stocks[agent][good],
                target,
                abs_tol=1e-8,
            )


def test_many_agent_settlement_is_fully_ledgered() -> None:
    result = run_economy_0_2()

    assert len(result.transactions) > 2
    assert {transaction.trade_id for transaction in result.transactions} == {1}
    assert all(transaction.quantity > 0 for transaction in result.transactions)
    assert all(
        transaction.sender != transaction.receiver
        for transaction in result.transactions
    )

    transferred_goods = {transaction.good for transaction in result.transactions}
    assert transferred_goods == {"X", "Y"}


def test_stock_flow_identity_and_conservation_hold_for_all_agents() -> None:
    result = run_economy_0_2()

    for agent, opening in result.opening_stocks.items():
        for good, opening_quantity in opening.items():
            assert isclose(
                opening_quantity + result.flows[agent][good],
                result.closing_stocks[agent][good],
                abs_tol=1e-10,
            )

    for good in ("X", "Y"):
        opening_total = sum(v[good] for v in result.opening_stocks.values())
        closing_total = sum(v[good] for v in result.closing_stocks.values())
        net_flow = sum(v[good] for v in result.flows.values())
        assert isclose(opening_total, closing_total, abs_tol=1e-10)
        assert isclose(net_flow, 0.0, abs_tol=1e-10)


def test_population_requires_unique_names_and_both_goods() -> None:
    duplicate = ExchangeAgentConfig("Same", 1.0, 0.0, 0.5)
    with pytest.raises(ValueError, match="unique"):
        Economy02Config(agents=(duplicate, duplicate))

    with pytest.raises(ValueError, match="some Y"):
        Economy02Config(
            agents=(ExchangeAgentConfig("Only X", 1.0, 0.0, 0.5),)
        )
