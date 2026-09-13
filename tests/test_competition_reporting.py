"""Money, physical flow and identity contracts for two-firm statements."""

import csv
import io
import json
from dataclasses import replace
from math import fsum

import pytest

from econ_agent_sim.competition_comparison import compare_competition_runs
from econ_agent_sim.competition_reporting import competition_report
from econ_agent_sim.economy_1_0 import (
    Firm,
    Household,
    advance_competition_period,
    default_firms,
    default_households,
)


def run(count=1, *, firms=None, households=None):
    firms = firms or tuple(Firm(**entry) for entry in default_firms())
    households = households or tuple(Household(**entry) for entry in default_households())
    periods = []
    for _ in range(count):
        periods.append(advance_competition_period(
            households, firms, periods[-1] if periods else None
        ))
    return tuple(periods)


def assert_accounts(report):
    assert all(report["checks"].values()), report["checks"]
    economy = report["economy"]
    for firm in report["firms"]:
        assert firm["opening_money"] + firm["sales_received"] == pytest.approx(
            firm["closing_money"] + firm["wages_paid"] + firm["dividends_paid"]
        )
        assert firm["equity_open"] + firm["net_operating_profit"] + firm["holding_gain"] == pytest.approx(
            firm["equity_close"] + firm["dividends_paid"]
        )
        assert firm["capital_value_open"] + firm["investment_value"] + firm["holding_gain"] == pytest.approx(
            firm["capital_value_close"] + firm["depreciation_value"]
        )
        assert firm["contributed_equity"] + firm["retained_earnings_close"] + firm["revaluation_reserve_close"] == pytest.approx(firm["equity_close"])
        for field in ("wages_paid", "dividends_paid", "sold_x", "sales_received"):
            assert fsum(item[field] for item in firm["allocations"]) == pytest.approx(firm[field])
    for household in report["households"]:
        assert household["opening_money"] + household["wages_received"] + household["dividends_received"] == pytest.approx(
            household["closing_money"] + household["purchases_paid"]
        )
        for field in ("wages_received", "dividends_received", "purchases_paid", "consumed_x", "ownership_value_open", "ownership_value_close"):
            assert fsum(item[field] for item in household["firms"]) == pytest.approx(household[field])
    assert economy["assets_close"] == pytest.approx(economy["closing_money"] + economy["capital_value_close"])
    assert fsum(h["ownership_value_close"] for h in report["households"]) == pytest.approx(
        fsum(f["equity_close"] for f in report["firms"])
    )
    assert economy["produced_x"] == pytest.approx(economy["consumed_x"] + economy["investment_quantity"])
    assert economy["production_value"] == pytest.approx(economy["net_income"] + economy["depreciation_value"])
    assert economy["household_cash_saving"] + economy["firm_net_saving"] == pytest.approx(
        economy["investment_value"] - economy["depreciation_value"]
    )


def test_default_statements_preserve_resource_neutral_baseline_and_both_ownership_claims():
    first = run()[0]
    report = competition_report(first)
    assert "firm" not in report
    assert report["price"] == pytest.approx(1.0365231137)
    assert report["wage"] == pytest.approx(13 / 11)
    assert report["economy"]["closing_money"] == pytest.approx(3)
    assert report["economy"]["capital_open"] == 1
    assert [item["sales_share"] for item in report["firms"]] == pytest.approx([0.5, 0.5])
    assert [item["work_used"] for item in report["firms"]] == pytest.approx([5 / 13, 5 / 13])
    assert all(len(h["firms"]) == 2 for h in report["households"])
    assert all(h["ownership"] == 0.5 for h in report["households"])
    assert_accounts(report)


def test_distinct_firm_sales_and_output_shares_are_not_confused():
    firms = (
        Firm("firm_a", "Firm A", money=1, reinvestment_rate=0.8),
        Firm("firm_b", "Firm B", money=1, reinvestment_rate=0.2),
    )
    report = competition_report(run(firms=firms))
    assert [f["production_share"] for f in report["firms"]] == pytest.approx([0.5, 0.5])
    assert [f["sales_share"] for f in report["firms"]] == pytest.approx([0.4, 0.6])
    assert all(not f["funding_binding"] for f in report["firms"])
    assert_accounts(report)


def test_cumulative_accounts_keep_original_prices_and_ratio_of_summed_sales():
    firms = (
        Firm("firm_a", "Firm A", money=1, reinvestment_rate=0.8),
        Firm("firm_b", "Firm B", money=1, reinvestment_rate=0.2),
    )
    periods = run(8, firms=firms)
    report = competition_report(periods, cumulative=True)
    assert_accounts(report)
    assert report["price"] == periods[-1].price
    assert report["price_wage_period"] == report["through_period"] == 8
    assert report["economy"]["capital_open"] == periods[0].capital_open
    assert report["economy"]["capital_close"] == periods[-1].capital_close
    assert report["economy"]["production_value"] == fsum(p.production_value for p in periods)
    assert report["economy"]["production_value"] != pytest.approx(
        report["economy"]["produced_x"] * periods[-1].price
    )
    first_firm = report["firms"][0]
    physical_share = fsum(p.firm_accounts["firm_a"].sales_quantity for p in periods) / fsum(
        a.sales_quantity for p in periods for a in p.firm_accounts.values()
    )
    assert first_firm["sales_share"] == physical_share
    assert first_firm["sales_share"] != pytest.approx(
        fsum(p.firm_accounts["firm_a"].sales_share for p in periods) / len(periods)
    )
    assert first_firm["revenue_share"] != pytest.approx(first_firm["sales_share"])
    assert first_firm["next_dividend_budget"] == periods[-1].firm_accounts["firm_a"].next_dividend_budget
    assert first_firm["funding_period"] == 8
    assert report["households"][0]["average_work"] == pytest.approx(
        fsum(p.work["household_1"] for p in periods) / 8
    )


