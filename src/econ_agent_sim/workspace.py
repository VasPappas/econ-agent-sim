"""Framework-independent controller for editable and submitted experiments.

Widget values are transient. The draft, submitted settings, immutable period
history and comparison baseline each have their own explicit lifetime.
"""

from collections.abc import MutableMapping
from dataclasses import asdict
from typing import Any

from econ_agent_sim.engine import (
    Firm,
    Household,
    advance_period,
    default_firms,
    default_households,
)
from econ_agent_sim.experiments import (
    MAX_HOUSEHOLDS,
    MAX_PERIODS,
    Experiment,
    load_experiment,
)

PREFERENCE_FIELDS = (
    "consumption_priority", "money_priority", "leisure_priority",
)
HOUSEHOLD_FIELDS = ("money", "consumption_target", *PREFERENCE_FIELDS)
FIRM_FIELDS = (
    "money", "capital", "productivity", "reinvestment_rate", "depreciation_rate",
)
PERCENT_FIELDS = ("reinvestment_rate", "depreciation_rate")
State = MutableMapping[str, Any]


def initialize(state: State) -> None:
    """Fill missing durable state without replacing a draft on navigation."""
    for key, value in {
        "households": default_households(), "firms": default_firms(), "count": 2,
        "history": [], "submitted": None, "view": "Set up",
        "error": None, "expanded": {}, "period_focus": 1,
        "selected_firm": default_firms()[0]["id"],
        "saved_scope": state.get("te_report_scope", "This period"),
        "experiment_name": "My experiment", "baseline": None,
    }.items():
        state.setdefault(f"te_{key}", value)


def capture(state: State) -> None:
    """Copy current widget values into the separate editable draft."""
    changed = False
    for index, household in enumerate(state["te_households"]):
        for field in HOUSEHOLD_FIELDS:
            value = float(state.get(f"te_household_{field}_{index}", household[field]))
            changed |= value != household[field]
            household[field] = value
    for index, firm in enumerate(state["te_firms"]):
        for field in FIRM_FIELDS:
            key = f"te_firm_{field}_{index}"
            if key in state:
                value = float(state[key])
                value = value / 100 if field in PERCENT_FIELDS else value
                changed |= value != firm[field]
                firm[field] = value
    if changed:
        state["te_preset_name"] = "Custom"


def remember_expander(state: State, name: str) -> None:
    state["te_expanded"][name] = state[f"te_open_{name}"]


def resize(state: State) -> None:
    capture(state)
    count = state["te_count"]
    if type(count) is not int or not 2 <= count <= MAX_HOUSEHOLDS:
        raise ValueError(f"Use between 2 and {MAX_HOUSEHOLDS} households.")
    households = state["te_households"]
    defaults = default_households(count)
    state["te_households"] = [
        households[index] if index < len(households) else defaults[index]
        for index in range(count)
    ]
    if count != len(households):
        state["te_preset_name"] = "Custom"
    for index in range(count, MAX_HOUSEHOLDS):
        for field in HOUSEHOLD_FIELDS:
            state.pop(f"te_household_{field}_{index}", None)
        name = f"household_{index}"
        state.pop(f"te_open_{name}", None)
        state["te_expanded"].pop(name, None)


def reset(state: State) -> None:
    """Reset this run and draft, retaining an explicitly saved baseline."""
    baseline = state["te_baseline"]
    for key in list(state):
        if key.startswith("te_"):
            del state[key]
    state["te_baseline"] = baseline
    initialize(state)
    state["te_notice"] = (
        "Default setup restored. Your comparison baseline is still saved."
        if baseline is not None else
        "Default setup restored. Ready for a fresh experiment."
    )


def select_period(state: State) -> None:
    state["te_period_focus"] = state["te_selected"]


def remember_report_scope(state: State) -> None:
    state["te_saved_scope"] = state["te_report_scope"]


def submitted_settings(state: State) -> tuple[tuple[Household, ...], tuple[Firm, ...]]:
    """Construct immutable candidate settings from the editable draft."""
    return (
        tuple(Household(**item) for item in state["te_households"]),
        tuple(Firm(**item) for item in state["te_firms"]),
    )


def start(state: State) -> None:
    """Only replace a completed run after the candidate first period succeeds."""
    try:
        capture(state)
        households, firms = submitted_settings(state)
        Experiment(
            state["te_experiment_name"], households, firms, selected_firm=firms[0].id,
        )
        candidate = advance_period(households, firms)
    except (ValueError, ArithmeticError, AssertionError) as error:
        state["te_error"] = f"Could not start this setup: {error}"
        return
    state["te_history"] = [candidate]
    state["te_submitted"] = (households, firms)
    if state["te_selected_firm"] not in {firm.id for firm in firms}:
        state["te_selected_firm"] = firms[0].id
    state["te_selected"] = 1
    state["te_period_focus"] = 1
    state["te_error"] = None
    state["te_next_view"] = "Results"
    if name := state.pop("te_copy_name", None):
        state["te_experiment_name"] = name
        state["te_name_input"] = name


