"""Target settings and histories survive saves without rewriting old models."""

import json
from dataclasses import replace
from pathlib import Path

import pytest

from econ_agent_sim.economy_1_1 import (
    Firm,
    Household,
    advance_target_period,
    default_firms,
    default_households,
)
from econ_agent_sim.target_experiments import (
    Experiment,
    ExperimentError,
    LegacyExperimentError,
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
        history.append(advance_target_period(
            households, firms, history[-1] if history else None,
        ))
    return Experiment("Target experiment", households, firms, tuple(history))


def test_roundtrip_preserves_target_dirty_draft_baseline_and_continuation():
    baseline = experiment()
    current = replace(
        baseline, name="Different target",
        draft_households=(replace(baseline.draft_households[0], consumption_target=0),
                          baseline.draft_households[1]),
        selected_period=2, report_scope="Cumulative", selected_firm="firm_b",
    )
    encoded = dump_experiment(current, baseline=baseline)
    payload = json.loads(encoded)
    assert payload["model"] == "consumption_target"
    assert payload["engine_version"] == "consumption-targets-1.1.0"
    assert payload["format_version"] == 3
    reopened = load_experiment(encoded)
    assert reopened.current == current
    assert reopened.baseline == baseline
    assert dump_experiment(reopened.current, baseline=reopened.baseline) == encoded
    restored_last = reopened.current.periods[-1]
    assert advance_target_period(
        restored_last.households, restored_last.firms, restored_last,
    ) == advance_target_period(
        baseline.periods[-1].households, baseline.periods[-1].firms,
        baseline.periods[-1],
    )


@pytest.mark.parametrize("target", [-1, 101, float("nan"), True, "0.5"])
def test_invalid_target_is_not_interpreted_as_a_preference_score(target):
    payload = json.loads(dump_experiment(experiment(0)))
    payload["current"]["draft"]["households"][0]["consumption_target"] = target
    with pytest.raises(ExperimentError):
        load_experiment(json.dumps(payload))


def test_target_changed_in_completed_run_fails_replay():
    payload = json.loads(dump_experiment(experiment(1)))
    payload["current"]["run"]["households"][0]["consumption_target"] = 5
    with pytest.raises(ExperimentError, match="reproduced"):
        load_experiment(json.dumps(payload))


def test_old_10_file_is_recognized_and_not_reinterpreted():
    path = Path(__file__).parent / "fixtures/economy_1_0_released_workspace.json"
    with pytest.raises(LegacyExperimentError) as captured:
        load_experiment(path.read_bytes())
    assert captured.value.economy == "1.0"
    assert "Two Firms, One Market" in str(captured.value)


def test_old_09_file_is_recognized_and_not_reinterpreted():
    from econ_agent_sim.economy_0_9 import Firm as OldFirm
    from econ_agent_sim.economy_0_9 import Household as OldHousehold
    from econ_agent_sim.investment_experiments import Experiment as OldExperiment
    from econ_agent_sim.investment_experiments import dump_experiment as dump_old

    data = dump_old(OldExperiment(
        "Old", (OldHousehold("One"), OldHousehold("Two")), OldFirm(),
    ))
    with pytest.raises(LegacyExperimentError) as captured:
        load_experiment(data)
    assert captured.value.economy == "0.9"


def test_reject_corrupted_baseline_even_if_current_is_valid():
    current = experiment(1)
    payload = json.loads(dump_experiment(current, baseline=current))
    payload["baseline"]["run"]["period_digests"][0] = "0" * 64
    with pytest.raises(ExperimentError, match="reproduced"):
        load_experiment(json.dumps(payload))
