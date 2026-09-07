"""Presentation adapter for Economy 0.4; no Streamlit or browser dependencies."""

from dataclasses import asdict
from math import isfinite

from econ_agent_sim.economy_0_3 import redistribute_y
from econ_agent_sim.economy_0_4 import ASSETS, MONEY, Economy04Result
from econ_agent_sim.explanations import built_in_explanations


def apply_transfer(population, action: dict, revision: int):
    """Validate an untrusted component command before calling the existing engine."""
    if not isinstance(action, dict) or action.get("kind") != "redistribute":
        raise ValueError("Unknown playground action.")
    action_id = action.get("id")
    if not isinstance(action_id, str) or not 1 <= len(action_id) <= 100:
        raise ValueError("The action needs a valid identifier.")
    if type(action.get("revision")) is not int or action["revision"] != revision:
        raise ValueError("The experiment changed. Please try your transfer again.")
    amount = action.get("amount")
    if isinstance(amount, bool) or not isinstance(amount, (int, float)):
        raise TypeError("Enter a numeric amount of Y.")
    if not isfinite(amount) or amount < 0.01:
        raise ValueError("Move at least 0.01 Y, using a finite amount.")
    sender, receiver = action.get("sender"), action.get("receiver")
    if not isinstance(sender, str) or not isinstance(receiver, str):
        raise TypeError("Choose two agents.")
    return redistribute_y(
        population, sender_name=sender, receiver_name=receiver, amount=float(amount)
    )


def playground_data(
    result: Economy04Result,
    selected_index: int,
    revision: int,
    last_transfer: dict | None = None,
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
        "latest_index": len(result.periods) - 1,
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
        "agents": [asdict(agent) for agent in result.config.period_populations[-1]],
        "opening_money": result.config.opening_money_per_agent,
        "opening": opening,
        "closing": closing,
        "trades": [asdict(trade) for trade in period.trades],
        "checks": {
            "market": period.steps[-1].market_error <= result.config.tolerance,
            "money": money_ok,
            "accounts": accounting_ok,
        },
        "last_transfer": (
            last_transfer if selected_index == len(result.periods) - 1 else None
        ),
    }
