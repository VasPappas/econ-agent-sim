"""Behavioral checks for the single application's durable state controller."""

import json
from dataclasses import replace

import pytest

from econ_agent_sim import workspace
from econ_agent_sim.engine import advance_period, default_firms, default_households
from econ_agent_sim.experiments import ExperimentError, dump_experiment


def running_workspace():
    state = {}
    workspace.initialize(state)
    workspace.start(state)
    assert state["te_error"] is None
    return state


def test_navigation_keeps_draft_and_next_period_uses_submitted_settings():
    state = running_workspace()
    first = state["te_history"][0]
    state["te_household_consumption_target_0"] = 8
    workspace.capture(state)
    state["te_view"] = "Results"
    workspace.initialize(state)
    assert state["te_households"][0]["consumption_target"] == 8
    workspace.next_period(state)
    assert state["te_history"][-1] == advance_period(first.households, first.firms, first)
    assert state["te_submitted"][0][0].consumption_target == .5
    state["te_view"] = "Set up"
    workspace.initialize(state)
    assert state["te_households"][0]["consumption_target"] == 8


def test_failed_start_and_partially_failed_batch_preserve_completed_run(monkeypatch):
    state = running_workspace()
    history = state["te_history"]
    submitted = state["te_submitted"]
    for household in state["te_households"]:
        household["money"] = 0
    workspace.start(state)
    assert "Could not start" in state["te_error"]
    assert state["te_history"] is history
    assert state["te_submitted"] == submitted
    calls = 0

    def fail_second(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise ValueError("Numerical case could not be solved")
        return advance_period(*args, **kwargs)

    monkeypatch.setattr(workspace, "advance_period", fail_second)
    workspace.next_period(state, 10)
    assert calls == 2
    assert state["te_history"] is history
    assert state["te_period_focus"] == 1
    assert "Could not advance" in state["te_error"]


def test_copy_preset_and_reset_preserve_baseline_and_do_not_apply_stale_widgets():
    state = running_workspace()
    workspace.save_baseline(state)
    baseline = state["te_baseline"]
    history = state["te_history"]
    state["te_household_money_0"] = 99
    state["te_firm_reinvestment_rate_0"] = 90
    state["te_firm_investment_policy_0"] = "user_cost"
    state["te_firm_required_return_0"] = 75
    households, firms = default_households(), default_firms()
    households[0]["consumption_target"] = 0
    workspace.apply_preset(state, households, firms, "No targets")
    workspace.capture(state)
    assert state["te_households"][0]["consumption_target"] == 0
    assert state["te_households"][0]["money"] == households[0]["money"]
    assert state["te_firms"][0]["investment_policy"] == "percentage"
    assert state["te_firms"][0]["required_return"] == .05
    assert state["te_history"] is history
    assert state["te_baseline"] is baseline
    workspace.edit_baseline_copy(state)
    assert state["te_households"][0]["consumption_target"] == .5
    assert state["te_history"] is history
    assert state["te_copy_name"] == "My experiment · variation"
    workspace.start(state)
    assert state["te_experiment_name"] == "My experiment · variation"
    workspace.reset(state)
    assert state["te_baseline"] is baseline
    assert state["te_history"] == []
    assert state["te_households"] == default_households()


def test_bulk_preferences_keep_individual_money_and_sync_draft_widgets():
    state = running_workspace()
    original_history = state["te_history"]
    state["te_household_consumption_priority_0"] = 3.2
    state["te_household_consumption_target_0"] = 1.1
    state["te_household_money_1"] = 7
    state["te_household_consumption_target_1"] = 9
    workspace.apply_household_preferences(state)
    workspace.capture(state)
    assert state["te_households"][1]["consumption_priority"] == 3.2
    assert state["te_households"][1]["consumption_target"] == 1.1
    assert state["te_households"][1]["money"] == 7
    assert state["te_history"] is original_history


def test_resize_removes_stale_widgets_and_respects_expander_state():
    state = {}
    workspace.initialize(state)
    state["te_count"] = 3
    workspace.resize(state)
    state["te_household_money_2"] = 19
    state["te_open_household_0"] = True
    workspace.remember_expander(state, "household_0")
    state["te_open_household_2"] = True
    workspace.remember_expander(state, "household_2")
    state["te_count"] = 2
    workspace.resize(state)
    assert state["te_expanded"]["household_0"] is True
    assert "household_2" not in state["te_expanded"]
    assert "te_household_money_2" not in state
    state["te_count"] = 3
    workspace.resize(state)
    assert state["te_households"][2]["money"] == default_households(3)[2]["money"]


def test_adding_households_after_import_keeps_all_entity_ids_unique_and_can_run():
    source = {}
    workspace.initialize(source)
    source["te_households"][0]["id"] = "household_3"
    source["te_firms"][0]["id"] = "household_4"
    source["te_firms"][1]["id"] = "household_5"
    source["te_selected_firm"] = "household_4"
    data = dump_experiment(workspace.current_experiment(source))
    state = {}
    workspace.initialize(state)
    workspace.restore_experiment(state, data)
    workspace.start(state)
    workspace.save_baseline(state)
    baseline = state["te_baseline"]
    retained = [dict(item) for item in state["te_households"]]
    firms = [dict(item) for item in state["te_firms"]]
    state["te_count"] = 20
    workspace.resize(state)
    ids = [item["id"] for item in (*state["te_households"], *state["te_firms"])]
    assert len(set(ids)) == len(ids) == 22
    assert state["te_households"][:2] == retained
    assert state["te_firms"] == firms
    workspace.start(state)
    assert state["te_error"] is None
    assert len(state["te_history"][0].households) == 20
    assert state["te_baseline"] is baseline
    current = workspace.current_experiment(state)
    restored = {}
    workspace.initialize(restored)
    workspace.restore_experiment(restored, dump_experiment(current, baseline=baseline))
    assert workspace.current_experiment(restored) == current
    assert restored["te_baseline"] == baseline


@pytest.mark.parametrize("name", ["bad\tname", "bad\ud800name", "x" * 81])
def test_invalid_name_edits_keep_last_valid_name_run_and_baseline(name):
    state = running_workspace()
    workspace.save_baseline(state)
    history, baseline = state["te_history"], state["te_baseline"]
    state["te_copy_name"] = "Pending variation"
    state["te_name_input"] = name
    workspace.remember_experiment_name(state)
    assert "Could not rename" in state["te_error"]
    assert state["te_name_input"] == state["te_experiment_name"] == "My experiment"
    assert state["te_history"] is history
    assert state["te_baseline"] is baseline
    assert state["te_copy_name"] == "Pending variation"
    assert dump_experiment(workspace.current_experiment(state), baseline=baseline)
    state["te_name_input"] = "  Another economy 🌍  "
    workspace.remember_experiment_name(state)
    assert state["te_name_input"] == state["te_experiment_name"] == "Another economy 🌍"
    assert state["te_error"] is None
    assert "te_copy_name" not in state


@pytest.mark.parametrize("old_name", ["bad\tname", "bad\ud800name"])
def test_valid_import_recovers_even_if_outgoing_name_is_invalid(old_name):
    source = running_workspace()
    workspace.save_baseline(source)
    current = replace(workspace.current_experiment(source), name="Restored economy")
    data = dump_experiment(current, baseline=source["te_baseline"])
    state = running_workspace()
    state["te_experiment_name"] = old_name
    state["te_name_input"] = old_name
    workspace.restore_experiment(state, data)
    assert workspace.current_experiment(state) == current
    assert state["te_name_input"] == "Restored economy"
    assert state["te_baseline"] == source["te_baseline"]
    assert state["te_error"] is None


@pytest.mark.parametrize("path", [
    ("current", "name"),
    ("baseline", "name"),
    ("current", "draft", "households", 0, "name"),
    ("current", "run", "firms", 0, "name"),
    ("baseline", "draft", "firms", 0, "name"),
    ("baseline", "run", "households", 0, "name"),
])
def test_surrogate_import_rejection_preserves_entire_workspace(path):
    source = running_workspace()
    workspace.save_baseline(source)
    payload = json.loads(dump_experiment(
        workspace.current_experiment(source), baseline=source["te_baseline"],
    ))
    target = payload
    for part in path[:-1]:
        target = target[part]
    target[path[-1]] = "broken\ud800name"
    state = running_workspace()
    workspace.next_period(state)
    workspace.save_baseline(state)
    state["te_households"][0]["consumption_target"] = 8
    state["te_household_consumption_target_0"] = 8
    state["te_name_input"] = "My experiment"
    current = workspace.current_experiment(state)
    snapshot = dict(state)
    baseline, history = state["te_baseline"], state["te_history"]
    with pytest.raises(ExperimentError, match="valid Unicode text"):
        workspace.restore_experiment(state, json.dumps(payload))
    assert state == snapshot
    assert state["te_history"] is history
    assert state["te_baseline"] is baseline
    assert workspace.current_experiment(state) == current


def test_restore_is_atomic_and_restores_view_dirty_draft_and_submitted_run():
    source = running_workspace()
    workspace.next_period(source)
    workspace.save_baseline(source)
    current = workspace.current_experiment(source)
    saved = replace(
        current, name="Saved experiment", report_scope="Cumulative", selected_firm="firm_b",
        draft_households=(replace(current.draft_households[0], consumption_target=8),
                          current.draft_households[1]),
        draft_firms=(
            replace(current.draft_firms[0], investment_policy="user_cost",
                    required_return=.12345, reinvestment_rate=.6789),
            replace(current.draft_firms[1], required_return=.321),
        ),
    )
    data = dump_experiment(saved, baseline=source["te_baseline"])
    state = running_workspace()
    workspace.restore_experiment(state, data)
    assert workspace.current_experiment(state) == saved
    assert state["te_view"] == "Results"
    assert state["te_households"][0]["consumption_target"] == 8
    assert state["te_submitted"][0][0].consumption_target == .5
    assert state["te_firms"][0]["investment_policy"] == "user_cost"
    assert state["te_firms"][0]["required_return"] == .12345
    assert state["te_firms"][0]["reinvestment_rate"] == .6789
    assert state["te_firms"][1]["investment_policy"] == "percentage"
    assert state["te_firms"][1]["required_return"] == .321
    assert state["te_submitted"][1][0].investment_policy == "percentage"
    snapshot = dict(state)
    corrupted = json.loads(data)
    corrupted["baseline"]["run"]["period_digests"][0] = "0" * 64
    with pytest.raises(ExperimentError):
        workspace.restore_experiment(state, json.dumps(corrupted))
    assert state == snapshot
    prior = state["te_history"][-1]
    workspace.next_period(state)
    assert state["te_history"][-1] == advance_period(prior.households, prior.firms, prior)
