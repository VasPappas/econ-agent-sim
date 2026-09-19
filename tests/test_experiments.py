"""Whole-plan replay, strict file validation and atomic workspace restoration."""

import json
from dataclasses import asdict, fields
from pathlib import Path

import pytest

from econ_agent_sim import experiments, workspace
from econ_agent_sim.domain import ENGINE_VERSION, MAX_PERIODS, MODEL_ID, Settings
from econ_agent_sim.engine import SimulationError, simulate
from econ_agent_sim.experiments import (
    FORMAT,
    FORMAT_VERSION,
    MAX_FILE_BYTES,
    Baseline,
    Experiment,
    ExperimentError,
    RetiredExperimentError,
    dump_experiment,
    dumps_experiment,
    load_experiment,
    restore_experiment,
)
from econ_agent_sim.monetary_growth import Period


@pytest.fixture(scope="module")
def run():
    return simulate(Settings())


@pytest.fixture
def draft_payload():
    return json.loads(dump_experiment(Experiment("My experiment", Settings())))


@pytest.fixture
def payload(run):
    return json.loads(dump_experiment(
        Experiment("Active", Settings(beta=.9), run, 11, 3, "Cumulative", "Ask why"),
        baseline=Baseline(run, 7, "Baseline"),
    ))


def test_roundtrip_preserves_active_draft_baseline_and_navigation(payload, run):
    encoded = json.dumps(payload).encode()
    restored = load_experiment(encoded)
    assert restored.current.draft == Settings(beta=.9)
    assert restored.current.run == run
    assert restored.current.run.settings == Settings()
    assert restored.current.visible_periods == 11
    assert restored.current.selected_period == 3
    assert restored.current.scope == "Cumulative" and restored.current.view == "Ask why"
    assert restored.baseline == Baseline(run, 7, "Baseline")
    assert len(payload["current"]["run"]["periods"]) == MAX_PERIODS
    assert payload["format_version"] == FORMAT_VERSION == 6
    assert payload["engine_version"] == ENGINE_VERSION
    assert payload["model"] == MODEL_ID


def test_draft_only_roundtrip_does_not_solve(monkeypatch, draft_payload):
    def unexpected(_):
        pytest.fail("A draft-only file must not be simulated.")

    monkeypatch.setattr(experiments, "simulate", unexpected)
    restored = load_experiment(json.dumps(draft_payload))
    assert restored.current == Experiment("My experiment", Settings())
    assert restored.baseline is None


def test_full_workspace_remains_within_file_limit(run):
    current = Experiment("α" * 80, Settings(), run, 100, 100)
    encoded = dump_experiment(current, baseline=Baseline(run, 100, "β" * 80))
    assert len(encoded) < MAX_FILE_BYTES
    assert load_experiment(encoded).current == current


def test_session_roundtrip_with_different_editable_inputs(payload):
    state = {"unrelated": "keep"}
    workspace.initialize(state)
    assert restore_experiment(state, json.dumps(payload))
    assert state["unrelated"] == "keep"
    assert state["te_view"] == "Ask why"
    assert state["te_draft"].beta == .9 and state["te_run"].settings.beta == .95
    saved = json.loads(dumps_experiment(state))
    assert saved == payload
    old_run = state["te_run"]
    assert workspace.advance(state, 10)
    assert state["te_visible_periods"] == 21 and state["te_run"] is old_run


@pytest.mark.parametrize("version", [1, 2, 3, 4, 5])
def test_earlier_economies_are_explicitly_rejected(version):
    with pytest.raises(RetiredExperimentError, match="earlier Tiny Economy model"):
        load_experiment(json.dumps({"format": FORMAT, "format_version": version}))


def test_released_format5_fixture_is_rejected():
    path = Path(__file__).parent / "fixtures" / "retired_format5_experiment.json"
    with pytest.raises(RetiredExperimentError):
        load_experiment(path.read_bytes())


@pytest.mark.parametrize("field,value", [
    ("format", "other"), ("format_version", True), ("format_version", 6.0),
    ("format_version", 7), ("model", "tiny_economy"),
    ("engine_version", "tiny-economy-3.0.0"),
])
def test_identity_version_and_engine_must_match(draft_payload, field, value):
    draft_payload[field] = value
    with pytest.raises(ExperimentError):
        load_experiment(json.dumps(draft_payload))


@pytest.mark.parametrize("field", [field.name for field in fields(Settings)])
@pytest.mark.parametrize("value", [True, False, "0.95", None, float("inf"), float("nan")])
def test_saved_inputs_are_finite_numbers_not_boolean_or_strings(draft_payload, field, value):
    draft_payload["current"]["draft"][field] = value
    with pytest.raises(ExperimentError):
        load_experiment(json.dumps(draft_payload))


@pytest.mark.parametrize("field,value", [
    ("visible_periods", True), ("visible_periods", 1.0), ("visible_periods", 101),
    ("visible_periods", 0), ("selected_period", True), ("selected_period", 0),
    ("selected_period", 12), ("selected_period", 1.0),
    ("scope", "All"), ("view", "Other"), ("name", ""),
    ("name", "bad\nname"), ("name", "\ud800"), ("name", "x" * 81),
])
def test_invalid_navigation_and_names_are_rejected(payload, field, value):
    payload["current"][field] = value
    with pytest.raises(ExperimentError):
        load_experiment(json.dumps(payload))


