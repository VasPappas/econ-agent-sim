"""Targets describe physical coverage, independently of monetary valuation."""

import json
from dataclasses import replace
from math import fsum

import pytest

from econ_agent_sim.competition_reporting import competition_report
from econ_agent_sim.economy_1_0 import Household as LegacyHousehold
from econ_agent_sim.economy_1_0 import advance_competition_period
from econ_agent_sim.economy_1_1 import (
    Firm,
    Household,
    advance_target_period,
    default_firms,
    default_households,
)
from econ_agent_sim.target_comparison import compare_target_runs
from econ_agent_sim.target_reporting import _coverage, target_report


def run(count=1, *, households=None, firms=None):
    households = households or tuple(Household(**row) for row in default_households())
    firms = firms or tuple(Firm(**row) for row in default_firms())
    history = []
    for _ in range(count):
        history.append(advance_target_period(
            households, firms, history[-1] if history else None
        ))
    return tuple(history)


def test_coverage_cannot_offset_a_shortfall_with_a_later_surplus():
    covered = _coverage((0.2, 0.8), 0.5)
    assert covered["needed_x"] == 1
    assert covered["needs_met_x"] == pytest.approx(0.7)
    assert covered["shortfall_x"] == pytest.approx(0.3)
    assert covered["target_coverage"] == pytest.approx(0.7)
    assert covered["below_target_periods"] == 1
    assert _coverage((0.5 - 1e-12,), 0.5)["below_target_periods"] == 0
    assert _coverage((0.5 - 1e-12,), 0.5)["shortfall_x"] > 0


def test_report_covers_households_separately_and_keeps_actual_consumption():
    households = (
        Household("household_1", "Household 1", consumption_target=0.1),
        Household("household_2", "Household 2", consumption_target=2),
    )
    period = run(households=households)[0]
    report = target_report(period)
    assert report["model"] == "consumption_target"
    assert all(report["checks"].values())
    first, second = report["households"]
    assert first["consumed_x"] > first["needed_x"]
    assert second["consumed_x"] < second["needed_x"]
    assert first["shortfall_x"] == 0
    assert second["shortfall_x"] == pytest.approx(2 - second["consumed_x"])
    assert first["parameters"]["consumption_target"] == 0.1
    economy = report["economy"]
    assert economy["consumed_x"] == fsum(period.consumption.values())
    assert economy["needed_x"] == 2.1
    assert economy["shortfall_x"] == second["shortfall_x"]
    assert economy["shortfall_x"] > max(economy["needed_x"] - economy["consumed_x"], 0)
    assert economy["needs_met_x"] + economy["shortfall_x"] == pytest.approx(2.1)
    assert economy["households_below_target"] == 1
    assert economy["household_periods_below_target"] == 1


def test_cumulative_reports_preserve_original_prices_and_sum_period_shortfalls():
    households = tuple(
        replace(Household(**row), consumption_target=1)
        for row in default_households()
    )
    periods = run(15, households=households)
    report = target_report(periods, cumulative=True)
    assert all(report["checks"].values())
    assert report["economy"]["needed_x"] == 30
    assert report["economy"]["production_value"] == fsum(p.production_value for p in periods)
    assert report["economy"]["production_value"] != pytest.approx(
        report["economy"]["produced_x"] * periods[-1].price
    )
    for household in report["households"]:
        consumption = [period.consumption[household["entity_id"]] for period in periods]
        assert min(consumption) < 1 < max(consumption)
        assert household["consumed_x"] == fsum(consumption)
        assert household["needed_x"] == 15
        assert household["shortfall_x"] == fsum(max(1 - value, 0) for value in consumption)
        assert household["shortfall_x"] > max(15 - fsum(consumption), 0)
        assert household["needs_met_x"] + household["shortfall_x"] == pytest.approx(15)
    assert report["economy"]["household_periods_below_target"] == sum(
        entry["below_target_periods"] for entry in report["households"]
    )
    assert target_report(periods) == target_report(periods[-1])


