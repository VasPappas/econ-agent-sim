"""Presentation adapter for Economy 0.4; no Streamlit or browser dependencies."""

from dataclasses import asdict

from econ_agent_sim.economy_0_4 import ASSETS, MONEY, Economy04Result
from econ_agent_sim.explanations import built_in_explanations


def playground_data(
    result: Economy04Result,
    selected_index: int,
    revision: int,
) -> dict:
    """Serialize actual model results, separating experiment setup from settlement."""
    period = result.periods[selected_index]
    previous = result.periods[selected_index - 1] if selected_index else None
    opening = period.opening_stocks
    closing = period.closing_stocks
    accounting_ok = all(
        abs(opening[name][asset] + period.flows[name][asset] - closing[name][asset])
        < 1e-10
        for name in opening
        for asset in ASSETS
    )
    money_ok = (
        abs(
            sum(stocks[MONEY] for stocks in opening.values())
            - sum(stocks[MONEY] for stocks in closing.values())
        )
        < 1e-10
    )
    return {
        "revision": revision,
        "selected_index": selected_index,
        "label": "Baseline" if not selected_index else f"Experiment {selected_index}",
        "price": period.prices["X"],
        "previous_price": previous.prices["X"] if previous else None,
        "explanations": built_in_explanations(result, selected_index),
        "changes": [
            {"name": agent.name, "before": old.y, "after": agent.y}
            for agent in period.population
            for old in (previous.population if previous else ())
            if agent.name == old.name and abs(agent.y - old.y) > 1e-10
        ],
        "agent_count": len(period.population),
        "opening": opening,
        "closing": closing,
        "trades": [asdict(trade) for trade in period.trades],
        "checks": {
            "market": period.steps[-1].market_error <= result.config.tolerance,
            "money": money_ok,
            "accounts": accounting_ok,
        },
    }
