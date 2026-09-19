"""Explanations disclose the actual dynamic model and selected results."""

import pytest

from econ_agent_sim.domain import Settings
from econ_agent_sim.engine import simulate
from econ_agent_sim.explanations import MODEL_PASSPORT, QUESTIONS, amount, explain


@pytest.fixture(scope="module")
def run():
    return simulate(Settings())


def test_all_questions_answer_selected_period_and_cumulative_scope(run):
    assert len(QUESTIONS) == len(set(QUESTIONS))
    for cumulative in (False, True):
        for question in QUESTIONS:
            answer = explain(question, run, 3, cumulative)
            assert isinstance(answer, str) and len(answer) > 50
    answer = explain("How should I read cumulative results?", run, 3, True)
    assert "Periods 1–3" in answer
    assert "original period price" in answer
    assert "stocks are never summed" in answer
    investment = explain("How do firms choose investment?", run, 3, True)
    assert "Period 3" in investment
    assert amount(run.periods[2].investment) in investment


def test_passport_discloses_forward_plans_restrictions_and_unsupported_regime(run):
    assert explain("What does this model assume?", run, 1) == MODEL_PASSPORT
    for phrase in ("infinite horizon", "perfect-foresight", "unspent opening cash",
                   "textbook", "before sales", "not a simulation of learning"):
        assert phrase in MODEL_PASSPORT
    assert "do not forecast" not in MODEL_PASSPORT
    assert "calibrated forecast" in MODEL_PASSPORT


def test_explanations_match_dated_book_accounting_and_no_double_counting(run):
    answer = explain("Why are profit, cash and capital value different?", run, 2)
    assert "previous period’s price" in answer
    assert "holding gain or loss, never cash" in answer
    assert "profit minus dividends plus holding gains" in answer
    ownership = explain("Who owns the firms?", run, 2)
    assert "50% of each firm" in ownership
    assert "eliminating the duplicate ownership claims" in ownership
    assert "not a traded share price" in ownership


def test_payment_explanation_uses_actual_selected_period_amounts(run):
    row = run.periods[3]
    answer = explain("How do payments stay funded?", run, 4, True)
    for value in (row.firm_cash, row.distribution, row.money_wage * row.labor,
                  row.goods_price * row.consumption):
        assert amount(value) in answer
    assert "Period 4" in answer
    assert "Total cash remains 1 Money" in answer


def test_no_unsupported_claim_of_adjustment_or_self_regulation(run):
    answer = explain("Does this show a self-regulating economy?", run, 1)
    assert "not proof" in answer
    assert "trial and error" in answer
    failure = explain("Why can a set of settings be unsupported?", run, 1)
    assert "explicitly unsupported" in failure
    assert "Numerical convergence can also fail" in failure
    assert "economic collapse" in failure


def test_boundary_description_does_not_make_dividends_a_profit_cap(run):
    answer = explain("Why can investment or dividends be zero?", run, 1)
    assert "need not equal current or previous accounting profit" in answer
    assert "cannot sell their installed capital" in answer


def test_explanations_reject_unknown_question_and_invalid_date(run):
    with pytest.raises(ValueError):
        explain("Invent a new forecast", run, 1)
    with pytest.raises(ValueError):
        explain(QUESTIONS[0], run, 101)


def test_amount_keeps_true_zeros_distinct_from_small_nonzero_values():
    assert amount(0) == "0.0000"
    assert amount(1e-9) == "1.000e-09"
    assert amount(-1e-8) == "-1.000e-08"
