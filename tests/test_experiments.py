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


def experiment(count=3, *, firms=None):
    households = tuple(
        Household(**{**item, "consumption_target": 1.2345678912345})
        for item in default_households()
    )
    if firms is None:
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
        "tiny_economy", "tiny-economy-3.0.0", 5,
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


def test_supported_unicode_names_roundtrip_in_literal_and_escaped_json():
    draft = experiment(0)
    households = tuple(
        replace(item, name=f"Οικογένεια {index} · 家庭 · 👩🏽‍🔬")
        for index, item in enumerate(draft.draft_households, 1)
    )
    firms = tuple(
        replace(item, name=f"مؤسسة {index} · Cafe\u0301")
        for index, item in enumerate(draft.draft_firms, 1)
    )
    current = replace(
        draft, name="Οικονομία · 経済 · 🌍", draft_households=households,
        draft_firms=firms, periods=(advance_period(households, firms),),
    )
    encoded = dump_experiment(current, baseline=current)
    for data in (encoded, json.dumps(json.loads(encoded))):
        reopened = load_experiment(data)
        assert reopened.current == current
        assert reopened.baseline == current


@pytest.mark.parametrize("policies", [
    ("user_cost", "user_cost"), ("user_cost", "percentage"),
])
def test_investment_policies_roundtrip_dirty_draft_baseline_and_continuation(policies):
    firms = tuple(
        replace(Firm(**item), investment_policy=policy, required_return=.08)
        for item, policy in zip(default_firms(), policies, strict=True)
    )
    submitted = experiment(2, firms=firms)
    current = replace(
        submitted,
        draft_firms=(
            replace(firms[0], investment_policy="percentage", required_return=.21),
            replace(firms[1], investment_policy="user_cost", reinvestment_rate=.7),
        ),
    )
    baseline = experiment(1)
    encoded = dump_experiment(current, baseline=baseline)
    restored = load_experiment(encoded)
    assert restored.current == current
    assert restored.baseline == baseline
    assert dump_experiment(restored.current, baseline=restored.baseline) == encoded
    previous = restored.current.periods[-1]
    assert advance_period(previous.households, previous.firms, previous) == advance_period(
        submitted.periods[-1].households, firms, submitted.periods[-1],
    )


@pytest.mark.parametrize("field,value", [
    ("investment_policy", None), ("investment_policy", True),
    ("investment_policy", "unknown"), ("investment_policy", []),
    ("required_return", -.01), ("required_return", 1.01),
    ("required_return", float("nan")), ("required_return", float("inf")),
    ("required_return", True), ("required_return", ".05"),
])
def test_invalid_policy_settings_are_rejected(field, value):
    payload = json.loads(dump_experiment(experiment(0)))
    payload["current"]["draft"]["firms"][0][field] = value
    with pytest.raises(ExperimentError):
        load_experiment(json.dumps(payload))


@pytest.mark.parametrize("field", ["investment_policy", "required_return"])
def test_current_format_requires_explicit_policy_settings(field):
    payload = json.loads(dump_experiment(experiment(0)))
    del payload["current"]["draft"]["firms"][0][field]
    with pytest.raises(ExperimentError, match="firm fields"):
        load_experiment(json.dumps(payload))


@pytest.mark.parametrize("field,value", [
    ("investment_policy", "user_cost"), ("required_return", .15),
])
def test_changed_submitted_policy_cannot_reuse_original_period_checks(field, value):
    payload = json.loads(dump_experiment(experiment(1)))
    payload["current"]["run"]["firms"][0][field] = value
    with pytest.raises(ExperimentError, match="reproduced"):
        load_experiment(json.dumps(payload))


@pytest.mark.parametrize("codepoint", [0xD800, 0xDFFF, 0xDABC])
def test_experiment_construction_rejects_non_unicode_scalar_names(codepoint):
    with pytest.raises(ExperimentError, match="valid Unicode text"):
        replace(experiment(0), name=f"broken{chr(codepoint)}name")


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
        encoded.replace('"format_version": 5', '"format_version": 5, "format_version": 5'),
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


@pytest.mark.parametrize("version,engine", [
    (4, "tiny-economy-3.0.0"), (5, "tiny-economy-2.0.0"),
])
def test_engine_identity_must_match_its_exact_supported_format(version, engine):
    payload = json.loads(dump_experiment(experiment(0)))
    payload.update(format_version=version, engine_version=engine)
    with pytest.raises(ExperimentError, match="different engine version"):
        load_experiment(json.dumps(payload))


@pytest.mark.parametrize("part", ["current", "baseline"])
@pytest.mark.parametrize("settings", ["draft", "run"])
@pytest.mark.parametrize("field,value", [
    ("investment_policy", "percentage"), ("required_return", .05),
])
def test_legacy_files_reject_policy_fields_even_when_they_match_defaults(
    part, settings, field, value,
):
    fixture = Path(__file__).parent / "fixtures/current_model_workspace.json"
    payload = json.loads(fixture.read_bytes())
    payload["baseline"] = json.loads(json.dumps(payload["current"]))
    payload[part][settings]["firms"][0][field] = value
    with pytest.raises(ExperimentError, match="firm fields"):
        load_experiment(json.dumps(payload))


@pytest.mark.parametrize("part", ["current", "baseline"])
def test_legacy_period_corruption_is_rejected_before_migration(part):
    fixture = Path(__file__).parent / "fixtures/current_model_workspace.json"
    payload = json.loads(fixture.read_bytes())
    payload["baseline"] = json.loads(json.dumps(payload["current"]))
    payload[part]["run"]["period_digests"][1] = "0" * 64
    with pytest.raises(ExperimentError, match="reproduced"):
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
    assert all(
        firm.investment_policy == "percentage" and firm.required_return == .05
        for firm in (*restored.draft_firms, *restored.periods[0].firms)
    )
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
    assert _digest(future, legacy=True) == (
        "31078a50cec4d819ae2a644f1f5704f2671551614256a74371c596e36f90d437"
    )
    encoded = dump_experiment(restored, baseline=restored)
    migrated = json.loads(encoded)
    assert migrated["format_version"] == 5
    assert migrated["engine_version"] == "tiny-economy-3.0.0"
    assert migrated["current"]["run"]["period_digests"] != json.loads(
        fixture.read_bytes(),
    )["current"]["run"]["period_digests"]
    reopened = load_experiment(encoded)
    assert reopened.current == reopened.baseline == restored
    assert advance_period(
        reopened.current.periods[-1].households,
        reopened.current.periods[-1].firms,
        reopened.current.periods[-1],
    ) == future


def test_legacy_hash_keeps_other_fields_named_like_the_new_policy_fields():
    period = experiment(1).periods[0]
    changed_check = replace(period, checks={**period.checks, "investment_policy": False})
    changed_solution = replace(period, solution={**period.solution, "required_return": .9})
    assert _digest(period, legacy=True) != _digest(changed_check, legacy=True)
    assert _digest(period, legacy=True) != _digest(changed_solution, legacy=True)