def test_zero_target_is_not_applicable_and_preserves_legacy_accounts():
    households = tuple(
        replace(Household(**row), consumption_target=0)
        for row in default_households()
    )
    periods = run(3, households=households)
    legacy = []
    for _ in range(3):
        legacy.append(advance_competition_period(
            tuple(LegacyHousehold(entry.id, entry.name) for entry in households),
            periods[0].firms, legacy[-1] if legacy else None,
        ))
    report = target_report(periods, cumulative=True)
    old = competition_report(legacy, cumulative=True)
    assert report["price"] == old["price"]
    assert report["wage"] == old["wage"]
    assert report["firms"] == old["firms"]
    assert report["economy"]["consumed_x"] == old["economy"]["consumed_x"]
    for entry in (*report["households"], report["economy"]):
        assert entry["needed_x"] == entry["needs_met_x"] == entry["shortfall_x"] == 0
        assert entry["target_coverage"] is None
    assert report["economy"]["households_below_target"] == 0
    assert report["economy"]["household_periods_below_target"] == 0


def test_full_precision_export_includes_target_coverage_and_is_detached():
    periods = run(2)
    report = target_report(periods, cumulative=True)
    json.dumps(report, allow_nan=False)
    rows = [row for row in report["rows"] if row.get("account_type") == "household"]
    assert len(rows) == 4
    for row in rows:
        period = periods[row["period"] - 1]
        assert row["consumption_target"] == row["needed_x"] == 0.5
        assert row["consumed_x"] == period.consumption[row["entity_id"]]
        assert row["needs_met_x"] + row["shortfall_x"] == pytest.approx(0.5)
    report["households"][0]["parameters"]["consumption_target"] = 99
    assert target_report(periods)["households"][0]["parameters"]["consumption_target"] == 0.5


def test_reports_reject_different_engines_changed_targets_and_unlinked_histories():
    first, second, third = run(3)
    changed = replace(second, households=(
        replace(second.households[0], consumption_target=0.8), second.households[1],
    ))
    legacy = advance_competition_period(
        (LegacyHousehold("h1", "H1"), LegacyHousehold("h2", "H2")), first.firms,
    )
    for history in ((), (legacy,), legacy, (first, third), (first, first), (first, changed)):
        with pytest.raises(ValueError):
            target_report(history, cumulative=True)


def test_comparison_exposes_changed_targets_and_compares_actual_shortfalls():
    baseline = run(3)
    households = tuple(replace(entry, consumption_target=1) for entry in baseline[0].households)
    current = run(3, households=households, firms=tuple(reversed(baseline[0].firms)))
    comparison = compare_target_runs(current, baseline, selected_period=3, cumulative=True)
    assert comparison["available"]
    assert len(comparison["metrics"]) == 7
    assert [change["label"] for change in comparison["settings_changes"]] == [
        "Consumption target", "Consumption target",
    ]
    assert all(change["baseline"] == 0.5 and change["current"] == 1
               for change in comparison["settings_changes"])
    metric = next(item for item in comparison["metrics"] if item["key"] == "shortfall")
    assert metric["current"] == target_report(current, True)["economy"]["shortfall_x"]
    assert metric["baseline"] == target_report(baseline, True)["economy"]["shortfall_x"]
    assert metric["change"] == metric["current"] - metric["baseline"]
    assert comparison["firms"][0]["entity_id"] == "firm_b"
    assert all(firm["available"] for firm in comparison["firms"])
    assert "Each run uses its own consumption targets" in comparison["note"]


def test_unavailable_comparison_retains_target_changes_and_does_not_extend_runs():
    baseline = run()
    current = run(2, households=tuple(
        replace(entry, consumption_target=0) for entry in baseline[0].households
    ))
    comparison = compare_target_runs(current, baseline, selected_period=2)
    assert not comparison["available"]
    assert comparison["comparable_through"] == 1
    assert comparison["metrics"] == []
    assert len(comparison["settings_changes"]) == 2
    assert len(current) == 2 and len(baseline) == 1
    with pytest.raises(ValueError, match="1.1"):
        compare_target_runs((object(),), baseline, selected_period=1)
    with pytest.raises(ValueError):
        compare_target_runs(current, baseline, selected_period=True)
