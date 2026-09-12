"""Compare frozen investment runs at an explicitly shared reporting horizon."""

from itertools import zip_longest
from math import isclose

from econ_agent_sim.economy_0_9 import Economy09Period, investment_report


def _settings_changes(current: Economy09Period, baseline: Economy09Period) -> list[dict]:
    changes = []

    def add(entity, label, old, new, unit=""):
        same = old == new if isinstance(old, str) or isinstance(new, str) else (
            isclose(old, new, rel_tol=1e-12, abs_tol=0.0)
        )
        if not same:
            changes.append({
                "entity": entity, "label": label, "baseline": old,
                "current": new, "unit": unit,
            })

    add("Economy", "Households", len(baseline.households), len(current.households))
    for field, label, unit, factor in (
        ("money", "Operating money", "M", 1),
        ("capital", "Starting capital", "capital units", 1),
        ("productivity", "Productivity", "", 1),
        ("theta", "Labor exponent", "", 1),
        ("reinvestment_rate", "Reinvest surplus", "%", 100),
        ("depreciation_rate", "Capital wear", "%", 100),
    ):
        add("Firm", label, getattr(baseline.firm, field) * factor,
            getattr(current.firm, field) * factor, unit)
    # Household positions are the stable IDs used by the reports and ledger.
    # Compare normalized preferences: scaling all three scores is no new choice.
    for index, (old, new) in enumerate(zip_longest(baseline.households, current.households)):
        entity = f"Household {index + 1}"
        add(entity, "Starting money", old.money if old else "—",
            new.money if new else "—", "M")
        for key, label in (
            ("consumption", "Consume preference"),
            ("money", "Money preference"),
            ("leisure", "Leisure preference"),
        ):
            add(entity, label, old.weights[key] * 100 if old else "—",
                new.weights[key] * 100 if new else "—", "%")
    return changes


def compare_investment_runs(
    current_periods: tuple[Economy09Period, ...],
    baseline_periods: tuple[Economy09Period, ...],
    *,
    selected_period: int,
    cumulative: bool = False,
    current_name: str = "Current",
    baseline_name: str = "Baseline",
) -> dict:
    """Flows retain original prices; stocks and rates belong to selected_period.

    A shorter run yields an unavailable comparison instead of silently comparing
    different dates. No experiment is advanced or changed to create a comparison.
    """
    if type(selected_period) is not int or selected_period < 1:
        raise ValueError("Choose a positive whole period for comparison.")
    comparable = min(len(current_periods), len(baseline_periods))
    result = {
        "available": False, "through_period": selected_period,
        "comparable_through": comparable,
        "scope": "cumulative" if cumulative else "period",
        "label": f"Periods 1–{selected_period}"
        if cumulative and selected_period > 1 else f"Period {selected_period}",
        "current_name": current_name, "baseline_name": baseline_name,
        "metrics": [], "settings_changes": [],
    }
    if current_periods and baseline_periods:
        result["settings_changes"] = _settings_changes(
            current_periods[0], baseline_periods[0]
        )
    if selected_period > comparable:
        result["note"] = (
            f"Both experiments need Period {selected_period} to compare it. "
            + (f"They currently share Periods 1–{comparable}." if comparable > 1
               else "They currently share Period 1." if comparable == 1
               else "Start both simulations first.")
        )
        return result

    current = investment_report(tuple(current_periods[:selected_period]), cumulative)
    baseline = investment_report(tuple(baseline_periods[:selected_period]), cumulative)
    metrics = []
    for key, label, unit, section, field, factor in (
        ("consumption", "Consumed X", "X", "economy", "consumed_x", 1),
        ("capital", "Closing capital", "capital units", "economy", "capital_close", 1),
        ("work", "Average work", "%", "economy", "average_work", 100),
        ("price", "X price", "M / X", None, "price", 1),
        ("real_wage", "Wage buys", "X / work unit", None, "real_wage", 1),
        ("profit", "Net firm profit", "M", "firm", "net_operating_profit", 1),
    ):
        new = (current[section] if section else current)[field] * factor
        old = (baseline[section] if section else baseline)[field] * factor
        metrics.append({
            "key": key, "label": label, "unit": unit,
            "baseline": old, "current": new, "change": new - old,
            "change_unit": "pp" if key == "work" else unit,
        })
    result.update(
        available=True, metrics=metrics,
        note=(
            "Consumption and profit cover this report range. Capital is the closing "
            "stock; work is the household average. Price and wage purchasing power "
            f"are from Period {selected_period}. Monetary flows keep each period’s "
            "original prices. Differences show current minus baseline."
        ),
    )
    return result
