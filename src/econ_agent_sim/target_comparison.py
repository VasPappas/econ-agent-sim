"""Compare soft consumption targets without changing either saved experiment."""

from math import isclose

from econ_agent_sim.competition_comparison import compare_competition_runs
from econ_agent_sim.economy_1_1 import Economy11Period
from econ_agent_sim.target_reporting import target_report


def compare_target_runs(
    current_periods, baseline_periods, *, selected_period: int,
    cumulative: bool = False, current_name: str = "Current", baseline_name: str = "Baseline",
) -> dict:
    """Compare original-price accounts and per-household, per-period shortfalls."""
    current_periods, baseline_periods = tuple(current_periods), tuple(baseline_periods)
    if any(
        not isinstance(period, Economy11Period)
        for history in (current_periods, baseline_periods) for period in history
    ):
        raise ValueError("Compare experiments using the same Economy 1.1 engine.")
    comparison = compare_competition_runs(
        current_periods, baseline_periods, selected_period=selected_period,
        cumulative=cumulative, current_name=current_name, baseline_name=baseline_name,
    )
    comparison["model"] = "consumption_target"
    if current_periods and baseline_periods:
        old_by_id = {entry.id: entry for entry in baseline_periods[0].households}
        new_by_id = {entry.id: entry for entry in current_periods[0].households}
        for identity in dict.fromkeys((*old_by_id, *new_by_id)):
            old, new = old_by_id.get(identity), new_by_id.get(identity)
            if old and new and isclose(
                old.consumption_target, new.consumption_target,
                rel_tol=1e-12, abs_tol=0.0,
            ):
                continue
            comparison["settings_changes"].append({
                "entity_id": identity, "entity": (new or old).name,
                "label": "Consumption target", "unit": "X / period",
                "baseline": old.consumption_target if old else "—",
                "current": new.consumption_target if new else "—",
            })
    if comparison["available"]:
        current = target_report(current_periods[:selected_period], cumulative)
        baseline = target_report(baseline_periods[:selected_period], cumulative)
        new = current["economy"]["shortfall_x"]
        old = baseline["economy"]["shortfall_x"]
        comparison["metrics"].append({
            "key": "shortfall", "label": "Below-target X", "unit": "X",
            "baseline": old, "current": new, "change": new - old,
            "change_unit": "X",
        })
        comparison["note"] += (
            " Below-target X sums individual period shortfalls without offsetting "
            "them against extra consumption. Each run uses its own consumption "
            "targets; changed targets are listed with the changed settings."
        )
    return comparison
