"""Portable, reproducible Economy 0.9 experiments, without a database.

Files store the editable draft separately from the submitted run. Completed
periods are represented by their full-precision settings and a SHA-256 digest of
each complete snapshot. Opening a file replays the supported engine and checks
every digest before returning anything to the caller. Thus an engine or runtime
change cannot silently rewrite saved accounts. Digests detect changed results;
they are not signatures or proof of who created an experiment.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass, fields, is_dataclass
from hashlib import sha256
from math import isfinite

from econ_agent_sim.economy_0_9 import (
    Economy09Period,
    Firm,
    Household,
    advance_investment_period,
)

FORMAT = "tiny-economy-experiment"
FORMAT_VERSION = 1
# Change this whenever the engine's numerical or accounting behavior changes.
ENGINE_VERSION = "investment-growth-0.9.1"
MAX_FILE_BYTES = 256 * 1024
MAX_PERIODS = 100
MAX_HOUSEHOLDS = 20
MAX_NAME_LENGTH = 80


class ExperimentError(ValueError):
    """An experiment cannot be safely saved or reopened."""


@dataclass(frozen=True)
class Experiment:
    name: str
    draft_households: tuple[Household, ...]
    draft_firm: Firm
    periods: tuple[Economy09Period, ...] = ()
    selected_period: int = 1
    report_scope: str = "This period"

    def __post_init__(self) -> None:
        # Detach caller-owned lists; each setting and period is already frozen.
        object.__setattr__(self, "draft_households", tuple(self.draft_households))
        object.__setattr__(self, "periods", tuple(self.periods))
        _name(self.name, "Experiment name")
        _settings(self.draft_households, self.draft_firm)
        if len(self.periods) > MAX_PERIODS:
            raise ExperimentError(f"An experiment supports up to {MAX_PERIODS} periods.")
        if self.periods:
            first = self.periods[0]
            if not isinstance(first, Economy09Period):
                raise ExperimentError("Use completed investment periods.")
            _settings(first.households, first.firm)
            for number, period in enumerate(self.periods, 1):
                if not isinstance(period, Economy09Period) or (
                    period.number != number
                    or period.households != first.households
                    or period.firm != first.firm
                ):
                    raise ExperimentError(
                        "Completed periods must start at 1 and use unchanged settings."
                    )
        if (
            type(self.selected_period) is not int
            or not 1 <= self.selected_period <= max(1, len(self.periods))
        ):
            raise ExperimentError("Choose a completed period in this experiment.")
        if self.report_scope not in ("This period", "Cumulative"):
            raise ExperimentError("Choose This period or Cumulative for the report.")


@dataclass(frozen=True)
class ExperimentFile:
    current: Experiment
    baseline: Experiment | None = None


def _name(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or not value.strip()
        or len(value) > MAX_NAME_LENGTH
        or any(ord(character) < 32 or ord(character) == 127 for character in value)
    ):
        raise ExperimentError(
            f"{label} needs 1–{MAX_NAME_LENGTH} characters without control characters."
        )
    return value


def _number(value: object, label: str, minimum: float, maximum: float) -> float:
    if (
        type(value) not in (int, float)
        or not isfinite(value)
        or not minimum <= value <= maximum
    ):
        raise ExperimentError(f"{label} must be between {minimum:g} and {maximum:g}.")
    return float(value)


def _entity_name(value: object, label: str) -> str:
    name = _name(value, label)
    if name.lstrip().startswith(("=", "+", "-", "@")):
        raise ExperimentError(f"{label} cannot start with a spreadsheet formula.")
    return name


def _object(value: object, keys: set[str], label: str) -> dict:
    if not isinstance(value, dict) or set(value) != keys:
        raise ExperimentError(f"The {label} fields are missing or unrecognized.")
    return value


def _parse_settings(value: object) -> tuple[tuple[Household, ...], Firm]:
    settings = _object(value, {"households", "firm"}, "settings")
    items = settings["households"]
    if not isinstance(items, list) or not 2 <= len(items) <= MAX_HOUSEHOLDS:
        raise ExperimentError(f"Use between 2 and {MAX_HOUSEHOLDS} households.")
    households = []
    household_fields = {field.name for field in fields(Household)}
    for item in items:
        item = _object(item, household_fields, "household")
        households.append(Household(
            name=_entity_name(item["name"], "Household name"),
            money=_number(item["money"], "Household money", 0, 1_000_000),
            **{
                field: _number(item[field], "Preference score", .01, 100)
                for field in household_fields - {"name", "money"}
            },
        ))
    item = _object(
        settings["firm"], {field.name for field in fields(Firm)}, "firm"
    )
    firm = Firm(
        name=_entity_name(item["name"], "Firm name"),
        money=_number(item["money"], "Operating money", .01, 1_000_000),
        capital=_number(item["capital"], "Starting capital", .1, 1_000_000),
        productivity=_number(item["productivity"], "Productivity", .1, 100),
        theta=_number(item["theta"], "Labor exponent", .5, .5),
        reinvestment_rate=_number(item["reinvestment_rate"], "Reinvestment", 0, .9),
        depreciation_rate=_number(item["depreciation_rate"], "Capital wear", 0, .9),
    )
    names = [household.name for household in households] + [firm.name]
    if len(set(names)) != len(names):
        raise ExperimentError("Households and the firm need unique names.")
    # A draft with zero household money can be saved even though it cannot run.
    return tuple(households), firm


def _settings(households: tuple[Household, ...], firm: Firm) -> dict:
    if not isinstance(firm, Firm) or any(
        not isinstance(household, Household) for household in households
    ):
        raise ExperimentError("Use household and firm settings for this economy.")
    result = {
        "households": [asdict(household) for household in households],
        "firm": asdict(firm),
    }
    validated_households, validated_firm = _parse_settings(result)
    return {
        "households": [asdict(household) for household in validated_households],
        "firm": asdict(validated_firm),
    }


def _plain(value: object) -> object:
    """Handle frozen snapshot mappings without deepcopy or pickle.

    JSON numbers are canonicalized to floats so a valid integer setting such as
    money=1 has the same digest after loading as the equivalent money=1.0.
    """
    if is_dataclass(value):
        return {field.name: _plain(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_plain(item) for item in value]
    if type(value) in (int, float):
        return float(value)
    return value


def _digest(period: Economy09Period) -> str:
    canonical = json.dumps(
        _plain(period), sort_keys=True, ensure_ascii=False,
        allow_nan=False, separators=(",", ":"),
    ).encode("utf-8")
    return sha256(canonical).hexdigest()


def _experiment_payload(experiment: Experiment) -> dict:
    if not isinstance(experiment, Experiment):
        raise ExperimentError("Choose an experiment to save.")
    run = None
    if experiment.periods:
        first = experiment.periods[0]
        run = {
            **_settings(first.households, first.firm),
            "period_digests": [_digest(period) for period in experiment.periods],
        }
    return {
        "name": experiment.name,
        "draft": _settings(experiment.draft_households, experiment.draft_firm),
        "run": run,
        "view": {
            "selected_period": experiment.selected_period,
            "report_scope": experiment.report_scope,
        },
    }


def dump_experiment(
    current: Experiment, *, baseline: Experiment | None = None
) -> bytes:
    """Save a complete workspace, including an optional independent baseline."""
    try:
        if baseline is not None and (
            not isinstance(baseline, Experiment) or not baseline.periods
        ):
            raise ExperimentError("A baseline needs at least one completed period.")
        payload = {
            "format": FORMAT,
            "format_version": FORMAT_VERSION,
            "engine_version": ENGINE_VERSION,
            "current": _experiment_payload(current),
            "baseline": _experiment_payload(baseline) if baseline is not None else None,
        }
        result = json.dumps(payload, ensure_ascii=False, allow_nan=False, indent=2)
        encoded = result.encode("utf-8")
    except (TypeError, ValueError, ArithmeticError) as error:
        if isinstance(error, ExperimentError):
            raise
        raise ExperimentError("These settings or results could not be saved.") from error
    if len(encoded) > MAX_FILE_BYTES:
        raise ExperimentError("This experiment exceeds the supported file size.")
    return encoded


def _unique_keys(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ExperimentError("The experiment contains duplicate fields.")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ExperimentError("Experiment numbers must be finite.")


def _restore(payload: object) -> Experiment:
    payload = _object(payload, {"name", "draft", "run", "view"}, "experiment")
    name = _name(payload["name"], "Experiment name")
    draft_households, draft_firm = _parse_settings(payload["draft"])
    view = _object(payload["view"], {"selected_period", "report_scope"}, "view")
    periods = []
    if payload["run"] is not None:
        run = _object(
            payload["run"], {"households", "firm", "period_digests"}, "run"
        )
        households, firm = _parse_settings({
            "households": run["households"], "firm": run["firm"],
        })
        digests = run["period_digests"]
        if not isinstance(digests, list) or not 1 <= len(digests) <= MAX_PERIODS:
            raise ExperimentError(f"A saved run needs 1–{MAX_PERIODS} completed periods.")
        if any(
            not isinstance(digest, str)
            or len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest)
            for digest in digests
        ):
            raise ExperimentError("The saved period checks are invalid.")
        previous = None
        for expected in digests:
            previous = advance_investment_period(households, firm, previous)
            if _digest(previous) != expected:
                raise ExperimentError(
                    "The saved accounts could not be reproduced exactly. The file "
                    "may have changed, or this runtime differs from the one that "
                    "saved it. Your current experiment has not been replaced."
                )
            periods.append(previous)
    return Experiment(
        name=name, draft_households=draft_households, draft_firm=draft_firm,
        periods=tuple(periods), selected_period=view["selected_period"],
        report_scope=view["report_scope"],
    )


def load_experiment(data: bytes | str) -> ExperimentFile:
    """Validate and reproduce the whole file before returning either experiment.

    Callers replace session state only after this function succeeds. No external
    files, URLs, imports, expressions or serialized Python objects are executed.
    """
    if not isinstance(data, (bytes, str)) or len(data) > MAX_FILE_BYTES:
        raise ExperimentError("Choose an experiment JSON file smaller than 256 KiB.")
    try:
        encoded = data.encode("utf-8") if isinstance(data, str) else data
        if len(encoded) > MAX_FILE_BYTES:
            raise ExperimentError("Choose an experiment JSON file smaller than 256 KiB.")
        payload = json.loads(
            encoded, object_pairs_hook=_unique_keys, parse_constant=_reject_constant
        )
        payload = _object(payload, {
            "format", "format_version", "engine_version", "current", "baseline",
        }, "file")
        if payload["format"] != FORMAT:
            raise ExperimentError("This is not a Tiny Economy experiment file.")
        if (
            type(payload["format_version"]) is not int
            or payload["format_version"] != FORMAT_VERSION
        ):
            raise ExperimentError("This experiment file version is not supported.")
        if payload["engine_version"] != ENGINE_VERSION:
            raise ExperimentError(
                "This experiment uses a different engine version. Its saved "
                "accounts cannot be safely reopened by this version of the app."
            )
        current = _restore(payload["current"])
        baseline = (
            _restore(payload["baseline"]) if payload["baseline"] is not None else None
        )
        if baseline is not None and not baseline.periods:
            raise ExperimentError("A baseline needs at least one completed period.")
        return ExperimentFile(current=current, baseline=baseline)
    except ExperimentError:
        raise
    except (ValueError, TypeError, ArithmeticError, RecursionError, AssertionError) as error:
        raise ExperimentError(
            "This file could not be reopened as a valid experiment. "
            "Your current experiment has not been replaced."
        ) from error
