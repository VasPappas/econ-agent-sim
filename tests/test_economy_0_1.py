from math import isclose

from econ_agent_sim.economy_0 import Economy0Config
from econ_agent_sim.economy_0_1 import Economy01Config, run_economy_0_1


def test_canonical_tatonnement_converges_to_textbook_price() -> None:
    result = run_economy_0_1()

    assert isclose(result.prices["X"], 1.0, abs_tol=1e-8)
    assert isclose(result.benchmark_price_x, 1.0, abs_tol=1e-12)
    assert isclose(result.prices["X"], result.benchmark_price_x, abs_tol=1e-8)


def test_excess_demand_raises_the_trial_price() -> None:
    result = run_economy_0_1()
    first = result.steps[0]

    assert first.price_x == 0.5
    assert first.excess_demand_x > 0
    assert first.next_price_x is not None
    assert first.next_price_x > first.price_x


def test_each_iteration_follows_the_documented_adjustment_rule() -> None:
    result = run_economy_0_1()
    speed = result.config.adjustment_speed

    for step in result.steps[:-1]:
        expected = step.price_x * (
            1.0 + speed * step.normalized_excess_demand_x
        )
        assert step.next_price_x is not None
        assert isclose(step.next_price_x, expected, abs_tol=1e-12)


def test_no_trade_occurs_until_price_discovery_has_converged() -> None:
    result = run_economy_0_1()

    assert result.steps[-1].next_price_x is None
    assert abs(result.steps[-1].normalized_excess_demand_x) <= result.config.tolerance
    assert len(result.transactions) == 2


def test_canonical_final_allocation_matches_economy_zero() -> None:
    result = run_economy_0_1()

    for agent in ("Alice", "Bob"):
        assert isclose(result.closing_stocks[agent]["X"], 0.5, abs_tol=1e-8)
        assert isclose(result.closing_stocks[agent]["Y"], 0.5, abs_tol=1e-8)


def test_custom_scenario_converges_to_analytic_benchmark() -> None:
    exchange = Economy0Config(
        alice_x=2.0,
        alice_y=0.5,
        alice_alpha=0.25,
        bob_x=0.5,
        bob_y=2.0,
        bob_alpha=0.75,
    )
    result = run_economy_0_1(
        Economy01Config(
            exchange=exchange,
            initial_price_x=0.3,
            adjustment_speed=0.8,
        )
    )

    assert isclose(result.prices["X"], result.benchmark_price_x, abs_tol=1e-8)


def test_stock_flow_identity_and_conservation_still_hold() -> None:
    result = run_economy_0_1()

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
        assert isclose(opening_total, closing_total, abs_tol=1e-10)
