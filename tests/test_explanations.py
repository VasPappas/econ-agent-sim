"""Built-in explanations retain the actual scope and model assumptions."""
from dataclasses import replace

from econ_agent_sim.engine import (
    Firm,
    Household,
    advance_period,
    default_firms,
    default_households,
)
from econ_agent_sim.explanations import built_in_explanations
from econ_agent_sim.reporting import build_report


def test_explanations_distinguish_targets_from_guarantees_and_shortfall_debt():
    households = tuple(Household(**item) for item in default_households())
    firms = tuple(Firm(**item) for item in default_firms())
    first = advance_period(households, firms)
    second = advance_period(households, firms, first)
    report = build_report((first, second), cumulative=True)
    answers = built_in_explanations(second, report)
    assert "not a guaranteed minimum" in answers["How does my consumption target work?"]
    assert "not a debt" in answers["How are target gaps counted?"]
    assert "Periods 1–2" in answers["How are target gaps counted?"]
    assert "0.50 X" in answers["Why did setting a target change nothing?"]
    assert "After Period 2" in answers["Who receives each firm's dividends?"]
    selection = answers["Can there be more than one clearing price?"]
    assert "previous period's price" in selection
    assert "does not establish uniqueness" in selection


def test_model_passport_states_economic_assumptions_and_no_version_chapters():
    households = tuple(Household(**item) for item in default_households())
    firms = tuple(Firm(**item) for item in default_firms())
    period = advance_period(households, firms)
    answers = built_in_explanations(period, build_report(period))
    passport = answers["What does this model assume?"]
    assert "current period" in passport
    assert "do not forecast" in passport
    assert "before current sales" in passport
    assert "textbook" in passport and "custom" in passport
    assert all("Economy 1." not in answer for answer in answers.values())


def test_forward_looking_explanations_use_selected_decision_in_cumulative_report():
    households = tuple(Household(**item) for item in default_households())
    firms = tuple(
        replace(Firm(**item), investment_policy="user_cost")
        for item in default_firms()
    )
    first = advance_period(households, firms)
    second = advance_period(households, firms, first)
    report = build_report((first, second), cumulative=True)
    answers = built_in_explanations(second, report)
    policy = answers["How do the investment policies differ?"]
    assert "maximum investment budget" in policy
    assert "not paid interest" in policy
    assert "current-period choices" in policy
    decision_answer = answers["Why did firms choose this investment?"]
    assert "Period 2" in decision_answer
    assert "Forecasts are not summed" in decision_answer
    assert "not a mandatory minimum" in decision_answer
    for firm in report["firms"]:
        decision = firm["investment_decision"]
        source = second.solution["investment_decisions"][firm["entity_id"]]
        assert decision["period"] == 2
        assert decision["scope"] == "selected_period"
        assert decision["investment_quantity"] == source["investment_quantity"]
        assert decision["investment_budget_quantity"] == source["investment_budget_quantity"]
        assert decision["replacement_quantity"] == second.firm_accounts[firm["entity_id"]].depreciation_quantity
        decision["investment_quantity"] = -1
        assert source["investment_quantity"] >= 0
