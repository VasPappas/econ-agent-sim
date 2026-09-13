"""Portable two-firm files preserve full accounts and reject incompatible state."""

import json
from dataclasses import replace

import pytest

from econ_agent_sim.competition_experiments import (
    ENGINE_VERSION,
    MAX_FILE_BYTES,
    Experiment,
    ExperimentError,
    LegacyExperimentError,
    dump_experiment,
    load_experiment,
)
from econ_agent_sim.competition_reporting import competition_report
from econ_agent_sim.economy_1_0 import (
    Firm,
    Household,
    advance_competition_period,
    default_firms,
    default_households,
)


def experiment(period_count=3, *, firms=None, name="My experiment", count=2):
    firms = firms or tuple(Firm(**item) for item in default_firms())
    households = tuple(Household(**item) for item in default_households(count))
    periods = []
    previous = None
    for _ in range(period_count):
        previous = advance_competition_period(households, firms, previous)
        periods.append(previous)
    return Experiment(name, households, firms, tuple(periods))


def test_workspace_roundtrip_keeps_both_firms_dirty_draft_baseline_and_future():
    baseline = experiment(name="Baseline")
    firms = (replace(baseline.draft_firms[0], productivity=2.4), baseline.draft_firms[1])
    current = experiment(firms=firms, name="A produces more")
    current = replace(
        current,
        draft_households=(
            replace(current.draft_households[0], consumption_priority=1.1234567891234567),
            current.draft_households[1],
        ),
        draft_firms=(firms[0], replace(firms[1], capital=3.1234567891234567)),
        selected_period=2, report_scope="Cumulative", selected_firm="firm_b",
    )
    encoded = dump_experiment(current, baseline=baseline)
    payload = json.loads(encoded)
    assert payload["format_version"] == 2
    assert payload["model"] == "competition"
    restored = load_experiment(encoded)
    assert restored.current == current
    assert restored.baseline == baseline
    assert restored.current.draft_firms != current.periods[0].firms
    assert dump_experiment(restored.current, baseline=restored.baseline) == encoded
    assert competition_report(restored.current.periods, cumulative=True) == (
        competition_report(current.periods, cumulative=True)
    )
    prior = restored.current.periods[-1]
    resumed = advance_competition_period(prior.households, prior.firms, prior)
    original = current.periods[-1]
    uninterrupted = advance_competition_period(original.households, original.firms, original)
    assert resumed == uninterrupted


def test_draft_only_file_preserves_an_unrunnable_setup_and_firm_selection():
    initial = experiment(period_count=0)
    draft = replace(
        initial,
        draft_households=tuple(replace(item, money=0) for item in initial.draft_households),
        selected_firm="firm_b",
    )
    restored = load_experiment(dump_experiment(draft))
    assert restored.current == draft
    assert restored.current.periods == ()
    assert restored.baseline is None


def test_maximum_workspace_is_bounded_and_reproducible():
    current = replace(experiment(period_count=100, count=20), selected_period=100)
    encoded = dump_experiment(current, baseline=current)
    assert len(encoded) < MAX_FILE_BYTES
    restored = load_experiment(encoded)
    assert restored.current.periods == current.periods
    assert restored.baseline.periods == current.periods


