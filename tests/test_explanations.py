from econ_agent_sim.economy_0_4 import run_economy_0_4
from econ_agent_sim.explanations import built_in_explanations
from econ_agent_sim.run_workspace import SubmittedRun, default_agents, setup_config


def test_explanation_tracks_independent_price_changes_and_actual_trade():
    baseline = run_economy_0_4(setup_config(default_agents()))
    for quantity, direction in ((2.0, "fell"), (.5, "rose")):
        agents = default_agents()
        agents[0]["x"] = quantity
        result = run_economy_0_4(setup_config(agents))
        run = SubmittedRun(result, baseline, 2, 2)
        context = run.context(0)
        answers = built_in_explanations(context)
        price = answers["Why did the price move?"]
        trade = context["selected_trade"]
        assert direction in price
        assert f"{context['prices']['X']:.4f}" in price
        assert "trade 1 of" in answers["Explain this trade"]
        assert f"{trade['quantity']:.4f} {trade['good']}" in answers["Explain this trade"]
        assert "20.0000 Money" in answers["Was any money created?"]
        assert "redistribution" not in price


def test_first_run_and_unchanged_run_do_not_invent_changes():
    result = run_economy_0_4(setup_config(default_agents()))
    first = built_in_explanations(SubmittedRun(result, None, 1, 1).context())
    assert "first run" in first["Why did the price move?"]
    assert "Why is there no trade?" in first
    assert "Explain this trade" not in first
    repeat = built_in_explanations(SubmittedRun(result, result, 2, 2).context())
    assert "was unchanged" in repeat["Why did the price move?"]
