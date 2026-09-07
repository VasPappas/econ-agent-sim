"""The result adapter must faithfully serialize the engine's records."""

import json

from econ_agent_sim.economy_0_4 import run_economy_0_4
from econ_agent_sim.playground import playground_data


def test_payload_matches_model_trade_and_balance_records():
    result = run_economy_0_4()
    payload = playground_data(result, 0, 0)
    json.dumps(payload, allow_nan=False)
    assert payload["opening"] == result.periods[0].opening_stocks
    assert payload["closing"] == result.periods[0].closing_stocks
    assert payload["trades"][0]["payment"] == result.trades[0].payment
    assert all(payload["checks"].values())
