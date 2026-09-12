"""Keep explanations aligned with actual scope and the economic payout rule."""

import json
from dataclasses import replace

from econ_agent_sim.economy_0_9 import (
    Firm,
    Household,
    advance_investment_period,
    investment_report,
)
from econ_agent_sim.investment_comparison import compare_investment_runs
from econ_agent_sim.investment_explanations import (
    amount,
    investment_context,
    investment_explanations,
)


def test_cumulative_explanation_keeps_next_dividend_as_one_future_budget():
    households = (Household("A"), Household("B"))
    first = advance_investment_period(households, Firm())
    second = advance_investment_period(households, Firm(), first)
    report = investment_report((first, second), cumulative=True)
    answers = investment_explanations(second, report)
    profit = answers["Why are profit, cash and dividends different?"]
    assert "Periods 1–2" in profit
    assert amount(first.net_operating_profit + second.net_operating_profit) in profit
    assert f"After Period 2, the next dividend budget is {amount(second.next_dividend_budget)}" in profit
    assert "past losses" in profit.lower()
    assert "do not block" in profit
    wages = answers["What can a wage buy?"]
    assert f"In Period 2, one full unit of work earns {amount(second.wage)}" in wages


def test_chat_context_is_json_serializable_and_bounded_at_maximum_population():
    households = tuple(Household(f"Household {i}") for i in range(20))
    periods = []
    for _ in range(3):
        periods.append(advance_investment_period(
            households, Firm(), periods[-1] if periods else None,
        ))
    report = investment_report(tuple(periods), cumulative=True)
    context = investment_context(periods[-1], report, 4)
    encoded = json.dumps(context, allow_nan=False, separators=(",", ":"))
    assert len(encoded) < 35000
    assert context["report"]["firm"] == report["firm"]
    assert context["report"]["households"] == report["households"]
    assert "transfers" not in context["report"]
    assert "rows" not in context["report"]


def test_small_positive_and_negative_amounts_do_not_become_false_zero():
    assert amount(1e-12) == "1.000e-12"
    assert amount(-1e-12) == "-1.000e-12"
    assert amount(-0.0) == "0.0000"
    assert amount(.24999999999999975) == "0.2500"


def test_chat_comparison_uses_the_displayed_metrics_and_all_changed_settings():
    baseline = tuple(Household(f"Household {i}") for i in range(20))
    changed = tuple(replace(
        household, money=2.31 + i / 23, consumption_priority=3.123 + i / 19,
        money_priority=2.154 + i / 17, leisure_priority=1.331 + i / 29,
    ) for i, household in enumerate(baseline))
    old = advance_investment_period(baseline, Firm())
    new = advance_investment_period(changed, Firm(reinvestment_rate=.2))
    comparison = compare_investment_runs((new,), (old,), selected_period=1)
    context = investment_context(
        new, investment_report((new,)), 1, comparison=comparison,
    )
    assert context["baseline_comparison"]["metrics"] == comparison["metrics"]
    assert len(context["baseline_comparison"]["changed_settings"]) == 81
    assert len(json.dumps(context, separators=(",", ":")).encode()) < 35000
