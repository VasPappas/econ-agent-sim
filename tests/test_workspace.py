"""Submission, navigation and baseline lifetimes for the current economy."""

from dataclasses import replace

import pytest

from econ_agent_sim import workspace
from econ_agent_sim.domain import MAX_PERIODS, MODEL_ID, Settings
from econ_agent_sim.engine import SimulationError, simulate


@pytest.fixture(scope="module")
def run():
    return simulate(Settings())


@pytest.fixture
def state():
    state = {}
    workspace.initialize(state)
    return state


def completed(state, run, monkeypatch):
    monkeypatch.setattr(workspace, "simulate", lambda _: run)
    assert workspace.start(state)
    return state


def test_initialize_preserves_draft_and_navigation(state):
    settings = Settings(beta=.9)
    workspace.set_draft(state, settings)
    state.update(te_view="Ask why", te_scope="Cumulative", te_name="My next idea")
    snapshot = dict(state)
    workspace.initialize(state)
    assert state == snapshot
    assert state["te_model_id"] == MODEL_ID


def test_old_session_is_explicitly_retired_including_baseline_and_widgets():
    state = {
        "unrelated": "keep", "te_history": ["old"], "te_baseline": "old baseline",
        "te_firm_capital_0": 5, "te_draft": "old", "te_error": "old error",
    }
    workspace.initialize(state)
    assert state["unrelated"] == "keep"
    assert "te_history" not in state and "te_firm_capital_0" not in state
    assert state["te_run"] is None and state["te_baseline"] is None
    assert state["te_draft"] == Settings()
    assert "different economic rules" in state["te_notice"]


def test_start_solves_once_advance_only_reveals_the_same_plan(state, run, monkeypatch):
    calls = []

    def solve(settings):
        calls.append(settings)
        return run

    monkeypatch.setattr(workspace, "simulate", solve)
    assert workspace.start(state)
    assert calls == [Settings()]
    assert state["te_visible_periods"] == state["te_selected_period"] == 1
    assert state["te_view"] == "Results"
    workspace.set_draft(state, Settings(beta=.9))
    assert workspace.advance(state, 10)
    assert state["te_visible_periods"] == state["te_selected_period"] == 11
    assert state["te_run"] is run and calls == [Settings()]
    workspace.select_period(state, 3)
    state["te_view"] = "Ask why"
    workspace.initialize(state)
    assert state["te_selected_period"] == 3 and state["te_run"] is run


def test_failed_start_preserves_run_baseline_draft_and_navigation(state, run, monkeypatch):
    completed(state, run, monkeypatch)
    workspace.advance(state, 10)
    workspace.save_baseline(state)
    workspace.set_draft(state, Settings(initial_capital=100))
    snapshot = dict(state)

    def fail(_):
        raise SimulationError("Opening cash retention is not supported.")

    monkeypatch.setattr(workspace, "simulate", fail)
    assert not workspace.start(state)
    assert {k: v for k, v in state.items() if k != "te_error"} == {
        k: v for k, v in snapshot.items() if k != "te_error"
    }
    assert "Opening cash retention" in state["te_error"]


def test_first_failed_start_has_no_partial_results(state, monkeypatch):
    def fail(_):
        raise ArithmeticError("Numerical failure")

    monkeypatch.setattr(workspace, "simulate", fail)
    assert not workspace.start(state)
    assert state["te_run"] is None and state["te_visible_periods"] == 0
    assert state["te_view"] == "Set up"


def test_start_with_explicit_settings_commits_only_successful_candidate(state, run, monkeypatch):
    workspace.set_draft(state, Settings(beta=.9))
    completed(state, run, monkeypatch)
    assert workspace.start(state, run.settings)
    assert state["te_draft"] == run.settings
    assert not workspace.start(state, {"beta": .8})
    assert state["te_draft"] == run.settings and state["te_run"] is run


@pytest.mark.parametrize("count", [True, False, 0, -1, 1.5, "10", None])
def test_advance_rejects_nonpositive_or_noninteger_counts(state, count):
    with pytest.raises(ValueError, match="positive whole"):
        workspace.advance(state, count)


def test_advance_stops_at_display_limit(state, run, monkeypatch):
    assert not workspace.advance(state)
    completed(state, run, monkeypatch)
    assert workspace.advance(state, 1000)
    assert state["te_visible_periods"] == state["te_selected_period"] == MAX_PERIODS
    snapshot = dict(state)
    assert not workspace.advance(state)
    assert state == snapshot


@pytest.mark.parametrize("number", [True, 0, -1, 2, 1.0, "1"])
def test_selection_cannot_reveal_unseen_periods(state, run, monkeypatch, number):
    completed(state, run, monkeypatch)
    with pytest.raises(ValueError, match="completed period"):
        workspace.select_period(state, number)
    assert state["te_selected_period"] == 1


def test_baseline_is_fixed_and_uses_submitted_settings(state, run, monkeypatch):
    assert not workspace.save_baseline(state)
    completed(state, run, monkeypatch)
    workspace.advance(state, 10)
    workspace.set_draft(state, replace(run.settings, beta=.9))
    assert workspace.save_baseline(state, "Original plan")
    baseline = state["te_baseline"]
    assert baseline.run is run and baseline.visible_periods == 11
    assert baseline.name == "Original plan"
    workspace.advance(state, 10)
    assert state["te_baseline"] is baseline and baseline.visible_periods == 11
    assert workspace.edit_baseline_copy(state)
    assert state["te_draft"] == run.settings
    assert state["te_view"] == "Set up" and state["te_visible_periods"] == 21
    assert state["te_run"] is run
    workspace.clear_baseline(state)
    assert state["te_baseline"] is None
    assert not workspace.edit_baseline_copy(state)


def test_reset_keeps_only_baseline_and_restores_defaults(state, run, monkeypatch):
    completed(state, run, monkeypatch)
    workspace.save_baseline(state)
    baseline = state["te_baseline"]
    workspace.rename(state, "A different name")
    workspace.set_draft(state, Settings(beta=.9))
    state.update(te_scope="Cumulative", te_view="Ask why", te_error="old")
    workspace.reset(state)
    assert state["te_baseline"] is baseline
    assert state["te_run"] is None and state["te_draft"] == Settings()
    assert state["te_visible_periods"] == 0 and state["te_selected_period"] == 1
    assert state["te_scope"] == "This period" and state["te_view"] == "Set up"
    assert state["te_name"] == "My experiment" and state["te_error"] is None
    assert "baseline is still saved" in state["te_notice"]


@pytest.mark.parametrize("name", ["", " ", "bad\nname", "bad\x00name", "x" * 81, "\ud800"])
def test_bad_name_preserves_valid_name_and_baseline(state, run, monkeypatch, name):
    completed(state, run, monkeypatch)
    workspace.save_baseline(state)
    baseline = state["te_baseline"]
    assert not workspace.rename(state, name)
    assert not workspace.save_baseline(state, name)
    assert state["te_name"] == "My experiment" and state["te_baseline"] is baseline


def test_draft_rejects_other_models(state):
    with pytest.raises(ValueError, match="current economy"):
        workspace.set_draft(state, {"beta": .9})
    assert state["te_draft"] == Settings()
