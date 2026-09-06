import json
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock, patch

import pytest

from econ_agent_sim.economy_0_3 import redistribute_y
from econ_agent_sim.economy_0_4 import Economy04Config, run_economy_0_4
from econ_agent_sim.experiment_chat import (
    ChatUnavailable,
    answer_question,
    context_id,
    experiment_context,
    reserve_request,
    validate_chat_target,
)


def experiment():
    config = Economy04Config()
    population = config.period_populations[0]
    changed = redistribute_y(
        population,
        sender_name=population[0].name,
        receiver_name=population[1].name,
        amount=0.1,
    )
    return run_economy_0_4(Economy04Config(period_populations=(population, changed)))


def test_context_tracks_selected_experiment_and_real_trade():
    result = experiment()
    baseline = experiment_context(result, 0)
    changed = experiment_context(result, 1, 5)
    assert baseline["agents"][0]["opening"]["Y"] == result.periods[0].population[0].y
    assert changed["agents"][0]["opening_Y_change_from_previous"] == pytest.approx(-0.1)
    assert changed["selected_trade"]["ordinal"] == 6
    assert changed["selected_trade"]["trade_id"] == result.periods[1].trades[5].trade_id
    assert changed["previous_prices"] == result.periods[0].prices
    assert changed["prices"]["Y"] == 1
    assert baseline["selected_trade"] is None
    assert context_id(baseline) != context_id(changed)


def test_untrusted_trade_selection_rejects_stale_and_invalid_context():
    valid = {"id": "event", "revision": 3, "selected_index": 1, "trade_index": 5}
    assert validate_chat_target(valid, 3, 1, 18)
    for field, value in [
        ("revision", 2),
        ("trade_index", -1),
        ("trade_index", 18),
        ("trade_index", True),
        ("selected_index", 0),
        ("id", ""),
    ]:
        assert not validate_chat_target({**valid, field: value}, 3, 1, 18)


def test_budget_is_shared_atomic_and_expires(tmp_path):
    path = tmp_path / "budget.db"

    def attempt(i):
        try:
            reserve_request(path, str(i), daily_limit=5, now=100000)
            return True
        except ChatUnavailable:
            return False

    with ThreadPoolExecutor(max_workers=8) as pool:
        assert sum(pool.map(attempt, range(12))) == 5
    reserve_request(path, "new", daily_limit=5, now=200000)


def test_budget_cooldown_and_session_limits(tmp_path):
    path = tmp_path / "budget.db"
    reserve_request(path, "same", now=100000)
    with pytest.raises(ChatUnavailable, match="few seconds"):
        reserve_request(path, "same", now=100001)
    for i in range(1, 20):
        reserve_request(path, "same", now=100000 + i * 6)
    with pytest.raises(ChatUnavailable, match="session"):
        reserve_request(path, "same", now=100200)


def request_args(tmp_path):
    return {
        "api_key": "test-secret-never-a-real-key",
        "budget_path": tmp_path / "b.db",
        "session_id": "test",
    }


def fake_connection(status=200, body=None):
    connection = MagicMock()
    response = connection.getresponse.return_value
    response.status = status
    response.read.return_value = json.dumps(
        body
        or {
            "status": "completed",
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": "Y is fixed at 1."}],
                }
            ],
        }
    ).encode()
    return connection


def test_api_sends_bounded_context_and_no_tools_or_remote_storage(tmp_path):
    connection = fake_connection()
    history = [{"role": "user", "content": "Previous question"}] * 10
    with patch(
        "econ_agent_sim.experiment_chat.http.client.HTTPSConnection",
        return_value=connection,
    ) as factory:
        answer = answer_question(
            "Why?",
            experiment_context(experiment(), 1),
            history,
            **request_args(tmp_path),
        )
    assert answer == "Y is fixed at 1."
    factory.assert_called_once_with("api.openai.com", timeout=30)
    payload = json.loads(connection.request.call_args.kwargs["body"])
    assert payload["store"] is False
    assert "tools" not in payload
    assert payload["max_output_tokens"] == 800
    assert len(payload["input"]) == 8
    assert "test-secret" not in json.dumps(payload)
    connection.close.assert_called_once()


@pytest.mark.parametrize("status", [401, 429, 500, 302])
def test_api_errors_are_safe_and_never_retried(tmp_path, status):
    connection = fake_connection(status=status)
    with patch(
        "econ_agent_sim.experiment_chat.http.client.HTTPSConnection",
        return_value=connection,
    ), pytest.raises(ChatUnavailable) as caught:
        answer_question("Why?", {}, [], **request_args(tmp_path))
    assert "test-secret" not in str(caught.value)
    connection.request.assert_called_once()


def test_missing_key_and_invalid_question_never_call_api(tmp_path):
    with patch("econ_agent_sim.experiment_chat.http.client.HTTPSConnection") as call:
        args = request_args(tmp_path)
        with pytest.raises(ChatUnavailable):
            answer_question("Why?", {}, [], **{**args, "api_key": ""})
        with pytest.raises(ChatUnavailable):
            answer_question("a" * 1201, {}, [], **args)
        call.assert_not_called()


def test_incomplete_response_is_not_presented_as_an_answer(tmp_path):
    connection = fake_connection(body={"status": "incomplete", "output": []})
    with patch(
        "econ_agent_sim.experiment_chat.http.client.HTTPSConnection",
        return_value=connection,
    ), pytest.raises(ChatUnavailable, match="completed"):
        answer_question("Why?", {}, [], **request_args(tmp_path))