def test_reporting_preserves_separate_loss_and_dividend_eligibility():
    periods = run(2, firms=(
        Firm("firm_a", "Firm A", capital=100, depreciation_rate=0.9),
        Firm("firm_b", "Firm B"),
    ))
    first, second = (competition_report(period) for period in periods)
    assert first["firms"][0]["net_operating_profit"] < -9
    assert first["firms"][1]["net_operating_profit"] > 0
    assert second["firms"][0]["dividends_paid"] == 0
    assert second["firms"][1]["dividends_paid"] > 0
    assert_accounts(competition_report(periods, cumulative=True))


def test_report_is_detached_serializable_and_exports_all_firms_and_allocations():
    periods = run(2)
    report = competition_report(periods, cumulative=True)
    json.dumps(report, allow_nan=False)
    report["firms"][0]["parameters"]["capital"] = 99
    report["households"][0]["parameters"]["scores"]["consumption"] = 99
    fresh = competition_report(periods, cumulative=True)
    assert fresh["firms"][0]["parameters"]["capital"] == 0.5
    assert fresh["households"][0]["parameters"]["scores"]["consumption"] == 1
    rows = fresh["rows"]
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(dict.fromkeys(key for row in rows for key in row)))
    writer.writeheader()
    writer.writerows(rows)
    exported = list(csv.DictReader(io.StringIO(output.getvalue())))
    assert {row["record_type"] for row in exported} == {"account", "allocation", "event", "transfer"}
    accounts = [row for row in exported if row["account_type"] == "firm"]
    assert len(accounts) == 4
    assert {row["entity_id"] for row in accounts} == {"firm_a", "firm_b"}
    assert float(accounts[0]["production_value"]) == periods[0].firm_accounts["firm_a"].production_value
    assert len([row for row in exported if row["record_type"] == "allocation"]) == 8
    assert all(row["pair_id"] for row in exported if row["record_type"] == "transfer")


def test_cumulative_report_rejects_gaps_duplicates_changed_settings_and_wrong_engine():
    first, second, third = run(3)
    changed = run(firms=(replace(first.firms[0], productivity=3), first.firms[1]))[0]
    for history in ((), (first, third), (first, first), (first, changed), (object(),)):
        with pytest.raises(ValueError):
            competition_report(history, cumulative=True)
    assert competition_report((first, second, third)) == competition_report(third)


def test_comparison_matches_stable_firm_identity_and_uses_percentage_points():
    baseline = run(3)
    firms = (baseline[0].firms[1], replace(baseline[0].firms[0], productivity=2.4))
    current = run(3, firms=firms)
    comparison = compare_competition_runs(current, baseline, selected_period=3, cumulative=True)
    assert comparison["available"] and len(comparison["metrics"]) == 6
    assert len(comparison["firms"]) == 2
    changes = comparison["settings_changes"]
    assert len(changes) == 1
    assert changes[0]["entity_id"] == "firm_a" and changes[0]["label"] == "Productivity"
    baseline_reports = {f["entity_id"]: f for f in competition_report(baseline, True)["firms"]}
    current_reports = {f["entity_id"]: f for f in competition_report(current, True)["firms"]}
    for firm in comparison["firms"]:
        assert len(firm["metrics"]) == 4
        share = next(metric for metric in firm["metrics"] if metric["key"] == "sales_share")
        identity = firm["entity_id"]
        assert share["change_unit"] == "pp"
        assert share["baseline"] == 100 * baseline_reports[identity]["sales_share"]
        assert share["current"] == 100 * current_reports[identity]["sales_share"]


def test_comparison_does_not_extend_short_runs_or_accept_wrong_dates_or_engines():
    history = run(3)
    comparison = compare_competition_runs(history, history[:1], selected_period=3)
    assert not comparison["available"] and comparison["comparable_through"] == 1
    assert comparison["metrics"] == comparison["firms"] == []
    assert len(history) == 3
    for kwargs in (
        {"selected_period": 0}, {"selected_period": True},
        {"selected_period": 1, "current_periods": (object(),)},
        {"selected_period": 1, "current_periods": history[1:]},
    ):
        arguments = {"current_periods": history, "baseline_periods": history, **kwargs}
        with pytest.raises(ValueError):
            compare_competition_runs(**arguments)


def test_comparison_does_not_match_renamed_ids_by_position_or_label():
    baseline = run()
    current = run(firms=(replace(baseline[0].firms[0], id="different_firm"), baseline[0].firms[1]))
    comparison = compare_competition_runs(current, baseline, selected_period=1)
    assert comparison["available"]
    assert not comparison["firms"][0]["available"]
    assert comparison["firms"][0]["metrics"] == []
    assert comparison["firms"][1]["available"]
