"""Public input, snapshot, report and export boundaries for Economy 0.9."""

import csv
import io
import json
from dataclasses import FrozenInstanceError, replace

import pytest

from econ_agent_sim.economy_0_9 import (
    Economy09Run,
    Firm,
    Household,
    advance_investment_period,
    default_firm,
    default_households,
    investment_report,
)


@pytest.mark.parametrize(
    "factory,settings",
    [
        (Household, {"name": "A", "money": -1}),
        (Household, {"name": "A", "consumption_priority": 0}),
        (Household, {"name": "A", "money_priority": float("nan")}),
        (Household, {"name": "A", "leisure_priority": float("inf")}),
        (Household, {"name": " "}),
        (Firm, {"money": 0}),
        (Firm, {"capital": 0}),
        (Firm, {"productivity": float("inf")}),
        (Firm, {"reinvestment_rate": 1}),
        (Firm, {"reinvestment_rate": -0.1}),
        (Firm, {"depreciation_rate": 1}),
        (Firm, {"depreciation_rate": float("nan")}),
        (Firm, {"theta": 0}),
    ],
)
def test_unsupported_settings_are_rejected(factory, settings):
    with pytest.raises(ValueError):
        factory(**settings)


@pytest.mark.parametrize(
    "households",
    [
        (),
        (Household("A"), Household("A")),
        (Household("Firm"),),
        (Household("A", money=0), Household("B", money=0)),
    ],
)
def test_population_requires_unique_names_and_positive_aggregate_money(households):
    with pytest.raises(ValueError):
        advance_investment_period(households, Firm())


def test_out_of_range_arithmetic_fails_without_changing_prior_snapshot():
    households = (Household("A"), Household("B"))
    first = advance_investment_period(households, Firm())
    original = investment_report((first,))
    with pytest.raises(ValueError, match="numerical range"):
        advance_investment_period(
            (Household("A", money=1e308), Household("B", money=1e308)),
            Firm(money=1e308),
        )
    invalid = replace(first, capital_close=float("inf"))
    with pytest.raises(ValueError, match="finite"):
        advance_investment_period(households, first.firm, invalid)
    assert investment_report((first,)) == original


def test_snapshot_and_settings_remain_fixed_while_reports_are_plain_copies():
    draft = default_households()
    households = tuple(Household(**entry) for entry in draft)
    firm = Firm(**default_firm())
    first = advance_investment_period(households, firm)
    draft[0]["money"] = 50
    with pytest.raises(FrozenInstanceError):
        first.firm.capital = 50
    with pytest.raises(TypeError):
        first.closing_cash[households[0].name] = 50
    report = investment_report((first,))
    report["households"][0]["parameters"]["scores"]["consumption"] = 50
    report["firm"]["parameters"]["capital"] = 50
    fresh = investment_report((first,))
    assert fresh["households"][0]["parameters"]["scores"]["consumption"] == 1
    assert fresh["firm"]["parameters"]["capital"] == 1
    assert first.opening_cash[households[0].name] == 1


def test_run_context_and_full_evidence_export_are_serializable_and_precise():
    first = advance_investment_period((Household("A"), Household("B")), Firm())
    second = advance_investment_period(first.households, first.firm, first)
    run = Economy09Run(second, first, 7)
    decoded = json.loads(json.dumps(run.context(0), allow_nan=False))
    assert decoded["model"] == "investment_growth"
    assert decoded["previous_period"] == 1
    assert decoded["revision"] == 7
    assert decoded["selected_transfer"]["kind"] == "dividend"
    assert run.context(999)["selected_transfer"] is None
    report = investment_report((first, second), cumulative=True)
    rows = report["rows"]
    fieldnames = list(dict.fromkeys(key for row in rows for key in row))
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    exported = list(csv.DictReader(io.StringIO(output.getvalue())))
    assert {row["record_type"] for row in exported} == {"account", "event", "transfer"}
    firm_row = next(row for row in exported if row["account_type"] == "firm")
    assert float(firm_row["production_value"]) == first.production_value
    assert float(firm_row["investment_quantity"]) == first.investment_quantity
    assert float(firm_row["capital_value_open"]) == first.capital_value_open
    assert "current_profit" not in fieldnames and "profit" not in fieldnames
    for row in exported:
        if row["record_type"] == "transfer":
            assert row["sender_id"] and row["receiver_id"] and row["unit"]
        elif row["record_type"] == "event":
            assert row["entity_id"] and row["unit"] and row["valuation_price"]


def test_cumulative_scope_rejects_missing_duplicate_or_mixed_periods():
    first = advance_investment_period((Household("A"), Household("B")), Firm())
    second = advance_investment_period(first.households, first.firm, first)
    third = advance_investment_period(first.households, first.firm, second)
    different = advance_investment_period(first.households, Firm(capital=2))
    for periods in ((first, third), (first, first), (first, different)):
        with pytest.raises(ValueError):
            investment_report(periods, cumulative=True)
    with pytest.raises(ValueError):
        investment_report(())
