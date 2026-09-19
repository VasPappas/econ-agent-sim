"""Compare solved current-model experiments at a common visible date."""

from dataclasses import asdict

from econ_agent_sim.domain import MODEL_ID
from econ_agent_sim.reporting import build_report

_SETTING_LABELS = {
    "beta": "Patience", "depreciation": "Capital wear", "leisure_weight": "Leisure weight",
    "money_weight": "Money weight", "initial_capital": "Starting capital per firm",
    "initial_firm_cash_share": "Firms’ initial share of money",
}


def compare_runs(
    current, baseline, *, selected_period: int, cumulative: bool = False,
    current_name: str = "Current", baseline_name: str = "Baseline",
) -> dict:
    """Compare matching dates without solving or extending either experiment.

    The UI must restrict the selected date to both experiments' *visible* dates.
    This function never reads a later date to fill an earlier comparison.
    """
    new = build_report(current, selected_period, cumulative)
    old = build_report(baseline, selected_period, cumulative)
    metrics = []
    for key, label, unit, section, factor in (
        ("consumed_x", "Consumption", "X", "economy", 1),
        ("investment_quantity", "Investment", "X", "economy", 1),
        ("capital_close", "Closing capital", "capital units", "economy", 1),
        ("average_work", "Average work", "%", "economy", 100),
        ("net_operating_profit", "Operating profit", "Money", "economy", 1),
        ("dividends_paid", "Dividends", "Money", "economy", 1),
        ("price", "Goods price", "Money / X", None, 1),
        ("real_wage", "Wage purchasing power", "X / work unit", None, 1),
    ):
        left = (new[section] if section else new)[key] * factor
        right = (old[section] if section else old)[key] * factor
        metrics.append({
            "key": key, "label": label, "unit": unit,
            "current": left, "baseline": right, "change": left - right,
            "change_unit": "percentage points" if key == "average_work" else unit,
        })
    new_settings, old_settings = asdict(current.settings), asdict(baseline.settings)
    return {
        "model": MODEL_ID, "available": True, "through_period": selected_period,
        "scope": new["scope"], "label": new["label"],
        "current_name": current_name, "baseline_name": baseline_name,
        "metrics": metrics,
        "settings_changes": [
            {"key": key, "label": _SETTING_LABELS[key], "baseline": old_settings[key],
             "current": value}
            for key, value in new_settings.items() if value != old_settings[key]
        ],
        "note": (
            "Differences are current minus baseline at the same date. Flows keep "
            "their original prices, capital is the closing stock, and work is a "
            "household average. Price and wage purchasing power are selected-period "
            "rates. Changed preferences mean consumption alone is not a common "
            "welfare measure."
        ),
    }