@pytest.mark.parametrize("extra", [True, False])
@pytest.mark.parametrize("section", ["root", "current", "draft", "run", "period", "baseline"])
def test_unknown_and_missing_fields_are_rejected(payload, section, extra):
    containers = {
        "root": payload, "current": payload["current"],
        "draft": payload["current"]["draft"], "run": payload["current"]["run"],
        "period": payload["current"]["run"]["periods"][0], "baseline": payload["baseline"],
    }
    container = containers[section]
    if extra:
        container["unexpected"] = 1
    else:
        del container[next(iter(container))]
    with pytest.raises(ExperimentError):
        load_experiment(json.dumps(payload))


@pytest.mark.parametrize("data", [
    b"", b"not json", b"null", b"[]", b"{", b"\xff", b"{}",
    '["' + "x" * MAX_FILE_BYTES + '"]',
    "[" * 1500 + "0" + "]" * 1500,
    '{"format":"tiny-economy-experiment","format":"duplicate"}',
    '{"number":NaN}', '{"number":Infinity}',
])
def test_malformed_oversized_or_nonfinite_files_are_rejected(data):
    with pytest.raises(ExperimentError):
        load_experiment(data)


def test_utf8_byte_limit_applies_to_unicode_text():
    data = '"' + "α" * (MAX_FILE_BYTES // 2) + '"'
    assert len(data) < MAX_FILE_BYTES and len(data.encode()) > MAX_FILE_BYTES
    with pytest.raises(ExperimentError, match="256 KiB"):
        load_experiment(data)


@pytest.mark.parametrize("count", [0, 1, 99, 101])
def test_saved_run_requires_entire_plan(payload, count):
    rows = payload["current"]["run"]["periods"]
    payload["current"]["run"]["periods"] = (rows + [rows[-1]])[:count]
    with pytest.raises(ExperimentError, match="complete 100-period plan"):
        load_experiment(json.dumps(payload))


@pytest.mark.parametrize("value", [True, 1.0, 0, 2])
def test_period_numbers_are_exact_consecutive_integers(payload, value):
    payload["current"]["run"]["periods"][0]["number"] = value
    with pytest.raises(ExperimentError, match="numbered consecutively"):
        load_experiment(json.dumps(payload))


@pytest.mark.parametrize("field", [field.name for field in fields(Period) if field.name != "number"])
def test_every_saved_quantity_is_checked_against_replay(payload, field):
    payload["current"]["run"]["periods"][-1][field] += .001
    with pytest.raises(ExperimentError, match="could not be reproduced"):
        load_experiment(json.dumps(payload))


@pytest.mark.parametrize("value", [True, False, None, "1", 1e309])
def test_saved_period_values_reject_nonfinite_non_numeric_values(payload, value):
    payload["current"]["run"]["periods"][0]["capital"] = value
    with pytest.raises(ExperimentError):
        load_experiment(json.dumps(payload))


def test_small_rounding_difference_is_accepted_but_never_installed(payload, run):
    saved = payload["current"]["run"]["periods"][-1]
    saved["capital"] += 1e-12
    restored = load_experiment(json.dumps(payload))
    assert restored.current.run.periods == run.periods
    assert restored.current.run.periods[-1].capital != saved["capital"]


def test_mutated_active_settings_without_matching_plan_are_rejected(payload):
    payload["current"]["run"]["settings"]["beta"] = .9
    with pytest.raises(ExperimentError, match="could not be reproduced"):
        load_experiment(json.dumps(payload))


def test_entire_baseline_schema_is_validated_before_any_solve(payload, monkeypatch):
    calls = []
    monkeypatch.setattr(experiments, "simulate", lambda settings: calls.append(settings))
    payload["baseline"]["run"]["periods"][-1]["capital"] = True
    with pytest.raises(ExperimentError):
        load_experiment(json.dumps(payload))
    assert calls == []


def test_bad_baseline_after_good_current_replay_cannot_partially_replace_state(payload, run):
    state = {}
    workspace.initialize(state)
    state.update(
        te_name="Existing", te_run=run, te_visible_periods=21, te_selected_period=8,
        te_draft=Settings(beta=.8), te_scope="Cumulative", te_view="Ask why",
        te_baseline=Baseline(run, 4, "Kept"),
    )
    snapshot = dict(state)
    payload["baseline"]["run"]["periods"][-1]["firm_cash"] += .1
    assert not restore_experiment(state, json.dumps(payload))
    assert {key: value for key, value in state.items() if key != "te_error"} == {
        key: value for key, value in snapshot.items() if key != "te_error"
    }
    assert "could not be reproduced" in state["te_error"]


def test_replay_solver_failure_is_atomic(payload, monkeypatch):
    state = {}
    workspace.initialize(state)
    state["te_name"] = "Do not replace"
    snapshot = dict(state)

    def fail(_):
        raise SimulationError("This regime is not supported.")

    monkeypatch.setattr(experiments, "simulate", fail)
    assert not restore_experiment(state, json.dumps(payload))
    assert {key: value for key, value in state.items() if key != "te_error"} == {
        key: value for key, value in snapshot.items() if key != "te_error"
    }


@pytest.mark.parametrize("visible", [True, 0, 101, 1.0])
def test_baseline_visible_count_is_strict(payload, visible):
    payload["baseline"]["visible_periods"] = visible
    with pytest.raises(ExperimentError):
        load_experiment(json.dumps(payload))


def test_baseline_requires_a_completed_run(payload):
    payload["baseline"]["run"] = None
    with pytest.raises(ExperimentError, match="completed plan"):
        load_experiment(json.dumps(payload))


def test_setting_snapshot_has_no_legacy_hidden_parameters(run):
    payload = json.loads(dump_experiment(Experiment("Current", Settings(), run, 1)))
    assert set(payload["current"]["run"]["settings"]) == set(asdict(Settings()))
    assert len(payload["current"]["run"]["settings"]) == 6
