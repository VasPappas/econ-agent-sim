"""Independent cash, goods, ownership and dated-price accounting contracts."""

import csv
import io
import json
from dataclasses import replace
from itertools import pairwise
from math import fsum

import pytest

from econ_agent_sim.comparison import compare_runs
from econ_agent_sim.domain import Settings
from econ_agent_sim.engine import Run, simulate
from econ_agent_sim.reporting import build_report, export_csv


@pytest.fixture(scope="module")
def runs():
    return {capital: simulate(Settings(initial_capital=capital)) for capital in (1., .1, 100.)}


def assert_accounts(report):
    assert all(report["checks"].values()), report["checks"]
    economy = report["economy"]
    for firm in report["firms"]:
        assert firm["opening_money"] + firm["sales_received"] == pytest.approx(
            firm["closing_money"] + firm["wages_paid"] + firm["dividends_paid"]
        )
        assert firm["capital_close"] - firm["capital_open"] == pytest.approx(
            firm["investment_quantity"] - firm["depreciation_quantity"], abs=1e-9
        )
        assert firm["equity_close"] - firm["equity_open"] == pytest.approx(
            firm["net_operating_profit"] - firm["dividends_paid"] + firm["holding_gain"],
            abs=1e-9,
        )
        assert firm["capital_value_close"] - firm["capital_value_open"] == pytest.approx(
            firm["investment_value"] - firm["depreciation_value"] + firm["holding_gain"],
            abs=1e-9,
        )
        assert firm["equity_close"] == pytest.approx(
            firm["closing_money"] + firm["capital_value_close"]
        )
    for household in report["households"]:
        assert household["opening_money"] + household["income_received"] == pytest.approx(
            household["closing_money"] + household["purchases_paid"]
        )
        assert household["average_work"] + household["average_leisure"] == pytest.approx(1)
        assert household["ownership_value_close"] == pytest.approx(
            fsum(.5 * f["equity_close"] for f in report["firms"])
        )
    assert economy["opening_money"] == pytest.approx(1)
    assert economy["closing_money"] == pytest.approx(1)
    assert economy["produced_x"] == pytest.approx(
        economy["consumed_x"] + economy["investment_quantity"]
    )
    assert economy["assets_close"] == pytest.approx(
        fsum(h["assets_close"] for h in report["households"])
    )
    assert economy["production_value"] == pytest.approx(
        economy["net_income"] + economy["depreciation_value"]
    )
    assert economy["household_cash_saving"] + economy["firm_net_saving"] == pytest.approx(
        economy["investment_value"] - economy["depreciation_value"], abs=1e-9
    )


@pytest.mark.parametrize("capital", (1., .1, 100.))
@pytest.mark.parametrize("period,cumulative", ((1, False), (4, False), (25, False), (25, True), (100, True)))
def test_cash_goods_and_book_equity_reconcile_interior_and_boundaries(runs, capital, period, cumulative):
    assert_accounts(build_report(runs[capital], period, cumulative))


def test_per_entity_and_aggregate_quantities_are_not_confused(runs):
    run = runs[1.]
    row = run.periods[2]
    report = build_report(run, 3)
    assert len(report["households"]) == len(report["firms"]) == 2
    assert report["economy"]["consumed_x"] == 2 * row.consumption
    assert report["economy"]["capital_close"] == 2 * row.next_capital
    assert report["economy"]["assets_close"] == pytest.approx(1 + 2 * row.goods_price * row.next_capital)
    for household in report["households"]:
        assert household["consumed_x"] == row.consumption
        assert household["dividends_received"] == row.distribution
        assert household["ownership"] == .5
    for firm in report["firms"]:
        assert firm["capital_close"] == row.next_capital
        assert firm["produced_x"] == row.output


def test_holding_gain_uses_opening_capital_and_previous_price(runs):
    run = runs[1.]
    previous, row = run.periods[:2]
    first = build_report(run, 1)["firms"][0]
    current = build_report(run, 2)["firms"][0]
    assert first["holding_gain"] == 0
    assert first["capital_value_open"] == previous.goods_price * previous.capital
    assert current["capital_value_open"] == first["capital_value_close"]
    assert current["equity_open"] == first["equity_close"]
    expected = (row.goods_price - previous.goods_price) * row.capital
    assert expected != pytest.approx(0, abs=1e-6)
    assert current["holding_gain"] == expected
    assert current["net_operating_profit"] == pytest.approx(
        row.goods_price * (row.output - run.settings.depreciation * row.capital)
        - row.money_wage * row.labor
    )


