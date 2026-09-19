"""Framework-independent state for the current forward-looking economy.

A submitted run is a complete certified plan. Advancing reveals that same plan;
editing the draft or navigating never changes its decisions or planning horizon.
"""

from collections.abc import MutableMapping
from typing import Any

from econ_agent_sim.domain import MAX_PERIODS, MODEL_ID, Settings
from econ_agent_sim.engine import simulate
from econ_agent_sim.experiments import Baseline, validate_experiment_name

State = MutableMapping[str, Any]


def initialize(state: State) -> None:
    """Initialize once, explicitly retiring sessions from a different economy."""
    retired = state.get("te_model_id") != MODEL_ID and any(
        key.startswith("te_") for key in state
    )
    if state.get("te_model_id") != MODEL_ID:
        for key in list(state):
            if key.startswith("te_"):
                del state[key]
    for key, value in {
        "model_id": MODEL_ID,
        "draft": Settings(),
        "run": None,
        "visible_periods": 0,
        "selected_period": 1,
        "scope": "This period",
        "view": "Set up",
        "baseline": None,
        "name": "My experiment",
        "error": None,
    }.items():
        state.setdefault(f"te_{key}", value)
    if retired:
        state["te_notice"] = (
            "Tiny Economy now uses a forward-looking monetary model. The previous "
            "session's results and baseline used different economic rules, so a "
            "fresh setup is ready. Previously downloaded files remain unchanged."
        )


def set_draft(state: State, settings: Settings) -> None:
    if type(settings) is not Settings:
        raise ValueError("Use the current economy's settings.")
    state["te_draft"] = settings


def start(state: State, settings: Settings | None = None) -> bool:
    """Replace results only after a complete candidate plan has succeeded."""
    candidate_settings = state["te_draft"] if settings is None else settings
    try:
        if type(candidate_settings) is not Settings:
            raise ValueError("Use the current economy's settings.")
        candidate = simulate(candidate_settings)
    except (ValueError, ArithmeticError) as error:
        state["te_error"] = f"Could not start this setup: {error}"
        return False
    state.update({
        "te_draft": candidate_settings,
        "te_run": candidate,
        "te_visible_periods": 1,
        "te_selected_period": 1,
        "te_view": "Results",
        "te_error": None,
    })
    return True


def advance(state: State, count: int = 1) -> bool:
    """Reveal already solved periods without solving a different economy."""
    if type(count) is not int or count < 1:
        raise ValueError("Advance a positive whole number of periods.")
    run = state["te_run"]
    visible = state["te_visible_periods"]
    if run is None or visible >= MAX_PERIODS:
        return False
    visible = min(visible + count, MAX_PERIODS, len(run.periods))
    state.update({
        "te_visible_periods": visible,
        "te_selected_period": visible,
        "te_error": None,
    })
    return True


def select_period(state: State, number: int) -> None:
    if type(number) is not int or not 1 <= number <= state["te_visible_periods"]:
        raise ValueError("Choose a completed period in this experiment.")
    state["te_selected_period"] = number


def rename(state: State, name: str) -> bool:
    try:
        validate_experiment_name(name)
    except ValueError as error:
        state["te_error"] = f"Could not rename this experiment: {error}"
        return False
    state["te_name"] = name
    state["te_error"] = None
    return True


def save_baseline(state: State, name: str | None = None) -> bool:
    if state["te_run"] is None:
        return False
    try:
        baseline = Baseline(
            run=state["te_run"], visible_periods=state["te_visible_periods"],
            name=state["te_name"] if name is None else name,
        )
    except ValueError as error:
        state["te_error"] = f"Could not keep this baseline: {error}"
        return False
    state["te_baseline"] = baseline
    state["te_error"] = None
    state["te_notice"] = "Baseline kept. Its results stay fixed while you try another setup."
    return True


def clear_baseline(state: State) -> None:
    state["te_baseline"] = None


def edit_baseline_copy(state: State) -> bool:
    baseline = state["te_baseline"]
    if baseline is None:
        return False
    state.update({
        "te_draft": baseline.run.settings,
        "te_view": "Set up",
        "te_error": None,
        "te_notice": (
            "Baseline settings copied. Change a setting, then start a new simulation. "
            "Current results and the baseline stay fixed until then."
        ),
    })
    return True


def reset(state: State) -> None:
    """Restore default draft and empty results, retaining the saved baseline."""
    baseline = state["te_baseline"]
    state.update({
        "te_draft": Settings(),
        "te_run": None,
        "te_visible_periods": 0,
        "te_selected_period": 1,
        "te_scope": "This period",
        "te_view": "Set up",
        "te_name": "My experiment",
        "te_error": None,
        "te_notice": (
            "Default setup restored. Your comparison baseline is still saved."
            if baseline is not None else
            "Default setup restored. Ready for a fresh experiment."
        ),
    })
