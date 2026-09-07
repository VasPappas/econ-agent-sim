"""Independent runs: editable setups never mutate a calculated result."""

from dataclasses import asdict
from math import isfinite

from econ_agent_sim.economy_0_2 import ExchangeAgentConfig
from econ_agent_sim.economy_0_4 import Economy04Config
from econ_agent_sim.experiment_chat import experiment_context
from econ_agent_sim.explanations import built_in_explanations


def default_agents(count=2):
    return [{"name": f"Agent {i + 1}", "x": 1.0, "y": 1.0, "alpha": .5} for i in range(count)]


def setup_config(agents, money=10.0):
    if not 2 <= len(agents) <= 20:
        raise ValueError("Choose between 2 and 20 agents.")
    if not isfinite(money) or money <= 0:
        raise ValueError("Opening money must be positive and finite.")
    for a in agents:
        if any(not isfinite(a[k]) for k in ("x", "y", "alpha")):
            raise ValueError("Use finite quantities and preferences.")
    if any(sum(a[k] for a in agents) <= 0 for k in ("x", "y")):
        raise ValueError("The economy needs a positive total of both X and Y.")
    return Economy04Config(
        period_populations=(tuple(ExchangeAgentConfig(**a) for a in agents),),
        opening_money_per_agent=money, initial_price_x=1.0, tolerance=1e-10,
    )


def run_changes(result, previous):
    if previous is None:
        return ["First run · no previous result to compare."]
    before = {a.name: a for a in previous.periods[0].population}
    after = {a.name: a for a in result.periods[0].population}
    changes = []
    for name, a in after.items():
        if name not in before:
            changes.append(f"{name} added · {a.x:g} X · {a.y:g} Y · {a.alpha:.0%} to X")
            continue
        b = before[name]
        for key, label in (("x", "X"), ("y", "Y"), ("alpha", "spending share on X")):
            old, new = getattr(b, key), getattr(a, key)
            if old != new:
                values = f"{old:.0%} → {new:.0%}" if key == "alpha" else f"{old:g} → {new:g}"
                changes.append(f"{name} · {label}: {values}")
    changes.extend(f"{name} removed" for name in before if name not in after)
    old, new = previous.config.opening_money_per_agent, result.config.opening_money_per_agent
    if old != new:
        changes.append(f"Opening money per agent: {old:g} → {new:g}")
    return changes or ["Same setup as the previous run."]


def run_context(result, previous, number, trade_index=None):
    context = experiment_context(result, 0, trade_index)
    context["experiment"] = f"Run {number}"
    context["setup_changes"] = run_changes(result, previous)
    context["previous_run"] = (
        {"prices": previous.periods[0].prices,
         "agents": [asdict(a) for a in previous.periods[0].population],
         "opening_money_per_agent": previous.config.opening_money_per_agent}
        if previous else None
    )
    context["previous_prices"] = previous.periods[0].prices if previous else None
    context["price_x_change_percent"] = (
        100 * (result.periods[0].prices["X"] / previous.periods[0].prices["X"] - 1)
        if previous else None
    )
    context["run_rule"] = "Independent submitted setups. Quantities, preferences, and agent count can all change. No balances carry forward. Ledger trade IDs restart within each run."
    return context


def run_explanations(result, previous, trade_index=None):
    answers = built_in_explanations(result, 0, trade_index)
    p = result.periods[0]
    text = f"X clears at {p.prices['X']:.4f} Money per unit. Y is the reference good, with its price fixed at 1. "
    if previous:
        text += f"The previous run's X price was {previous.periods[0].prices['X']:.4f}. "
    text += (
        "The clearing price depends on starting goods and spending preferences across all agents. "
        "Changing quantities, preferences, or population can change demand and supply. "
        "When several inputs change, the comparison alone does not isolate one cause."
    )
    answers["Why did X change but not Y?"] = text
    if not p.trades:
        answers = {"Why is there no trade?": (
            "At the clearing prices, each agent already holds their desired bundle, "
            "within the model's numerical tolerance. No exchange is needed. "
            "Two agents with 1 X, 1 Y and equal spending preferences are such a case at equal prices."
        ), **answers}
    return answers
