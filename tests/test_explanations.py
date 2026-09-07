from econ_agent_sim.economy_0_2 import canonical_population
from econ_agent_sim.economy_0_3 import redistribute_y
from econ_agent_sim.economy_0_4 import Economy04Config, run_economy_0_4
from econ_agent_sim.explanations import built_in_explanations


def test_explanation_tracks_both_directions_and_actual_trade():
    base = canonical_population()
    for sender, receiver, direction, share in [
        ("Agent 1", "Agent 2", "rose", "larger"),
        ("Agent 2", "Agent 1", "fell", "smaller"),
    ]:
        changed = redistribute_y(base, sender_name=sender, receiver_name=receiver, amount=.1)
        result = run_economy_0_4(Economy04Config(period_populations=(base, changed)))
        answers = built_in_explanations(result, 1, 5)
        price = answers["Why did X change but not Y?"]
        trade = result.periods[1].trades[5]
        assert direction in price
        assert share in price
        assert f"{result.periods[1].prices['X']:.4f}" in price
        assert "trade 6 of" in answers["Explain this trade"]
        assert f"{trade.quantity:.4f} {trade.good}" in answers["Explain this trade"]
        assert "100.0000 Money" in answers["Was any money created?"]


def test_baseline_explanation_does_not_invent_a_transfer():
    result = run_economy_0_4(Economy04Config(period_populations=(canonical_population(2),)))
    answers = built_in_explanations(result, 0)
    assert "no redistribution" in answers["Why did X change but not Y?"]
    assert "20.0000 Money" in answers["Was any money created?"]
    assert "Explain this trade" not in answers