def test_cumulative_flows_keep_dated_prices_and_stocks_are_not_added(runs):
    run = runs[1.]
    rows = run.periods[:12]
    report = build_report(run, 12, cumulative=True)
    firm = report["firms"][0]
    assert firm["sales_received"] == fsum(r.goods_price * r.consumption for r in rows)
    assert firm["sales_received"] != pytest.approx(rows[-1].goods_price * fsum(r.consumption for r in rows))
    assert firm["investment_value"] == fsum(r.goods_price * r.investment for r in rows)
    assert firm["holding_gain"] == pytest.approx(fsum(
        (new.goods_price - old.goods_price) * new.capital
        for old, new in pairwise(rows)
    ))
    assert firm["capital_open"] == rows[0].capital
    assert firm["capital_close"] == rows[-1].next_capital
    assert firm["opening_money"] == rows[0].firm_cash
    assert firm["closing_money"] == rows[-1].next_firm_cash
    assert report["price"] == rows[-1].goods_price
    assert report["real_wage"] == rows[-1].money_wage / rows[-1].goods_price
    assert report["households"][0]["average_work"] == fsum(r.labor for r in rows) / 12


def test_report_never_substitutes_shadow_values_for_book_equity(runs):
    run = runs[.1]
    row = run.periods[0]
    assert row.cash_shadow_value > 1
    modified = replace(row, capital_shadow_value=99999, cash_shadow_value=12345)
    changed = Run(run.settings, replace(run.solution, periods=(modified, *run.periods[1:])))
    assert build_report(changed, 1) == build_report(run, 1)


def test_zero_choices_are_visible_without_inventing_profit_payout_rule(runs):
    low = build_report(runs[.1], 1)["firms"][0]
    high = build_report(runs[100.], 1)["firms"][0]
    assert low["dividends_paid"] == 0
    assert low["zero_dividend_periods"] == 1
    assert high["investment_quantity"] == 0
    assert high["zero_investment_periods"] == 1
    assert high["dividends_paid"] > 0
    assert high["net_operating_profit"] < 0


def test_reports_are_detached_serializable_and_one_period_cumulative_matches(runs):
    run = runs[1.]
    report = build_report(run, 1)
    json.dumps(report, allow_nan=False)
    assert report["economy"] == build_report(run, 1, True)["economy"]
    report["firms"][0]["closing_money"] = 999
    assert build_report(run, 1)["firms"][0]["closing_money"] == run.periods[0].next_firm_cash


def test_csv_contains_only_visible_periods_and_round_trips_float_precision(runs):
    run = runs[1.]
    rows = list(csv.DictReader(io.StringIO(export_csv(run, 7))))
    assert len(rows) == 7 * 5
    assert {int(row["period"]) for row in rows} == set(range(1, 8))
    assert {row["entity_id"] for row in rows} == {
        "household_1", "household_2", "firm_a", "firm_b", "economy",
    }
    firm_rows = [r for r in rows if r["entity_id"] == "firm_a"]
    assert float(firm_rows[0]["production_value"]) == run.periods[0].goods_price * run.periods[0].output
    assert float(firm_rows[-1]["capital_close"]) == run.periods[6].next_capital
    assert all(row["scope"] == "period" for row in rows)
    assert all(row["money_unit"] == "Money" for row in rows)


@pytest.mark.parametrize("period", (0, -1, 101, 1.5, True))
def test_reporting_rejects_invalid_dates(runs, period):
    with pytest.raises(ValueError):
        build_report(runs[1.], period)
    with pytest.raises(ValueError):
        export_csv(runs[1.], period)


def test_reporting_requires_verified_current_run_and_boolean_scope(runs):
    with pytest.raises(ValueError):
        build_report(object(), 1)
    run = runs[1.]
    with pytest.raises(ValueError):
        build_report(Run(run.settings, replace(run.solution, converged=False)), 1)
    with pytest.raises(ValueError):
        build_report(run, 1, "cumulative")


def test_comparison_uses_same_period_and_records_actual_setting_change(runs):
    comparison = compare_runs(runs[.1], runs[1.], selected_period=4, cumulative=True)
    assert comparison["available"]
    assert comparison["label"] == "Periods 1–4"
    assert comparison["settings_changes"] == [{
        "key": "initial_capital", "label": "Starting capital per firm", "baseline": 1., "current": .1,
    }]
    for item in comparison["metrics"]:
        assert item["change"] == item["current"] - item["baseline"]
    consumption = next(item for item in comparison["metrics"] if item["key"] == "consumed_x")
    assert consumption["current"] == 2 * fsum(r.consumption for r in runs[.1].periods[:4])
    price = next(item for item in comparison["metrics"] if item["key"] == "price")
    assert price["current"] == runs[.1].periods[3].goods_price
    assert price["baseline"] == runs[1.].periods[3].goods_price


def test_comparison_does_not_extend_a_shorter_available_path(runs):
    run = runs[1.]
    short = Run(run.settings, replace(run.solution, periods=run.periods[:2]))
    with pytest.raises(ValueError):
        compare_runs(run, short, selected_period=3)
    same = compare_runs(run, run, selected_period=2)
    assert all(item["change"] == 0 for item in same["metrics"])
    assert same["settings_changes"] == []