def next_period(state: State, count: int = 1) -> None:
    """Advance a whole requested batch atomically using submitted settings."""
    if type(count) is not int or count < 1:
        raise ValueError("Advance a positive whole number of periods.")
    history = state["te_history"]
    if not history or len(history) >= MAX_PERIODS:
        return
    households, firms = state["te_submitted"]
    pending = []
    previous = history[-1]
    try:
        for _ in range(min(count, MAX_PERIODS - len(history))):
            previous = advance_period(households, firms, previous=previous)
            pending.append(previous)
    except (ValueError, ArithmeticError, AssertionError) as error:
        state["te_error"] = f"Could not advance this economy: {error}"
        return
    state["te_history"] = [*history, *pending]
    state["te_selected"] = len(history) + len(pending)
    state["te_period_focus"] = len(history) + len(pending)
    state["te_error"] = None


def replace_draft(state: State, households, firms) -> None:
    """Replace draft settings and discard widgets bound to the previous draft."""
    household_settings = tuple(
        item if isinstance(item, Household) else Household(**item) for item in households
    )
    firm_settings = tuple(item if isinstance(item, Firm) else Firm(**item) for item in firms)
    Experiment(
        state["te_experiment_name"], household_settings, firm_settings,
        selected_firm=firm_settings[0].id,
    )
    for key in list(state):
        if key.startswith((
            "te_household_", "te_firm_", "te_open_household_", "te_open_firm_",
        )):
            del state[key]
    state["te_households"] = [asdict(item) for item in household_settings]
    state["te_firms"] = [asdict(item) for item in firm_settings]
    state["te_count"] = len(household_settings)
    if not state["te_history"] and state["te_selected_firm"] not in {
        firm.id for firm in firm_settings
    }:
        state["te_selected_firm"] = firm_settings[0].id
    state["te_expanded"] = {
        key: value for key, value in state["te_expanded"].items()
        if not key.startswith(("household_", "firm_"))
    }


def apply_preset(state: State, households, firms, name: str) -> None:
    replace_draft(state, households, firms)
    state.pop("te_copy_name", None)
    state["te_preset_name"] = name
    state["te_view"] = "Set up"
    state["te_error"] = None
    state["te_notice"] = (
        f"{name} settings loaded. Start a new simulation to apply them."
    )


def apply_household_preferences(state: State, source_index: int = 0) -> None:
    """Copy preferences and target explicitly; keep each household's money."""
    capture(state)
    households = state["te_households"]
    source = households[source_index]
    for index, household in enumerate(households):
        for field in (*PREFERENCE_FIELDS, "consumption_target"):
            household[field] = source[field]
            state[f"te_household_{field}_{index}"] = source[field]
    state["te_preset_name"] = "Custom"
    state["te_notice"] = (
        f"{source['name']} preferences and target copied to all households. "
        "Starting money is unchanged. Start a new simulation to apply this draft."
    )


def current_experiment(state: State) -> Experiment:
    history = tuple(state["te_history"])
    households, firms = submitted_settings(state)
    return Experiment(
        name=state["te_experiment_name"],
        draft_households=households, draft_firms=firms, periods=history,
        selected_period=min(state["te_period_focus"], len(history)) if history else 1,
        report_scope=state["te_saved_scope"],
        selected_firm=state["te_selected_firm"],
    )


def save_baseline(state: State) -> None:
    history = tuple(state["te_history"])
    if not history:
        return
    state["te_baseline"] = Experiment(
        name=state["te_experiment_name"],
        draft_households=history[0].households, draft_firms=history[0].firms,
        periods=history, selected_period=state["te_period_focus"],
        report_scope=state["te_saved_scope"], selected_firm=state["te_selected_firm"],
    )
    state["te_notice"] = "Baseline kept. Its results stay fixed while you try another setup."


def edit_baseline_copy(state: State) -> None:
    baseline = state["te_baseline"]
    if baseline is None:
        return
    replace_draft(state, baseline.periods[0].households, baseline.periods[0].firms)
    state["te_copy_name"] = f"{baseline.name[:60]} · variation"
    state["te_preset_name"] = "Custom"
    state["te_view"] = "Set up"
    state["te_error"] = None
    state["te_notice"] = (
        "Baseline settings copied. Change a setting, then start a new simulation. "
        "Current results change only when you start; the baseline stays fixed."
    )


def clear_baseline(state: State) -> None:
    state["te_baseline"] = None
    state.pop("te_copy_name", None)


def restore_experiment(state: State, data: bytes | str) -> None:
    """Validate both complete runs before making any state changes."""
    bundle = load_experiment(data)
    current = bundle.current
    history = list(current.periods)
    replace_draft(state, current.draft_households, current.draft_firms)
    state.update({
        "te_experiment_name": current.name, "te_name_input": current.name,
        "te_history": history,
        "te_submitted": (history[0].households, history[0].firms) if history else None,
        "te_baseline": bundle.baseline,
        "te_selected": current.selected_period, "te_period_focus": current.selected_period,
        "te_report_scope": current.report_scope, "te_saved_scope": current.report_scope,
        "te_selected_firm": current.selected_firm,
        "te_view": "Results" if history else "Set up", "te_error": None,
        "te_notice": "Experiment reopened. Your setup, results and baseline are restored.",
        "te_preset_name": "Custom",
    })
    for key in ("te_copy_name", "te_export_cache", "te_next_view"):
        state.pop(key, None)
