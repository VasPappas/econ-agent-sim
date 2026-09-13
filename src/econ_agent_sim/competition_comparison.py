"""Compare two-firm experiments at a shared date without extending either run."""

from math import isclose

from econ_agent_sim.competition_reporting import competition_report
from econ_agent_sim.economy_1_0 import Economy10Period


def _settings_changes(current, baseline):
    changes = []

    def add(identity, entity, label, old, new, unit=""):
        same = old == new if isinstance(old, str) or isinstance(new, str) else isclose(
            old, new, rel_tol=1e-12, abs_tol=0.0
        )
        if not same:
            changes.append({
                "entity_id": identity, "entity": entity, "label": label,
                "baseline": old, "current": new, "unit": unit,
            })

    add("economy", "Economy", "Households", len(baseline.households), len(current.households))
    for kind, old_entries, new_entries in (
        ("firm", baseline.firms, current.firms),
        ("household", baseline.households, current.households),
    ):
        old_by_id = {entry.id: entry for entry in old_entries}
        new_by_id = {entry.id: entry for entry in new_entries}
        for identity in dict.fromkeys((*old_by_id, *new_by_id)):
            old, new = old_by_id.get(identity), new_by_id.get(identity)
            name = (new or old).name
            if kind == "firm":
                for field, label, unit, factor in (
                    ("money", "Operating money", "M", 1),
                    ("capital", "Starting capital", "capital units", 1),
                    ("productivity", "Productivity", "", 1),
                    ("reinvestment_rate", "Reinvest surplus", "%", 100),
                    ("depreciation_rate", "Capital wear", "%", 100),
                ):
                    add(identity, name, label,
                        getattr(old, field) * factor if old else "—",
                        getattr(new, field) * factor if new else "—", unit)
            else:
                add(identity, name, "Starting money", old.money if old else "—",
                    new.money if new else "—", "M")
                for key, label in (
                    ("consumption", "Consume preference"),
                    ("money", "Money preference"),
                    ("leisure", "Leisure preference"),
                ):
                    add(identity, name, label, old.weights[key] * 100 if old else "—",
                        new.weights[key] * 100 if new else "—", "%")
    return changes


def _metric(key, label, unit, current, baseline, *, change_unit=None):
    return {
        "key": key, "label": label, "unit": unit,
        "baseline": baseline, "current": current, "change": current - baseline,
        "change_unit": change_unit or unit,
    }


def compare_competition_runs(
    current_periods, baseline_periods, *, selected_period: int,
    cumulative: bool = False, current_name: str = "Current", baseline_name: str = "Baseline",
) -> dict:
    """Compare original-price flows, closing stocks and selected-period rates.

    Stable firm IDs, not labels or array positions, match firm accounts. A short
    history returns an unavailable comparison; no solve or mutation occurs here.
    """
    if type(selected_period) is not int or selected_period < 1:
        raise ValueError("Choose a positive whole period for comparison.")
    current_periods, baseline_periods = tuple(current_periods), tuple(baseline_periods)
    for history in (current_periods, baseline_periods):
        if any(not isinstance(period, Economy10Period) for period in history):
            raise ValueError("Compare experiments using the same Economy 1.0 engine.")
        if any(period.number != index for index, period in enumerate(history, 1)):
            raise ValueError("A comparison needs consecutive histories beginning at Period 1.")
    comparable = min(len(current_periods), len(baseline_periods))
    result = {
        "available": False, "through_period": selected_period,
        "comparable_through": comparable, "scope": "cumulative" if cumulative else "period",
        "label": f"Periods 1–{selected_period}" if cumulative and selected_period > 1 else f"Period {selected_period}",
        "current_name": current_name, "baseline_name": baseline_name,
        "metrics": [], "firms": [], "settings_changes": [],
    }
    if current_periods and baseline_periods:
        result["settings_changes"] = _settings_changes(current_periods[0], baseline_periods[0])
    if selected_period > comparable:
        shared = (
            f"They currently share Periods 1–{comparable}." if comparable > 1
            else "They currently share Period 1." if comparable == 1
            else "Start both simulations first."
        )
        result["note"] = f"Both experiments need Period {selected_period} to compare it. {shared}"
        return result

    current = competition_report(current_periods[:selected_period], cumulative)
    baseline = competition_report(baseline_periods[:selected_period], cumulative)
    for key, label, unit, section, field, factor in (
        ("consumption", "Consumed X", "X", "economy", "consumed_x", 1),
        ("capital", "Closing capital", "capital units", "economy", "capital_close", 1),
        ("work", "Average work", "%", "economy", "average_work", 100),
        ("price", "X price", "M / X", None, "price", 1),
        ("real_wage", "Wage buys", "X / work unit", None, "real_wage", 1),
        ("profit", "Net firm profit", "M", "economy", "net_operating_profit", 1),
    ):
        new = (current[section] if section else current)[field] * factor
        old = (baseline[section] if section else baseline)[field] * factor
        result["metrics"].append(_metric(
            key, label, unit, new, old, change_unit="pp" if key == "work" else unit
        ))
    baseline_firms = {entry["entity_id"]: entry for entry in baseline["firms"]}
    for firm in current["firms"]:
        old = baseline_firms.get(firm["entity_id"])
        comparison = {
            "entity_id": firm["entity_id"], "name": firm["name"],
            "available": old is not None, "metrics": [],
        }
        if old is None:
            comparison["note"] = "This firm has no matching identity in the baseline."
        else:
            for key, label, unit, field, factor in (
                ("production", "Produced X", "X", "produced_x", 1),
                ("sales_share", "Share of sales", "%", "sales_share", 100),
                ("profit", "Net profit", "M", "net_operating_profit", 1),
                ("capital", "Closing capital", "capital units", "capital_close", 1),
            ):
                comparison["metrics"].append(_metric(
                    key, label, unit, firm[field] * factor, old[field] * factor,
                    change_unit="pp" if key == "sales_share" else unit,
                ))
        result["firms"].append(comparison)
    result.update(
        available=True,
        note=(
            "Production, consumption and profit cover this report range. Capital is the closing stock; "
            "work is the household average. Sales shares use total physical X sold over the range. "
            f"Price and wage purchasing power are from Period {selected_period}. "
            "Monetary flows keep each period’s original prices. Differences show current minus baseline."
        ),
    )
    return result
