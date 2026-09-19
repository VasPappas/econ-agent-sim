"""Application boundary checks for the one current monetary model."""

from dataclasses import FrozenInstanceError, replace

import pytest

from econ_agent_sim import MAX_PERIODS, Settings, SimulationError, simulate
from econ_agent_sim.domain import SETTING_BOUNDS


def test_application_builds_one_immutable_certified_plan_beyond_display_end():
    settings = Settings()
    run = simulate(settings)
    assert len(run.periods) == MAX_PERIODS == 100
    assert run.solution.horizon > MAX_PERIODS
    assert run.solution.comparison_horizon > MAX_PERIODS
    assert run.solution.max_equation_residual < 1e-10
    assert run.solution.prefix_difference < 1e-8
    assert run.solution.terminal_gap < 1e-8
    assert run.periods[-1].next_capital > 0
    with pytest.raises(FrozenInstanceError):
        run.periods[0].consumption = 0
    with pytest.raises(FrozenInstanceError):
        settings.beta = .8


def test_submitted_parameters_and_starting_resources_reach_the_solver():
    settings = Settings(beta=.9, depreciation=.25, leisure_weight=1.2,
                        money_weight=.2, initial_capital=2., initial_firm_cash_share=.4)
    run = simulate(settings)
    assert run.solution.parameters == settings.to_parameters()
    assert run.periods[0].capital == 2
    assert run.periods[0].firm_cash == .2
    assert run.periods[0].household_cash == .3
    assert run.settings == settings


@pytest.mark.parametrize("settings,field", (
    (Settings(initial_capital=.1), "distribution"),
    (Settings(initial_capital=100.), "investment"),
))
def test_app_uses_constrained_choices_and_later_resumes_activity(settings, field):
    run = simulate(settings)
    assert getattr(run.periods[0], field) == 0
    assert getattr(run.periods[-1], field) > 0


def test_unsupported_cash_retention_has_a_useful_public_error():
    with pytest.raises(SimulationError, match="opening money unspent"):
        simulate(Settings(initial_capital=.1, initial_firm_cash_share=.99))


def test_failed_or_mismatched_solver_result_is_never_accepted(monkeypatch):
    from econ_agent_sim import engine

    run = simulate(Settings())
    monkeypatch.setattr(engine, "solve_constrained_transition", lambda *a, **k:
                        replace(run.solution, converged=False, status="horizon_budget_exhausted"))
    with pytest.raises(SimulationError, match="verified"):
        simulate(Settings())
    monkeypatch.setattr(engine, "solve_constrained_transition", lambda *a, **k:
                        replace(run.solution, periods=run.periods[:3]))
    with pytest.raises(SimulationError, match="does not match"):
        simulate(Settings())


@pytest.mark.parametrize("field", tuple(SETTING_BOUNDS))
def test_settings_validate_finite_numeric_application_domain(field):
    low, high = SETTING_BOUNDS[field]
    for value in (True, "1", None, float("nan"), float("inf"), low / 2, high * 2):
        with pytest.raises(ValueError):
            Settings(**{field: value})


def test_settings_file_mapping_is_exact_and_roundtrips():
    values = Settings().to_dict()
    assert Settings.from_dict(values) == Settings()
    for invalid in ({}, {**values, "old_policy": "percentage"}, [], None):
        with pytest.raises(ValueError):
            Settings.from_dict(invalid)
