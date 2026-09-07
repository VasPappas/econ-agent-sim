"""Set up an economy, run it explicitly, then inspect immutable results."""
from dataclasses import asdict

import streamlit as st

from econ_agent_sim.chat_view import render_chat
from econ_agent_sim.economy_0_4 import ASSETS
from econ_agent_sim.evidence_view import render_evidence
from econ_agent_sim.experiment_chat import validate_chat_target
from econ_agent_sim.playground import playground_data
from econ_agent_sim.playground_component import cached_economy, render_playground
from econ_agent_sim.run_workspace import (
    default_agents,
    run_changes,
    run_explanations,
    setup_config,
)
from econ_agent_sim.workspace_style import apply_workspace_style


def capture_draft():
    for i, agent in enumerate(st.session_state.lab_agents):
        for key in ("x", "y", "alpha"):
            value = st.session_state.get(f"lab_{key}_{i}", agent[key])
            agent[key] = float(value)
    st.session_state.lab_money = float(st.session_state.get("lab_money_input", st.session_state.lab_money))


def resize_agents():
    capture_draft()
    count = int(st.session_state.lab_count)
    agents = st.session_state.lab_agents
    st.session_state.lab_agents = [
        agents[i] if i < len(agents) else default_agents(count)[i] for i in range(count)
    ]
    for i in range(count, 20):
        for key in ("x", "y", "alpha"):
            st.session_state.pop(f"lab_{key}_{i}", None)


def reset():
    generation = st.session_state.lab_generation + 1
    for key in list(st.session_state):
        if key.startswith("lab_"):
            st.session_state.pop(key, None)
    st.session_state.lab_generation = generation
    st.session_state.economy04_conversations = {}
    st.session_state.economy04_saved_focus = {}
    st.session_state.pop("economy04_selected_trade", None)
    st.session_state.lab_notice = "Reset to two identical agents. Press Run to calculate the starting economy."


def run():
    capture_draft()
    try:
        config = setup_config(st.session_state.lab_agents, st.session_state.lab_money)
        candidate = cached_economy(config)
    except (ValueError, TypeError, RuntimeError, AssertionError, OverflowError) as error:
        st.session_state.lab_error = f"Could not run this setup: {error}"
        return
    st.session_state.lab_previous = st.session_state.lab_result
    st.session_state.lab_result = candidate
    st.session_state.lab_number += 1
    st.session_state.lab_generation += 1
    st.session_state.lab_error = None
    st.session_state.lab_next_view = "Results"
    st.session_state.pop("economy04_selected_trade", None)


st.set_page_config(page_title="Tiny Economy — Set up and run", layout="centered", initial_sidebar_state="collapsed")
for key, value in {
    "agents": default_agents(), "count": len(st.session_state.get("lab_agents", default_agents())), "money": 10.0, "result": None,
    "previous": None, "number": 0, "generation": 0, "view": "Set up", "error": None,
}.items():
    st.session_state.setdefault(f"lab_{key}", value)
apply_workspace_style()
st.caption("TINY ECONOMY · MONEY")
st.page_link("streamlit_app.py", label="← Explore economies")
if target := st.session_state.pop("lab_next_view", None):
    st.session_state.lab_view = target
with st.container(key="economy04_mobile_nav"):
    view = st.pills("View", options=("Set up", "Results", "Ask why"), required=True,
                    default="Set up", key="lab_view", label_visibility="collapsed", width="stretch")
st.button("Reset", on_click=reset, width="stretch",
          help="Restore two agents with 1 X, 1 Y, equal preferences, and 10 Money each. Clear the current and previous results.")
if notice := st.session_state.pop("lab_notice", None):
    st.success(notice)

result = st.session_state.lab_result
previous = st.session_state.lab_previous
number = st.session_state.lab_number
revision = st.session_state.lab_generation
dirty = result is not None and (
    st.session_state.lab_agents != [asdict(a) for a in result.periods[0].population]
    or st.session_state.lab_money != result.config.opening_money_per_agent
)
if dirty:
    st.info(f"Setup changed · Run {number} still shows the last submitted setup. Press Run to calculate your edits.")
if st.session_state.lab_error:
    st.error(st.session_state.lab_error)

