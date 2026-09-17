"""Versioned portable workspaces for the current Tiny Economy model.

The editable draft and submitted run are separate. Opening replays the exact
supported engine and checks complete immutable snapshots before exposing any
replacement state. Fingerprints detect changed results; they are not signatures.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import asdict, dataclass, fields, is_dataclass
from hashlib import sha256
from math import isfinite

from econ_agent_sim.engine import (
    EconomyPeriod,
    Firm,
    Household,
    advance_period,
)

FORMAT = "tiny-economy-experiment"
FORMAT_VERSION = 5
MODEL = "tiny_economy"
# Bump whenever solving, settlement or accounting changes saved snapshots.
ENGINE_VERSION = "tiny-economy-3.0.0"
LEGACY_FORMAT_VERSION = 4
LEGACY_ENGINE_VERSION = "tiny-economy-2.0.0"
_NEW_FIRM_FIELDS = {"investment_policy", "required_return"}
MAX_FILE_BYTES = 256 * 1024
MAX_PERIODS = 100
MAX_HOUSEHOLDS = 20
MAX_NAME_LENGTH = 80


class ExperimentError(ValueError):
    """A workspace cannot be safely saved or reopened."""


class RetiredExperimentError(ExperimentError):
    """A historical file must not be reinterpreted with changed economic rules."""


@dataclass(frozen=True)
class Experiment:
    name: str
    draft_households: tuple[Household, ...]
    draft_firms: tuple[Firm, ...]
    periods: tuple[EconomyPeriod, ...] = ()
    selected_period: int = 1
    report_scope: str = "This period"
    selected_firm: str = "firm_a"

    def __post_init__(self) -> None:
        object.__setattr__(self, "draft_households", tuple(self.draft_households))
        object.__setattr__(self, "draft_firms", tuple(self.draft_firms))
        object.__setattr__(self, "periods", tuple(self.periods))
        validate_experiment_name(self.name)
        _settings(self.draft_households, self.draft_firms)
        if len(self.periods) > MAX_PERIODS:
            raise ExperimentError(f"An experiment supports up to {MAX_PERIODS} periods.")
        firms = self.draft_firms
        if self.periods:
            first = self.periods[0]
            if not isinstance(first, EconomyPeriod):
                raise ExperimentError("Use completed Tiny Economy periods.")
            _settings(first.households, first.firms)
            firms = first.firms
            for number, period in enumerate(self.periods, 1):
                if not isinstance(period, EconomyPeriod) or (
                    period.number != number
                    or period.households != first.households
                    or period.firms != first.firms
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
        if self.selected_firm not in tuple(firm.id for firm in firms):
            raise ExperimentError("Choose a firm in this experiment.")


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
    if any(0xD800 <= ord(character) <= 0xDFFF for character in value):
        raise ExperimentError(f"{label} must contain valid Unicode text.")
    return value


def validate_experiment_name(value: object) -> str:
    """Validate editable labels before publishing them to the workspace."""
    return _name(value, "Experiment name")


def _entity_name(value: object, label: str) -> str:
    name = _name(value, label)
    if name.lstrip().startswith(("=", "+", "-", "@")):
        raise ExperimentError(f"{label} cannot start with a spreadsheet formula.")
    return name


def _entity_id(value: object) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", value) is None:
        raise ExperimentError("Entity IDs need letters, numbers, underscores or hyphens.")
    return value


def _number(value: object, label: str, minimum: float, maximum: float) -> float:
    if (
        type(value) not in (int, float)
        or not isfinite(value)
        or not minimum <= value <= maximum
    ):
        raise ExperimentError(f"{label} must be between {minimum:g} and {maximum:g}.")
    return float(value)


def _object(value: object, keys: set[str], label: str) -> dict:
    if not isinstance(value, dict) or set(value) != keys:
        raise ExperimentError(f"The {label} fields are missing or unrecognized.")
    return value


def _investment_policy(value: object) -> str:
    if not isinstance(value, str) or value not in ("percentage", "user_cost"):
        raise ExperimentError("Choose percentage or user_cost for the investment policy.")
    return value


def _parse_settings(
    value: object, *, legacy: bool = False,
) -> tuple[tuple[Household, ...], tuple[Firm, ...]]:
    settings = _object(value, {"households", "firms"}, "settings")
    items = settings["households"]
    if not isinstance(items, list) or not 2 <= len(items) <= MAX_HOUSEHOLDS:
        raise ExperimentError(f"Use between 2 and {MAX_HOUSEHOLDS} households.")
    household_fields = {field.name for field in fields(Household)}
    households = []
    for item in items:
        item = _object(item, household_fields, "household")
        households.append(Household(
            id=_entity_id(item["id"]),
            name=_entity_name(item["name"], "Household name"),
            money=_number(item["money"], "Household money", 0, 1_000_000),
            consumption_target=_number(
                item["consumption_target"], "Consumption target", 0, 100,
            ),
            **{
                field: _number(item[field], "Preference score", .01, 100)
                for field in household_fields - {"id", "name", "money", "consumption_target"}
            },
        ))
    items = settings["firms"]
    if not isinstance(items, list) or len(items) != 2:
        raise ExperimentError("This economy needs exactly two firms.")
    firms = []
    firm_fields = {field.name for field in fields(Firm)}
    if legacy:
        firm_fields -= _NEW_FIRM_FIELDS
    for item in items:
        item = _object(item, firm_fields, "firm")
        firms.append(Firm(
            id=_entity_id(item["id"]),
            name=_entity_name(item["name"], "Firm name"),
            money=_number(item["money"], "Operating money", .01, 1_000_000),
            capital=_number(item["capital"], "Starting capital", .1, 1_000_000),
            productivity=_number(item["productivity"], "Productivity", .1, 100),
            theta=_number(item["theta"], "Labor exponent", .5, .5),
            reinvestment_rate=_number(item["reinvestment_rate"], "Reinvestment", 0, .9),
            depreciation_rate=_number(item["depreciation_rate"], "Capital wear", 0, .9),
            investment_policy="percentage" if legacy else _investment_policy(
                item["investment_policy"],
            ),
            required_return=.05 if legacy else _number(
                item["required_return"], "Required return", 0, 1,
            ),
        ))
    ids = [entity.id for entity in (*households, *firms)]
    if len(set(ids)) != len(ids):
        raise ExperimentError("Households and firms need unique IDs.")
    # Zero aggregate household cash is a savable draft, though it cannot run.
    return tuple(households), tuple(firms)


def _settings(households: tuple[Household, ...], firms: tuple[Firm, ...]) -> dict:
    if any(not isinstance(item, Household) for item in households) or any(
        not isinstance(item, Firm) for item in firms
    ):
        raise ExperimentError("Use household and firm settings for this economy.")
    validated_households, validated_firms = _parse_settings({
        "households": [asdict(item) for item in households],
        "firms": [asdict(item) for item in firms],
    })
    return {
        "households": [asdict(item) for item in validated_households],
        "firms": [asdict(item) for item in validated_firms],
    }


def _plain(value: object, *, legacy: bool = False) -> object:
    """Canonicalize every snapshot field, including frozen nested mappings."""
    if is_dataclass(value):
        return {
            field.name: _plain(getattr(value, field.name), legacy=legacy)
            for field in fields(value)
            if not (legacy and isinstance(value, Firm) and field.name in _NEW_FIRM_FIELDS)
        }
    if isinstance(value, Mapping):
        return {key: _plain(item, legacy=legacy) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_plain(item, legacy=legacy) for item in value]
    if type(value) in (int, float):
        return float(value)
    return value


def _digest(period: EconomyPeriod, *, legacy: bool = False) -> str:
    if legacy and any(
        firm.investment_policy != "percentage" or firm.required_return != .05
        for firm in period.firms
    ):
        raise ExperimentError("Only migrated percentage settings have legacy period checks.")
    canonical = json.dumps(
        _plain(period, legacy=legacy), sort_keys=True, ensure_ascii=False,
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
            **_settings(first.households, first.firms),
            "period_digests": [_digest(period) for period in experiment.periods],
        }
    return {
        "name": experiment.name,
        "draft": _settings(experiment.draft_households, experiment.draft_firms),
        "run": run,
        "view": {
            "selected_period": experiment.selected_period,
            "report_scope": experiment.report_scope,
            "selected_firm": experiment.selected_firm,
        },
    }


def dump_experiment(current: Experiment, *, baseline: Experiment | None = None) -> bytes:
    """Save both firms, every completed period, draft edits and a frozen baseline."""
    try:
        if baseline is not None and (
            not isinstance(baseline, Experiment) or not baseline.periods
        ):
            raise ExperimentError("A baseline needs at least one completed period.")
        payload = {
            "format": FORMAT, "format_version": FORMAT_VERSION,
            "model": MODEL, "engine_version": ENGINE_VERSION,
            "current": _experiment_payload(current),
            "baseline": _experiment_payload(baseline) if baseline is not None else None,
        }
        encoded = json.dumps(
            payload, ensure_ascii=False, allow_nan=False, indent=2,
        ).encode("utf-8")
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


def _restore(payload: object, *, legacy: bool = False) -> Experiment:
    payload = _object(payload, {"name", "draft", "run", "view"}, "experiment")
    name = validate_experiment_name(payload["name"])
    households_draft, firms_draft = _parse_settings(payload["draft"], legacy=legacy)
    view = _object(
        payload["view"], {"selected_period", "report_scope", "selected_firm"}, "view",
    )
    periods = []
    if payload["run"] is not None:
        run = _object(payload["run"], {"households", "firms", "period_digests"}, "run")
        households, firms = _parse_settings({
            "households": run["households"], "firms": run["firms"],
        }, legacy=legacy)
        digests = run["period_digests"]
        if not isinstance(digests, list) or not 1 <= len(digests) <= MAX_PERIODS:
            raise ExperimentError(f"A saved run needs 1–{MAX_PERIODS} completed periods.")
        if any(
            not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None
            for digest in digests
        ):
            raise ExperimentError("The saved period checks are invalid.")
        previous = None
        for expected in digests:
            previous = advance_period(households, firms, previous)
            if _digest(previous, legacy=legacy) != expected:
                raise ExperimentError(
                    "The saved accounts could not be reproduced exactly. The file "
                    "may have changed, or this runtime differs from the one that "
                    "saved it. Your current experiment has not been replaced."
                )
            periods.append(previous)
    return Experiment(
        name, households_draft, firms_draft, tuple(periods),
        view["selected_period"], view["report_scope"], view["selected_firm"],
    )


def load_experiment(data: bytes | str) -> ExperimentFile:
    """Reproduce the whole workspace before returning any replacement state."""
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
            isinstance(payload, dict)
            and payload.get("format") == FORMAT
            and type(payload.get("format_version")) is int
            and 1 <= payload["format_version"] < LEGACY_FORMAT_VERSION
        ):
            raise RetiredExperimentError(
                "This file was saved by a retired model. Its results cannot be "
                "reopened in the current Tiny Economy because the economic rules "
                "have changed. Start a new experiment and enter the settings you "
                "want to explore. Your current experiment has not been replaced."
            )
        payload = _object(payload, {
            "format", "format_version", "model", "engine_version", "current", "baseline",
        }, "file")
        if payload["format"] != FORMAT:
            raise ExperimentError("This is not a Tiny Economy experiment file.")
        version = payload["format_version"]
        if type(version) is not int or version not in (LEGACY_FORMAT_VERSION, FORMAT_VERSION):
            raise ExperimentError("This experiment file version is not supported.")
        if payload["model"] != MODEL:
            raise ExperimentError("This experiment belongs to a different economy.")
        legacy = version == LEGACY_FORMAT_VERSION
        expected_engine = LEGACY_ENGINE_VERSION if legacy else ENGINE_VERSION
        if payload["engine_version"] != expected_engine:
            raise ExperimentError(
                "This experiment uses a different engine version. Its saved "
                "accounts cannot be safely reopened by this version of the app."
            )
        current = _restore(payload["current"], legacy=legacy)
        baseline = (
            _restore(payload["baseline"], legacy=legacy)
            if payload["baseline"] is not None else None
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
