"""Target explanations retain actual scope, parameters and bounded context."""

import json
from dataclasses import replace

from econ_agent_sim.economy_1_1 import (
    Firm,
    Household,
    advance_target_period,
    default_firms,
    default_households,
)
from econ_agent_sim.target_comparison import compare_target_runs
from econ_agent_sim.target_explanations import target_context, target_explanations
from econ_agent_sim.target_reporting import target_report


def test_explanations_distinguish_targets_from_guarantees_and_shortfall_debt():
    households = tuple(Household(**item) for item in default_households())
    firms = tuple(Firm(**item) for item in default_firms())
    first = advance_target_period(households, firms)
    second = advance_target_period(households, firms, first)
    report = target_report((first, second), cumulative=True)
    answers = target_explanations(second, report)
    assert "not a guaranteed minimum" in answers["How does my consumption target work?"]
    assert "not a debt" in answers["How are shortfalls counted?"]
    assert "Periods 1–2" in answers["How are shortfalls counted?"]
    assert "0.50 X" in answers["Why did setting a target change nothing?"]
    assert "After Period 2" in answers["Who receives each firm's dividends?"]


def test_maximum_context_preserves_targets_and_changed_settings_within_allowance():
    households = tuple(Household(**item) for item in default_households(20))
    firms = tuple(Firm(**item) for item in default_firms())
    baseline = advance_target_period(households, firms)
    changed = tuple(replace(
        h, name="世" * 78 + str(i), money=2.31 + i / 23,
        consumption_priority=3.123 + i / 19,
        money_priority=2.154 + i / 17, leisure_priority=1.331 + i / 29,
        consumption_target=.123456789 + i / 7,
    ) for i, h in enumerate(households))
    changed_firms = tuple(replace(
        f, money=2.71, capital=.83, productivity=3.14,
        reinvestment_rate=.2, depreciation_rate=.05,
    ) for f in firms)
    period = advance_target_period(changed, changed_firms)
    comparison = compare_target_runs((period,), (baseline,), selected_period=1)
    report = target_report(period)
    context = target_context(period, report, 2, comparison=comparison)
    table = context["report"]["household_parameters"]
    values = [dict(zip(table["columns"], row)) for row in table["values"]]
    assert {v["entity_id"]: v["consumption_target"] for v in values} == {
        h.id: h.consumption_target for h in changed
    }
    assert context["model"] == "consumption_target"
    compact = context["baseline_comparison"]
    changes = compact["changed_settings"]
    fields = {field["id"]: field for field in compact["setting_fields"]}
    restored = []
    for row in changes["values"]:
        change = dict(zip(changes["columns"], row))
        field = fields[change.pop("field_id")]
        restored.append({**change, "label": field["label"], "unit": field["unit"]})
    assert restored == [
        {key: value for key, value in change.items() if key != "entity"}
        for change in comparison["settings_changes"]
    ]
    assert len(json.dumps(
        context, allow_nan=False, separators=(",", ":"), ensure_ascii=False,
    )) < 35000