if view == "Set up":
    st.title("Set up your economy.")
    st.write("Choose what each agent has and what they prefer. Then press Run.")
    if result is None:
        st.caption("Starting point: two agents, each with 1 X, 1 Y, and equal preferences. At equal prices, neither needs to trade.")
    st.number_input("Number of agents", min_value=2, max_value=20, step=1,
                    key="lab_count", on_change=resize_agents)
    for i, agent in enumerate(st.session_state.lab_agents):
        with st.expander(agent["name"], expanded=len(st.session_state.lab_agents) <= 4):
            for good in ("x", "y"):
                key = f"lab_{good}_{i}"
                st.session_state.setdefault(key, agent[good])
                st.number_input(f"{agent['name']} · starting {good.upper()}",
                                min_value=0.0, step=.1, format="%.3f", key=key, on_change=capture_draft)
            key = f"lab_alpha_{i}"
            st.session_state.setdefault(key, agent["alpha"])
            st.slider(f"{agent['name']} · preference for X", min_value=.01, max_value=.99,
                      step=.01, key=key, on_change=capture_draft)
            st.caption(f"Spending shares: {agent['alpha']:.0%} X · {1-agent['alpha']:.0%} Y. 50/50 means equal preferences.")
    agents = st.session_state.lab_agents
    st.write(f"Starting totals: {sum(a['x'] for a in agents):g} X · {sum(a['y'] for a in agents):g} Y")
    with st.expander("Money and model details"):
        st.session_state.setdefault("lab_money_input", st.session_state.lab_money)
        st.number_input("Opening money per agent", min_value=.1, step=1.0,
                        key="lab_money_input", on_change=capture_draft)
        st.caption("Money settles trades but does not limit purchases. Y is the reference good, priced at 1. Preferences use positive spending shares for both goods (1–99%).")
    st.button("Run", type="primary", on_click=run, width="stretch")
    st.caption("Editing changes only the draft. Each Run starts from these quantities with fresh money. Results never carry balances into your next setup.")

elif result is None:
    st.info("No run yet. Set up your agents, then press Run.")
    if st.button("Go to setup", width="stretch"):
        st.session_state.lab_next_view = "Set up"
        st.rerun()

elif view == "Results":
    st.subheader(f"Run {number}")
    st.caption(f"Compared with Run {number - 1}." if previous else "Your first calculated result.")
    with st.expander("What changed in the setup?", expanded=bool(previous)):
        for change in run_changes(result, previous):
            st.write(change)
    data = playground_data(result, 0, revision)
    data.update(view="Results", label=f"Run {number}",
                previous_price=previous.periods[0].prices["X"] if previous else None,
                setup_summary=f"Run {number} · submitted setup",
                explanations=run_explanations(result, previous))
    saved = st.session_state.get("economy04_selected_trade")
    if validate_chat_target(saved, revision, 0, len(result.trades)):
        data["selected_trade"] = saved.get("trade_index")
    component = render_playground(data)
    selection = getattr(component, "selection", None)
    if (validate_chat_target(selection, revision, 0, len(result.trades))
            and selection["id"] != st.session_state.get("lab_last_selection")):
        st.session_state.economy04_selected_trade = selection
        st.session_state.lab_last_selection = selection["id"]
    question = getattr(component, "question", None)
    if (validate_chat_target(question, revision, 0, len(result.trades))
            and question["id"] != st.session_state.get("lab_last_question")):
        st.session_state.lab_last_question = question["id"]
        st.session_state.economy04_chat_trade = question.get("trade_index")
        st.session_state.economy04_chat_trade_identity = (revision, 0)
        if question.get("trade_index") is not None:
            st.session_state.economy04_selected_trade = question
        st.session_state.lab_next_view = "Ask why"
        st.rerun()
    navigation = getattr(component, "navigation", None)
    if (validate_chat_target(navigation, revision, 0, len(result.trades))
            and navigation.get("view") == "Experiment"
            and navigation["id"] != st.session_state.get("lab_last_navigation")):
        st.session_state.lab_last_navigation = navigation["id"]
        st.session_state.lab_next_view = "Set up"
        st.rerun()
    period = result.periods[0]
    with st.expander("Inspect the evidence"):
        rows = [
            {"agent": name, "asset": asset, "opening": opening[asset],
             "net flow": period.flows[name][asset], "closing": period.closing_stocks[name][asset],
             "check": opening[asset] + period.flows[name][asset] - period.closing_stocks[name][asset]}
            for name, opening in period.opening_stocks.items() for asset in ASSETS
        ]
        render_evidence(result, 0, rows)

else:
    render_chat(result, 0, revision, previous_result=previous, run_number=number)
    if st.button("← Back to results", width="stretch"):
        st.session_state.lab_next_view = "Results"
        st.rerun()
