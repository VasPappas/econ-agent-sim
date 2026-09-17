"""Portable current experiments preserve drafts, histories and exact accounts."""

import json
from dataclasses import replace
from math import sqrt
from pathlib import Path

import pytest

from econ_agent_sim.engine import (
    Firm,
    Household,
    advance_period,
    default_firms,
    default_households,
)
from econ_agent_sim.experiments import (
    MAX_FILE_BYTES,
    Experiment,
    ExperimentError,
    RetiredExperimentError,
    _digest,
    dump_experiment,
    load_experiment,
)


def experiment(count=3):
    households = tuple(
        Household(**{**item, "consumption_target": 1.2345678912345})
        for item in default_households()
    )
    firms = tuple(Firm(**item) for item in default_firms())
    history = []
    for _ in range(count):
        history.append(advance_period(
            households, firms, history[-1] if history else None,
        ))
    return Experiment("My experiment", households, firms, tuple(history))


def test_roundtrip_preserves_dirty_draft_baseline_and_continuation():
    baseline = experiment()
    current = replace(
        baseline, name="Different target",
        draft_households=(replace(baseline.draft_households[0], consumption_target=0),
                          baseline.draft_households[1]),
        selected_period=2, report_scope="Cumulative", selected_firm="firm_b",
    )
    encoded = dump_experiment(current, baseline=baseline)
    payload = json.loads(encoded)
    assert (payload["model"], payload["engine_version"], payload["format_version"]) == (
        "tiny_economy", "tiny-economy-2.0.0", 4,
    )
    reopened = load_experiment(encoded)
    assert reopened.current == current
    assert reopened.baseline == baseline
    assert dump_experiment(reopened.current, baseline=reopened.baseline) == encoded
    restored_last = reopened.current.periods[-1]
    assert advance_period(
        restored_last.households, restored_last.firms, restored_last,
    ) == advance_period(
        baseline.periods[-1].households, baseline.periods[-1].firms,
        baseline.periods[-1],
    )


@pytest.mark.parametrize("target", [-1, 101, float("nan"), True, "0.5"])
def test_invalid_target_is_not_interpreted_as_a_preference_score(target):
    payload = json.loads(dump_experiment(experiment(0)))
    payload["current"]["draft"]["households"][0]["consumption_target"] = target
    with pytest.raises(ExperimentError):
        load_experiment(json.dumps(payload))


def test_changed_run_or_corrupted_baseline_cannot_be_replayed():
    current = experiment(1)
    payload = json.loads(dump_experiment(current, baseline=current))
    payload["current"]["run"]["households"][0]["consumption_target"] = 5
    with pytest.raises(ExperimentError, match="reproduced"):
        load_experiment(json.dumps(payload))
    payload = json.loads(dump_experiment(current, baseline=current))
    payload["baseline"]["run"]["period_digests"][0] = "0" * 64
    with pytest.raises(ExperimentError, match="reproduced"):
        load_experiment(json.dumps(payload))


@pytest.mark.parametrize("version", [1, 2, 3])
def test_retired_files_are_rejected_before_replay_without_dead_links(version):
    payload = json.loads(dump_experiment(experiment(0)))
    payload["format_version"] = version
    payload["engine_version"] = "retired-engine"
    with pytest.raises(RetiredExperimentError, match="retired model") as captured:
        load_experiment(json.dumps(payload))
    assert "Start a new experiment" in str(captured.value)
    assert "Your current experiment has not been replaced" in str(captured.value)


def test_reject_duplicate_keys_nonfinite_unknown_fields_and_oversize_input():
    encoded = dump_experiment(experiment(0)).decode()
    for malformed in (
        encoded.replace('"format_version": 4', '"format_version": 4, "format_version": 4'),
        encoded.replace('"consumption_target": 1.2345678912345', '"consumption_target": NaN'),
        encoded.replace('"selected_period": 1', '"selected_period": 1, "extra": 2'),
        " " * (MAX_FILE_BYTES + 1),
    ):
        with pytest.raises(ExperimentError):
            load_experiment(malformed)


def test_zero_cash_draft_can_be_saved_without_claiming_a_valid_run():
    draft = experiment(0)
    draft = replace(draft, draft_households=tuple(
        replace(household, money=0) for household in draft.draft_households
    ))
    restored = load_experiment(dump_experiment(draft)).current
    assert restored == draft
    assert not restored.periods


def test_unsupported_engine_cannot_silently_recalculate_saved_results():
    payload = json.loads(dump_experiment(experiment(0)))
    payload["engine_version"] = "future-rules"
    with pytest.raises(ExperimentError, match="different engine version"):
        load_experiment(json.dumps(payload))


def test_frozen_current_file_and_continuation_preserve_the_published_contract():
    fixture = Path(__file__).parent / "fixtures/current_model_workspace.json"
    restored = load_experiment(fixture.read_bytes()).current
    assert len(restored.periods) == 3
    assert restored.selected_period == 2
    assert restored.report_scope == "Cumulative"
    assert restored.selected_firm == "firm_b"
    assert restored.draft_households[0].consumption_target == 1.25
    assert restored.periods[0].households[0].consumption_target == .5
    # Independent symmetric-equilibrium benchmark: the target is slack.
    first = restored.periods[0]
    consumption = .8 * sqrt(10 / 13)
    assert first.wage == pytest.approx(13 / 11)
    assert first.price == pytest.approx((8 / 11) / consumption)
    assert first.work["household_1"] == pytest.approx(5 / 13)
    assert first.consumption["household_1"] == pytest.approx(consumption)
    assert first.closing_cash["household_1"] == pytest.approx(8 / 11)
    previous = restored.periods[-1]
    future = advance_period(previous.households, previous.firms, previous)
    assert _digest(future) == "31078a50cec4d819ae2a644f1f5704f2671551614256a74371c596e36f90d437"
