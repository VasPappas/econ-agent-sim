"""The tutor retains displayed scope and both firms within its existing budget."""

import json
from dataclasses import replace

from econ_agent_sim.competition_comparison import compare_competition_runs
from econ_agent_sim.competition_explanations import (
    amount,
    competition_context,
    competition_explanations,
)
from econ_agent_sim.competition_reporting import competition_report
from econ_agent_sim.economy_1_0 import (
    Firm,
    Household,
    advance_competition_period,
    default_firms,
    default_households,
)


def setup(count=2):
    return (
        tuple(Household(**item) for item in default_households(count)),
        tuple(Firm(**item) for item in default_firms()),
    )


def test_cumulative_answers_keep_firm_dividends_and_rates_in_selected_period():
    households, firms = setup()
    firms = (replace(firms[0], capital=100, depreciation_rate=.9), firms[1])
    first = advance_competition_period(households, firms)
    second = advance_competition_period(households, firms, first)
    report = competition_report((first, second), cumulative=True)
    answers = competition_explanations(second, report)
    assert "After Period 2" in answers["Who receives each firm's dividends?"]
    for account in second.firm_accounts.values():
        assert (
            f"{account.name}: {amount(account.next_dividend_budget)} Money"
            in answers["Who receives each firm's dividends?"]
        )
    assert "In Period 2" in answers["What can a wage buy?"]
    assert report["label"] in answers["Why did capital change?"]
    assert "sum" in answers["How should I read cumulative results?"]


def test_context_preserves_both_firms_and_households_at_maximum_population():
    households, firms = setup(20)
    households = tuple(replace(
        household, name=f"Household {index:02d} " + "a" * 66,
        money=2.31 + index / 23,
        consumption_priority=3.123 + index / 19,
        money_priority=2.154 + index / 17,
        leisure_priority=1.331 + index / 29,
    ) for index, household in enumerate(households))
    history = []
    for _ in range(3):
        history.append(advance_competition_period(
            households, firms, history[-1] if history else None,
        ))
    report = competition_report(history, cumulative=True)
    context = competition_context(history[-1], report, 1)
    encoded = json.dumps(context, allow_nan=False, separators=(",", ":"))
    assert len(encoded) < 35000
    assert {"rows", "transfers", "events"}.isdisjoint(context["report"])
    household_table = context["report"]["households"]
    restored = [dict(zip(household_table["columns"], values))
                for values in household_table["values"]]
    assert restored == [
        {key: value for key, value in household.items()
         if key not in {"firms", "parameters"}}
        for household in report["households"]
    ]
    parameters = context["report"]["household_parameters"]
    by_id = {row["entity_id"]: row for row in (
        dict(zip(parameters["columns"], values)) for values in parameters["values"]
    )}
    for household in report["households"]:
        row = by_id[household["entity_id"]]
        for key, value in household["parameters"]["scores"].items():
            assert row[f"{key}_score"] == value
        for key, value in household["parameters"]["weights"].items():
            assert row[f"{key}_weight"] == value
    assert context["report"]["firms"] == [
        {key: value for key, value in firm.items() if key != "allocations"}
        for firm in report["firms"]
    ]
    assert len(context["report"]["household_firm_allocations"]["values"]) == 40


def test_comparison_context_fits_without_losing_changed_settings():
    households, firms = setup(20)
    baseline = advance_competition_period(households, firms)
    changed_households = tuple(replace(
        household, name="世" * 78 + str(index), money=2.31 + index / 23,
        consumption_priority=3.123 + index / 19,
        money_priority=2.154 + index / 17,
        leisure_priority=1.331 + index / 29,
    ) for index, household in enumerate(households))
    changed_firms = tuple(replace(
        firm, money=2.71, capital=.83, productivity=3.14,
        reinvestment_rate=.2, depreciation_rate=.05,
    ) for firm in firms)
    current = advance_competition_period(changed_households, changed_firms)
    comparison = compare_competition_runs((current,), (baseline,), selected_period=1)
    context = competition_context(
        current, competition_report(current), 2, comparison=comparison,
    )
    compact = context["baseline_comparison"]
    assert compact["metrics"] == comparison["metrics"]
    assert compact["firms"] == comparison["firms"]
    restored = []
    names = {item.id: item.name for item in (*changed_households, *changed_firms)}
    for entity in compact["changed_settings"]:
        settings = entity["changes"]
        restored.extend({
            "entity_id": entity["entity_id"],
            "entity": entity.get("entity", names.get(entity["entity_id"])),
            **dict(zip(settings["columns"], values)),
        } for values in settings["values"])
    assert restored == comparison["settings_changes"]
    assert len(json.dumps(
        context, allow_nan=False, separators=(",", ":"), ensure_ascii=False,
    )) < 35000