@pytest.mark.parametrize("change", [
    lambda p: p.update(format_version=1),
    lambda p: p.update(format_version=True),
    lambda p: p.update(model="investment"),
    lambda p: p.update(engine_version=ENGINE_VERSION + "-new"),
    lambda p: p["current"]["draft"]["firms"].pop(),
    lambda p: p["current"]["draft"]["firms"][0].update(money=True),
    lambda p: p["current"]["draft"]["firms"][0].update(capital=0),
    lambda p: p["current"]["draft"]["firms"][0].update(theta=.4),
    lambda p: p["current"]["draft"]["firms"][0].update(extra=1),
    lambda p: p["current"]["draft"]["firms"][0].update(name="=1+1"),
    lambda p: p["current"]["draft"]["firms"][1].update(id="firm_a"),
    lambda p: p["current"]["draft"]["firms"][0].update(id="household_1"),
    lambda p: p["current"]["draft"]["firms"][0].update(id="<firm>"),
    lambda p: p["current"]["run"]["period_digests"].append("0" * 64),
    lambda p: p["current"]["run"]["firms"][1].update(capital=5),
    lambda p: p["current"]["view"].update(selected_period=0),
    lambda p: p["current"]["view"].update(report_scope="Everything"),
    lambda p: p["current"]["view"].update(selected_firm="firm_c"),
])
def test_invalid_files_do_not_mutate_the_original_experiment(change):
    existing = experiment()
    before = dump_experiment(existing)
    payload = json.loads(before)
    change(payload)
    with pytest.raises(ExperimentError):
        load_experiment(json.dumps(payload))
    assert dump_experiment(existing) == before


def test_corrupt_baseline_rejects_entire_file_and_empty_baseline_is_not_saved():
    existing = experiment()
    payload = json.loads(dump_experiment(existing, baseline=existing))
    payload["baseline"]["run"]["period_digests"][1] = "0" * 64
    with pytest.raises(ExperimentError, match="could not be reproduced exactly"):
        load_experiment(json.dumps(payload))
    empty = experiment(period_count=0)
    with pytest.raises(ExperimentError, match="baseline needs"):
        dump_experiment(existing, baseline=empty)


def test_digest_checks_both_firm_accounts_and_per_household_allocations():
    original = experiment(period_count=1)
    period = original.periods[0]
    account = period.firm_accounts["firm_b"]
    changed_account = replace(
        period,
        firm_accounts={**period.firm_accounts, "firm_b": replace(
            account, net_operating_profit=account.net_operating_profit + .01,
        )},
    )
    allocation = period.allocations[0]
    changed_allocation = replace(
        period,
        allocations=(replace(allocation, work=allocation.work + .01), *period.allocations[1:]),
    )
    for changed in (changed_account, changed_allocation):
        encoded = dump_experiment(replace(original, periods=(changed,)))
        with pytest.raises(ExperimentError, match="could not be reproduced exactly"):
            load_experiment(encoded)


def test_legacy_file_is_recognized_and_still_reopens_in_original_engine():
    from econ_agent_sim.economy_0_9 import Firm as InvestmentFirm
    from econ_agent_sim.economy_0_9 import Household as InvestmentHousehold
    from econ_agent_sim.economy_0_9 import advance_investment_period
    from econ_agent_sim.investment_experiments import Experiment as InvestmentExperiment
    from econ_agent_sim.investment_experiments import dump_experiment as dump_legacy
    from econ_agent_sim.investment_experiments import load_experiment as load_legacy

    households = (InvestmentHousehold("One"), InvestmentHousehold("Two"))
    firm = InvestmentFirm()
    first = advance_investment_period(households, firm)
    old = InvestmentExperiment("Original economy", households, firm, (first,))
    encoded = dump_legacy(old)
    with pytest.raises(LegacyExperimentError, match="Economy 0.9"):
        load_experiment(encoded)
    restored = load_legacy(encoded)
    assert restored.current == old
    assert advance_investment_period(households, firm, restored.current.periods[0]) == (
        advance_investment_period(households, firm, first)
    )


@pytest.mark.parametrize("data", [
    b"not json", b"\xff", b"[]", b"null", b"{}",
    b'{"format": "one", "format": "two"}',
    b'{"number": NaN}', b'{"number": Infinity}',
    b"[" * 2000 + b"]" * 2000,
    b" " * (MAX_FILE_BYTES + 1),
    "\N{SNOWMAN}" * (MAX_FILE_BYTES // 2),
])
def test_invalid_or_oversized_json_has_a_readable_error(data):
    with pytest.raises(ExperimentError):
        load_experiment(data)
