"""Tutor explanations use the same settled Economy 0.8 accounts."""

from econ_agent_sim.economy_0_8 import (
    Economy08Run,
    Firm,
    Household,
    advance_firm_period,
)
from econ_agent_sim.experiment_chat import INSTRUCTIONS
from econ_agent_sim.explanations import built_in_explanations


def baseline_periods():
    households = (Household("Household 1"), Household("Household 2"))
    firm = Firm()
    first = advance_firm_period(households, firm)
    second = advance_firm_period(households, firm, first)
    return first, second


def test_firm_explanations_cover_prices_work_profit_and_money():
    first, _ = baseline_periods()
    context = Economy08Run(first, None, 1).context()
    answers = built_in_explanations(context)

    assert "How were the wage and price found?" in answers
    assert "Why did households work this much?" in answers
    assert "Where did the profit go?" in answers
    assert "Was any money created?" in answers
    assert "representative price-taking producer" in answers["Why is there only one firm?"]
    assert f"{first.wage:.4f}" in answers["How were the wage and price found?"]
    assert "there was none in Period 1" in answers["Where did the profit go?"]


def test_firm_explanations_distinguish_prior_dividend_and_selected_transfer():
    first, second = baseline_periods()
    run = Economy08Run(second, first, 2)
    dividend_index = next(
        index
        for index, transfer in enumerate(second.transfers)
        if transfer.kind == "dividend"
    )
    answers = built_in_explanations(run.context(dividend_index))

    assert "Explain this transfer" in answers
    assert "dividend" in answers["Explain this transfer"]
    assert f"{first.profit:.4f}" in answers["Where did the profit go?"]
    assert "start of the next period" in answers["Where did the profit go?"]


def test_ai_tutor_contract_includes_firm_wage_model_boundaries():
    assert "When model is firms_wages (Economy 0.8)" in INSTRUCTIONS
    assert "cannot borrow" in INSTRUCTIONS
    assert "representative price-taking firm" in INSTRUCTIONS
    assert "start of the next period" in INSTRUCTIONS.lower()
