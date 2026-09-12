"""Keep explanations aligned with actual scope and the economic payout rule."""

import json

from econ_agent_sim.economy_0_9 import (
    Firm,
    Household,
    advance_investment_period,
    investment_report,
)
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
