"""Portable files keep submitted results and editable drafts independent."""

import json
from dataclasses import replace

import pytest

from econ_agent_sim.economy_0_9 import (
    Firm,
    Household,
    advance_investment_period,
    investment_report,
)
from econ_agent_sim.investment_experiments import (
    ENGINE_VERSION,
    MAX_FILE_BYTES,
    Experiment,
    ExperimentError,
    dump_experiment,
    load_experiment,
)


def experiment(period_count=3, *, firm=None, name="My experiment"):
    firm = firm or Firm()
    households = (Household("Household 1"), Household("Household 2", money=2))
    periods = []
    previous = None
    for _ in range(period_count):
        previous = advance_investment_period(households, firm, previous)
        periods.append(previous)
    return Experiment(name, households, firm, tuple(periods))


def test_workspace_roundtrip_restores_dirty_draft_baseline_and_original_accounts():
    baseline = experiment(name="Baseline")
    current = experiment(firm=Firm(reinvestment_rate=.2), name="Consume more")
    draft = (
        replace(current.draft_households[0], consumption_priority=1.1234567891234567),
        current.draft_households[1],
    )
    current = replace(
        current, draft_households=draft, draft_firm=Firm(capital=3.1234567891234567),
        selected_period=2, report_scope="Cumulative",
    )
    encoded = dump_experiment(current, baseline=baseline)
    restored = load_experiment(encoded)
    assert restored.current == current
    assert restored.baseline == baseline
    assert restored.current.draft_households != current.periods[0].households
    assert restored.current.draft_firm != current.periods[0].firm
    assert dump_experiment(restored.current, baseline=restored.baseline) == encoded
    assert investment_report(restored.current.periods, cumulative=True) == (
        investment_report(current.periods, cumulative=True)
    )
    prior = restored.current.periods[-1]
    resumed = advance_investment_period(prior.households, prior.firm, prior)
    original = current.periods[-1]
    uninterrupted = advance_investment_period(
        original.households, original.firm, original
    )
    assert resumed == uninterrupted
    assert investment_report((resumed,)) == investment_report((uninterrupted,))


def test_draft_only_file_can_preserve_a_setup_that_is_not_ready_to_run():
    draft = Experiment(
        "Deciding where money starts", (
            Household("Household 1", money=0), Household("Household 2", money=0)
        ), Firm(),
    )
    restored = load_experiment(dump_experiment(draft))
    assert restored.current == draft
    assert restored.current.periods == ()
    assert restored.baseline is None


def test_maximum_workspace_is_bounded_and_reproducible():
    households = tuple(Household(f"Household {i + 1}") for i in range(20))
    periods = []
    previous = None
    for _ in range(100):
        previous = advance_investment_period(households, Firm(), previous)
        periods.append(previous)
    current = Experiment("Long run", households, Firm(), tuple(periods), 100)
    encoded = dump_experiment(current, baseline=current)
    assert len(encoded) < MAX_FILE_BYTES
    restored = load_experiment(encoded)
    assert restored.current.periods == current.periods
    assert restored.baseline.periods == current.periods


@pytest.mark.parametrize(
    "change",
    [
        lambda payload: payload.update(format_version=2),
        lambda payload: payload.update(format_version=True),
        lambda payload: payload.update(engine_version=ENGINE_VERSION + "-new"),
        lambda payload: payload["current"]["draft"]["firm"].update(money=True),
        lambda payload: payload["current"]["draft"]["firm"].update(capital=0),
        lambda payload: payload["current"]["draft"]["firm"].update(theta=.4),
        lambda payload: payload["current"]["draft"]["firm"].update(extra=1),
        lambda payload: payload["current"]["draft"]["firm"].update(name="=1+1"),
        lambda payload: payload["current"]["run"]["period_digests"].append("0" * 64),
        lambda payload: payload["current"]["run"]["firm"].update(capital=5),
        lambda payload: payload["current"]["view"].update(selected_period=0),
        lambda payload: payload["current"]["view"].update(report_scope="Everything"),
    ],
)
def test_changed_files_are_rejected_without_mutating_an_existing_experiment(change):
    existing = experiment()
    before = dump_experiment(existing)
    payload = json.loads(before)
    change(payload)
    with pytest.raises(ExperimentError):
        load_experiment(json.dumps(payload))
    assert dump_experiment(existing) == before


def test_invalid_baseline_rejects_whole_file():
    existing = experiment()
    payload = json.loads(dump_experiment(existing, baseline=existing))
    payload["baseline"]["run"]["period_digests"][1] = "0" * 64
    with pytest.raises(ExperimentError, match="could not be reproduced exactly"):
        load_experiment(json.dumps(payload))


def test_baseline_must_have_completed_periods():
    current = experiment()
    empty = experiment(period_count=0)
    with pytest.raises(ExperimentError, match="baseline needs"):
        dump_experiment(current, baseline=empty)
    payload = json.loads(dump_experiment(current, baseline=current))
    payload["baseline"]["run"] = None
    with pytest.raises(ExperimentError, match="baseline needs"):
        load_experiment(json.dumps(payload))


@pytest.mark.parametrize(
    "data",
    [
        b"not json", b"\xff", b"[]", b"null", b"{}",
        b'{"format": "one", "format": "two"}',
        b'{"number": NaN}', b'{"number": Infinity}',
        b"[" * 2000 + b"]" * 2000,
        b" " * (MAX_FILE_BYTES + 1),
        "\N{SNOWMAN}" * (MAX_FILE_BYTES // 2),
    ],
)
def test_invalid_or_oversized_json_has_a_readable_error(data):
    with pytest.raises(ExperimentError):
        load_experiment(data)
