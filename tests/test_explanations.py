"""Built-in explanations retain the actual scope and model assumptions."""
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
