from math import isclose

import pytest

from econ_agent_sim.economy_0_2 import Economy02Config, ExchangeAgentConfig
from econ_agent_sim.economy_0_3 import (
    Economy03Config,
    baseline_period_populations,
    canonical_period_populations,
    redistribute_y,
    run_economy_0_3,
)


def _user_defined_periods() -> tuple[tuple[ExchangeAgentConfig, ...], ...]:
    baseline = baseline_period_populations()[0]
    second = redistribute_y(
        baseline,
        sender_name="Agent 2",
        receiver_name="Agent 1",
        amount=0.5,
    )
    third = redistribute_y(
        second,
        sender_name="Agent 4",
        receiver_name="Agent 6",
        amount=0.25,
    )
    return baseline, second, third


def test_legacy_canonical_schedule_remains_reproducible() -> None:
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


def test_economy_0_3_uses_practical_default_tolerance_only() -> None:
    assert Economy03Config().tolerance == 1e-6
    assert Economy02Config().tolerance == 1e-10


def test_default_scenario_is_the_single_baseline_period() -> None:
    result = run_economy_0_3()

    assert len(result.periods) == 1
    period = result.periods[0]
    assert isclose(period.prices["X"], 1.0, abs_tol=1e-5)
    assert isclose(period.prices["X"], period.benchmark_price_x, abs_tol=1e-5)
    assert period.steps[-1].market_error <= result.config.tolerance


def test_redistribute_y_preserves_totals_and_changes_only_selected_agents() -> None:
    baseline = baseline_period_populations()[0]
    redistributed = redistribute_y(
        baseline,
        sender_name="Agent 2",
        receiver_name="Agent 1",
        amount=0.5,
    )

    before = {agent.name: agent for agent in baseline}
    after = {agent.name: agent for agent in redistributed}

    assert isclose(after["Agent 2"].y, before["Agent 2"].y - 0.5, abs_tol=1e-12)
    assert isclose(after["Agent 1"].y, before["Agent 1"].y + 0.5, abs_tol=1e-12)
    assert isclose(sum(agent.y for agent in baseline), 10.0, abs_tol=1e-12)
    assert isclose(sum(agent.y for agent in redistributed), 10.0, abs_tol=1e-12)

    for agent in baseline:
        assert after[agent.name].x == agent.x
        assert after[agent.name].alpha == agent.alpha
        if agent.name not in {"Agent 1", "Agent 2"}:
            assert after[agent.name].y == agent.y


def test_user_can_define_any_number_of_redistribution_periods() -> None:
    periods = _user_defined_periods()
    result = run_economy_0_3(Economy03Config(period_populations=periods))

    assert len(result.periods) == 3
    for period in result.periods:
        assert isclose(period.prices["X"], period.benchmark_price_x, abs_tol=1e-5)
        assert period.steps[-1].market_error <= result.config.tolerance
        assert round(period.prices["X"], 4) == round(period.benchmark_price_x, 4)

    prices = [period.prices["X"] for period in result.periods]
    assert len({round(price, 6) for price in prices}) > 1


def test_configured_initial_price_starts_every_period_tatonnement() -> None:
    config = Economy03Config(
        period_populations=_user_defined_periods(),
        initial_price_x=2.0,
    )
    result = run_economy_0_3(config)

    for period in result.periods:
        assert isclose(period.steps[0].price_x, 2.0, abs_tol=1e-12)
        assert isclose(
            period.prices["X"],
            period.benchmark_price_x,
            abs_tol=1e-5,
        )

    assert result.periods[0].steps[-1].iteration > 0


def test_lower_lambda_slows_tatonnement_without_changing_equilibrium() -> None:
    fast = run_economy_0_3(Economy03Config(adjustment_speed=1.0))
    slow = run_economy_0_3(Economy03Config(adjustment_speed=0.1))

    for fast_period, slow_period in zip(fast.periods, slow.periods, strict=True):
        assert slow_period.steps[-1].iteration > fast_period.steps[-1].iteration
        assert isclose(
            slow_period.prices["X"],
            fast_period.prices["X"],
            abs_tol=1e-5,
        )
        assert isclose(
            slow_period.prices["X"],
            slow_period.benchmark_price_x,
            abs_tol=1e-5,
        )

    assert fast.periods[0].steps[-1].iteration == 14
    assert slow.periods[0].steps[-1].iteration == 205


def test_next_period_uses_user_endowment_reset_not_previous_closing_stocks() -> None:
    periods = _user_defined_periods()[:2]
    result = run_economy_0_3(Economy03Config(period_populations=periods))
    first, second = result.periods

    assert second.opening_stocks["Agent 1"]["X"] == 1.8
    assert second.opening_stocks["Agent 1"]["Y"] == 0.7
    assert not isclose(
        first.closing_stocks["Agent 1"]["Y"],
        second.opening_stocks["Agent 1"]["Y"],
        abs_tol=1e-10,
    )


def test_combined_ledger_has_unique_ids_and_explicit_user_periods() -> None:
    periods = _user_defined_periods()
    result = run_economy_0_3(Economy03Config(period_populations=periods))

    ids = [transaction.transaction_id for transaction in result.transactions]
    assert ids == list(range(1, len(ids) + 1))
    assert {transaction.period for transaction in result.transactions} == {1, 2, 3}
    assert all(
        transaction.trade_id == transaction.period
        for transaction in result.transactions
    )
    assert all(transaction.quantity > 0 for transaction in result.transactions)


def test_stock_flow_identity_and_conservation_hold_in_every_user_period() -> None:
    periods = _user_defined_periods()
    result = run_economy_0_3(Economy03Config(period_populations=periods))

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


def test_redistribution_rejects_invalid_transfers() -> None:
    baseline = baseline_period_populations()[0]

    with pytest.raises(ValueError, match="different agents"):
        redistribute_y(
            baseline,
            sender_name="Agent 1",
            receiver_name="Agent 1",
            amount=0.1,
        )

    with pytest.raises(ValueError, match="only has"):
        redistribute_y(
            baseline,
            sender_name="Agent 1",
            receiver_name="Agent 2",
            amount=1.0,
        )

    with pytest.raises(ValueError, match="unknown receiver"):
        redistribute_y(
            baseline,
            sender_name="Agent 1",
            receiver_name="Nobody",
            amount=0.1,
        )


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
