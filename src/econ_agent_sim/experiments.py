"""Portable workspaces with strict schemas and complete monetary-plan replay.

Editable inputs, the submitted plan and the baseline have separate lifetimes.
Every saved period is checked against a freshly certified plan before import
replaces state. Earlier economic models are deliberately not reinterpreted.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, MutableMapping
from dataclasses import asdict, dataclass, fields
from math import isclose, isfinite
from typing import Any

from econ_agent_sim.domain import ENGINE_VERSION, MAX_PERIODS, MODEL_ID, Settings
from econ_agent_sim.engine import Run, simulate
from econ_agent_sim.monetary_growth import Period

FORMAT = "tiny-economy-experiment"
FORMAT_VERSION = 6
MAX_FILE_BYTES = 256 * 1024
MAX_NAME_LENGTH = 80
REPLAY_REL_TOLERANCE = 1e-9
REPLAY_ABS_TOLERANCE = 1e-11


class ExperimentError(ValueError):
    """A workspace cannot be safely saved or reopened."""


class RetiredExperimentError(ExperimentError):
    """A historical file belongs to a different economic model."""


def validate_experiment_name(value: object) -> str:
    if (
        not isinstance(value, str) or not value.strip() or len(value) > MAX_NAME_LENGTH
        or any(ord(char) < 32 or ord(char) == 127 for char in value)
        or any(0xD800 <= ord(char) <= 0xDFFF for char in value)
    ):
        raise ExperimentError(
            f"Experiment name needs 1–{MAX_NAME_LENGTH} valid text characters "
            "without control characters."
        )
    return value


def _count(value: object, *, minimum: int, maximum: int, label: str) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise ExperimentError(f"{label} must be a whole number from {minimum} to {maximum}.")
    return value


def _run_valid(run: Run) -> None:
    if type(run) is not Run or type(run.settings) is not Settings:
        raise ExperimentError("Use a completed plan from the current economy.")
    if not run.solution.converged or len(run.periods) != MAX_PERIODS:
        raise ExperimentError(f"A saved run needs a certified {MAX_PERIODS}-period plan.")


@dataclass(frozen=True)
class Baseline:
    run: Run
    visible_periods: int
    name: str

    def __post_init__(self) -> None:
        _run_valid(self.run)
        validate_experiment_name(self.name)
        _count(self.visible_periods, minimum=1, maximum=MAX_PERIODS, label="Visible periods")


@dataclass(frozen=True)
class Experiment:
    name: str
    draft: Settings
    run: Run | None = None
    visible_periods: int = 0
    selected_period: int = 1
    scope: str = "This period"
    view: str = "Set up"

    def __post_init__(self) -> None:
        validate_experiment_name(self.name)
        if type(self.draft) is not Settings:
            raise ExperimentError("Use the current economy's draft settings.")
        if self.run is not None:
            _run_valid(self.run)
        _validate_navigation(
            self.visible_periods, self.selected_period, self.scope, self.view,
            has_run=self.run is not None,
        )


@dataclass(frozen=True)
class ExperimentFile:
    current: Experiment
    baseline: Baseline | None = None


def _validate_navigation(visible, selected, scope, view, *, has_run):
    _count(
        visible, minimum=1 if has_run else 0, maximum=MAX_PERIODS if has_run else 0,
        label="Visible periods",
    )
    _count(selected, minimum=1, maximum=max(1, visible), label="Selected period")
    if scope not in ("This period", "Cumulative"):
        raise ExperimentError("Choose This period or Cumulative for the report.")
    if view not in ("Set up", "Results", "Ask why"):
        raise ExperimentError("Choose a recognized workspace view.")


def _object(value: object, keys: set[str], label: str) -> dict:
    if not isinstance(value, dict) or set(value) != keys:
        raise ExperimentError(f"The {label} fields are missing or unrecognized.")
    return value


def _settings(value: object) -> Settings:
    value = _object(value, {field.name for field in fields(Settings)}, "settings")
    try:
        return Settings(**value)
    except (ValueError, TypeError, ArithmeticError) as error:
        raise ExperimentError(f"The saved settings are invalid: {error}") from error


def _snapshot(value: object, number: int) -> dict:
    value = _object(value, {field.name for field in fields(Period)}, "period")
    if type(value["number"]) is not int or value["number"] != number:
        raise ExperimentError("Saved periods must be numbered consecutively from 1.")
    for key, item in value.items():
        if key == "number" or (key == "next_capital_shadow_value" and item is None):
            continue
        if type(item) not in (int, float) or not isfinite(item):
            raise ExperimentError("Saved period quantities must be finite numbers.")
    return value


def _run_payload(run: Run | None) -> dict | None:
    if run is None:
        return None
    _run_valid(run)
    return {
        "settings": asdict(run.settings),
        "periods": [_snapshot(asdict(row), i) for i, row in enumerate(run.periods, 1)],
    }


def dump_experiment(current: Experiment, *, baseline: Baseline | None = None) -> bytes:
    """Save complete plans, including periods not yet revealed in the interface."""
    try:
        if type(current) is not Experiment:
            raise ExperimentError("Choose a current experiment to save.")
        if baseline is not None and type(baseline) is not Baseline:
            raise ExperimentError("Choose a saved comparison baseline.")
        payload = {
            "format": FORMAT, "format_version": FORMAT_VERSION,
            "model": MODEL_ID, "engine_version": ENGINE_VERSION,
            "current": {
                "name": current.name, "draft": asdict(current.draft),
                "run": _run_payload(current.run),
                "visible_periods": current.visible_periods,
                "selected_period": current.selected_period,
                "scope": current.scope, "view": current.view,
            },
            "baseline": None if baseline is None else {
                "name": baseline.name, "run": _run_payload(baseline.run),
                "visible_periods": baseline.visible_periods,
            },
        }
        encoded = json.dumps(
            payload, ensure_ascii=False, allow_nan=False, separators=(",", ":"),
        ).encode("utf-8")
    except ExperimentError:
        raise
    except (TypeError, ValueError, ArithmeticError) as error:
        raise ExperimentError("These settings or results could not be saved.") from error
    if len(encoded) > MAX_FILE_BYTES:
        raise ExperimentError("This experiment exceeds the supported 256 KiB file size.")
    return encoded


def dumps_experiment(state: Mapping[str, Any]) -> str:
    current = Experiment(
        state["te_name"], state["te_draft"], state["te_run"],
        state["te_visible_periods"], state["te_selected_period"],
        state["te_scope"], state["te_view"],
    )
    return dump_experiment(current, baseline=state["te_baseline"]).decode("utf-8")


def _unique_keys(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ExperimentError("The experiment contains duplicate fields.")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ExperimentError("Experiment numbers must be finite.")


def _parse_run(value: object) -> tuple[Settings, list[dict]] | None:
    if value is None:
        return None
    value = _object(value, {"settings", "periods"}, "run")
    settings = _settings(value["settings"])
    periods = value["periods"]
    if not isinstance(periods, list) or len(periods) != MAX_PERIODS:
        raise ExperimentError(f"A saved run needs the complete {MAX_PERIODS}-period plan.")
    return settings, [_snapshot(row, i) for i, row in enumerate(periods, 1)]


def _replay(parsed: tuple[Settings, list[dict]] | None) -> Run | None:
    if parsed is None:
        return None
    settings, saved = parsed
    run = simulate(settings)
    _run_valid(run)
    for actual, expected in zip(run.periods, saved, strict=True):
        for key, value in asdict(actual).items():
            old = expected[key]
            equal = (
                old is None if value is None else
                old is not None and isclose(
                    value, old, rel_tol=REPLAY_REL_TOLERANCE,
                    abs_tol=REPLAY_ABS_TOLERANCE,
                )
            )
            if not equal:
                raise ExperimentError(
                    "The saved plan could not be reproduced within numerical tolerance. "
                    "The file may have changed or this runtime gives different results. "
                    "Your current experiment has not been replaced."
                )
    # Saved numbers never become the running economy; use the new certified solve.
    return run


def load_experiment(data: bytes | str) -> ExperimentFile:
    """Validate the entire schema, then replay both plans before returning state."""
    if not isinstance(data, (bytes, str)) or len(data) > MAX_FILE_BYTES:
        raise ExperimentError("Choose an experiment JSON file smaller than 256 KiB.")
    try:
        encoded = data.encode("utf-8") if isinstance(data, str) else data
        if len(encoded) > MAX_FILE_BYTES:
            raise ExperimentError("Choose an experiment JSON file smaller than 256 KiB.")
        payload = json.loads(
            encoded, object_pairs_hook=_unique_keys, parse_constant=_reject_constant,
        )
        if (
            isinstance(payload, dict) and payload.get("format") == FORMAT
            and type(payload.get("format_version")) is int
            and 1 <= payload["format_version"] < FORMAT_VERSION
        ):
            raise RetiredExperimentError(
                "This file belongs to an earlier Tiny Economy model. Its settings and "
                "results cannot be reopened under the new forward-looking economic "
                "rules. Keep the original file for reference and start a new experiment. "
                "Your current experiment has not been replaced."
            )
        payload = _object(payload, {
            "format", "format_version", "model", "engine_version", "current", "baseline",
        }, "file")
        if payload["format"] != FORMAT:
            raise ExperimentError("This is not a Tiny Economy experiment file.")
        version = payload["format_version"]
        if type(version) is not int or version != FORMAT_VERSION:
            raise ExperimentError("This experiment file version is not supported.")
        if payload["model"] != MODEL_ID:
            raise ExperimentError("This experiment belongs to a different economic model.")
        if payload["engine_version"] != ENGINE_VERSION:
            raise ExperimentError("This experiment uses a different engine version.")
        current = _object(payload["current"], {
            "name", "draft", "run", "visible_periods", "selected_period", "scope", "view",
        }, "experiment")
        name = validate_experiment_name(current["name"])
        draft = _settings(current["draft"])
        parsed_run = _parse_run(current["run"])
        _validate_navigation(
            current["visible_periods"], current["selected_period"],
            current["scope"], current["view"], has_run=parsed_run is not None,
        )
        baseline = payload["baseline"]
        parsed_baseline = None
        if baseline is not None:
            baseline = _object(baseline, {"name", "run", "visible_periods"}, "baseline")
            validate_experiment_name(baseline["name"])
            parsed_baseline = _parse_run(baseline["run"])
            if parsed_baseline is None:
                raise ExperimentError("A baseline needs a completed plan.")
            _count(
                baseline["visible_periods"], minimum=1, maximum=MAX_PERIODS,
                label="Baseline visible periods",
            )
        run = _replay(parsed_run)
        baseline_run = _replay(parsed_baseline)
        return ExperimentFile(
            current=Experiment(
                name, draft, run, current["visible_periods"], current["selected_period"],
                current["scope"], current["view"],
            ),
            baseline=None if baseline is None else Baseline(
                baseline_run, baseline["visible_periods"], baseline["name"],
            ),
        )
    except ExperimentError:
        raise
    except (ValueError, TypeError, ArithmeticError, RecursionError) as error:
        raise ExperimentError(
            "This file could not be reopened as a valid experiment. "
            "Your current experiment has not been replaced."
        ) from error


def restore_experiment(state: MutableMapping[str, Any], data: bytes | str) -> bool:
    """Commit a checked import atomically; preserve active state on failure."""
    try:
        bundle = load_experiment(data)
    except ExperimentError as error:
        state["te_error"] = f"Could not reopen this experiment: {error}"
        return False
    current = bundle.current
    state.update({
        "te_model_id": MODEL_ID, "te_name": current.name, "te_draft": current.draft,
        "te_run": current.run, "te_visible_periods": current.visible_periods,
        "te_selected_period": current.selected_period, "te_scope": current.scope,
        "te_view": current.view, "te_baseline": bundle.baseline, "te_error": None,
        "te_notice": "Experiment reopened. Your setup, results and baseline are restored.",
    })
    return True
