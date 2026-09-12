"""Acceptance checks for portable runs and economically comparable results.

These exercise public file/report APIs and independently reconstruct cumulative
flows. A saved setup draft must never rewrite an already completed economy.
"""

from dataclasses import replace
from math import fsum

import pytest

from econ_agent_sim.economy_0_9 import (
    Firm,
    Household,
    advance_investment_period,
    investment_report,
)
from econ_agent_sim.investment_experiments import (
    Experiment,
    dump_experiment,
    load_experiment,
)


def periods_for(households, firm, count):
    periods = []
    previous = None
    for _ in range(count):
        previous = advance_investment_period(households, firm, previous)
        periods.append(previous)
    return tuple(periods)


@pytest.fixture
def experiment():
    households = (
        Household("Household 1", money=1.7, consumption_priority=1.3),
        Household("Household 2", money=.4, leisure_priority=2.7),
    )
    firm = Firm(capital=4.2, reinvestment_rate=.2, depreciation_rate=.15)
    return Experiment(
        name="Consume today — comparison",
        draft_households=(
            replace(households[0], money=3.0),
            replace(households[1], leisure_priority=.4),
            Household("Household 3"),
        ),
        draft_firm=replace(firm, reinvestment_rate=.7),
        periods=periods_for(households, firm, 6),
        selected_period=3,
        report_scope="Cumulative",
    )


def test_portable_run_preserves_separate_draft_every_account_and_continuation(
    experiment,
):
    restored = load_experiment(dump_experiment(experiment)).current
    assert restored == experiment
    assert len(restored.draft_households) == 3
    assert len(restored.periods[-1].households) == 2
    assert restored.draft_firm.reinvestment_rate == .7
    assert restored.periods[-1].firm.reinvestment_rate == .2
    assert restored.selected_period == 3
    assert restored.report_scope == "Cumulative"

    # Exact comparison includes original prices, all historical transfers,
    # noncash events, full-precision account rows and cumulative balances.
    for through in range(1, 7):
        for cumulative in (False, True):
            assert investment_report(
                restored.periods[:through], cumulative=cumulative
            ) == investment_report(
                experiment.periods[:through], cumulative=cumulative
            )
    old_last = experiment.periods[-1]
    new_last = restored.periods[-1]
    uninterrupted = advance_investment_period(
        old_last.households, old_last.firm, old_last
    )
    continued = advance_investment_period(
        new_last.households, new_last.firm, new_last
    )
    assert continued == uninterrupted


def test_cumulative_comparison_keeps_historical_flow_prices_and_endpoint_stocks():
    from econ_agent_sim.investment_comparison import compare_investment_runs

    households = (Household("Household 1"), Household("Household 2"))
    baseline = periods_for(households, Firm(reinvestment_rate=.2), 8)
    current = periods_for(households, Firm(reinvestment_rate=.7), 5)
    compared = compare_investment_runs(
        current, baseline, selected_period=4, cumulative=True
    )
    assert compared["available"] is True
    assert compared["through_period"] == 4
    metrics = {item["key"]: item for item in compared["metrics"]}
    assert len(metrics) == 6
    # Do not accept repricing every period's wage or output using period 4.
    for side, periods in (("current", current[:4]), ("baseline", baseline[:4])):
        values = {key: row[side] for key, row in metrics.items()}
        expected = {
            "consumption": fsum(fsum(p.consumption.values()) for p in periods),
            "capital": periods[-1].capital_close,
            "work": 100 * fsum(fsum(p.work.values()) for p in periods) / 8,
            "price": periods[-1].price,
            "real_wage": periods[-1].wage / periods[-1].price,
            "profit": fsum(p.net_operating_profit for p in periods),
        }
        assert values == pytest.approx(expected)
        assert expected["profit"] != pytest.approx(
            periods[-1].price * fsum(p.output for p in periods)
            - periods[-1].wage * fsum(fsum(p.work.values()) for p in periods)
            - periods[-1].price * fsum(p.depreciation_quantity for p in periods)
        )
    for metric in metrics.values():
        assert metric["change"] == pytest.approx(
            metric["current"] - metric["baseline"]
        )


def test_comparison_never_substitutes_a_different_period():
    from econ_agent_sim.investment_comparison import compare_investment_runs

    households = (Household("Household 1"), Household("Household 2"))
    periods = periods_for(households, Firm(), 5)
    compared = compare_investment_runs(
        periods, periods[:2], selected_period=4, cumulative=True
    )
    assert compared["available"] is False
    assert compared["comparable_through"] == 2
    assert not compared.get("metrics")


def test_relative_preference_rescaling_is_not_an_economic_setting_change():
    from econ_agent_sim.investment_comparison import compare_investment_runs

    baseline_hh = (Household("Household 1"), Household("Household 2"))
    current_hh = (
        Household(
            "Household 1", consumption_priority=3,
            money_priority=3, leisure_priority=3,
        ),
        baseline_hh[1],
    )
    baseline = periods_for(baseline_hh, Firm(), 2)
    current = periods_for(current_hh, Firm(), 2)
    compared = compare_investment_runs(current, baseline, selected_period=2)
    assert compared["available"] is True
    assert compared["settings_changes"] == []
    for metric in compared["metrics"]:
        assert metric["current"] == pytest.approx(metric["baseline"])
