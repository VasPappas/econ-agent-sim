"""The tutor receives work choices, not the previous chapter's fixed-output story."""

import json
from unittest.mock import MagicMock, patch

from econ_agent_sim.economy_0_7 import WorkAgent, WorkRun, advance_work_period
from econ_agent_sim.experiment_chat import INSTRUCTIONS, answer_question
from econ_agent_sim.explanations import built_in_explanations


def test_work_explanations_cover_actual_choices_without_fixed_output_claims():
    population = (WorkAgent("A", money=100, leisure=.9), WorkAgent("B"))
    first = advance_work_period(population)
    second = advance_work_period(population, first)
    context = WorkRun(second, first, 1).context(0)
    answers = built_in_explanations(context)
    work = answers["Why did agents choose this much work?"]
    for agent in population:
        assert f"{agent.name}: work {100 * second.effort[agent.name]:.1f}%" in work
    assert "weight" in work and "not the fraction" in work
    assert "Compared with Period 1" in answers["Why did the price move?"]
    assert "Work costs leisure" in answers["What happens each period?"]
    assert "Money divided by the price of X" in answers["Why keep money instead of consuming more?"]
    assert "Period 2, trade" in answers["Explain this trade"]
    text = " ".join(answers.values())
    for stale in ("fixed quantity", "Production is automatic", "no work decision", "Y is the reference"):
        assert stale not in text
    baseline = advance_work_period((WorkAgent("A"), WorkAgent("B")))
    baseline_answers = built_in_explanations(WorkRun(baseline, None, 1).context())
    assert "works 50%" in baseline_answers["Why is there no trade?"]
    assert "exactly ⅓" in baseline_answers["Why did agents choose this much work?"]


def test_twenty_agent_work_context_fits_tutor_and_keeps_actual_period_data(tmp_path):
    population = tuple(WorkAgent(f"Agent {i + 1}", x=.13*i, money=.2*(20-i),
                                 alpha=.1+.04*i, productivity=.3*(i+1), leisure=.1+.04*i)
                       for i in range(20))
    first = advance_work_period(population)
    second = advance_work_period(population, first)
    context = WorkRun(second, first, 1).context(0)
    assert len(json.dumps(context, separators=(",", ":"), allow_nan=False).encode()) <= 35000
    connection = MagicMock()
    response = connection.getresponse.return_value
    response.status = 200
    response.read.return_value = json.dumps({"status": "completed", "output": [
        {"type": "message", "content": [{"type": "output_text", "text": "Work costs leisure."}]}]
    }).encode()
    with patch("econ_agent_sim.experiment_chat.http.client.HTTPSConnection", return_value=connection):
        assert answer_question("Why this much work?", context, [], api_key="test-key",
                               budget_path=tmp_path / "budget.db", session_id="work-test") == "Work costs leisure."
    payload = json.loads(connection.request.call_args.kwargs["body"])
    sent = json.loads(payload["input"][0]["content"].removeprefix("Experiment data: "))
    assert sent == context
    assert sent["settings"]["agents"][0]["leisure"] == population[0].leisure
    assert sent["effort"] == second.effort
    assert sent["period_opening"] == first.closing_stocks
    assert payload["store"] is False and "tools" not in payload
    work_rules = INSTRUCTIONS.split("When model is work_leisure (Economy 0.7):")[1].split(
        "The following two-good rules", 1)[0]
    for concept in ("piecewise-linear", "zero work", "not a money fee", "planning future purchases",
                    "exactly 1/3", "Production is endogenous", "all posttrade X"):
        assert concept in work_rules
