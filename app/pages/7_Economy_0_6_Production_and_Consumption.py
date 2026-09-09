"""A persistent economy: produce, trade, consume, and carry money forward."""

from dataclasses import asdict
from math import fsum

import streamlit as st

from econ_agent_sim.chat_view import render_chat
from econ_agent_sim.economy_0_6 import (
    ProductionAgent,
    ProductionRun,
    advance_period,
    default_production_agents,
)
from econ_agent_sim.results_component import render_results
from econ_agent_sim.workspace_style import apply_workspace_style

MAX_PERIODS = 100
FIELDS = ("x", "money", "alpha", "production")


def capture():
    for i, agent in enumerate(st.session_state.prod_agents):
        for field in FIELDS:
            agent[field] = float(st.session_state.get(f"prod_{field}_{i}", agent[field]))


def resize():
    capture()
    agents, count = st.session_state.prod_agents, st.session_state.prod_count
    defaults = default_production_agents(count)
    st.session_state.prod_agents = [agents[i] if i < len(agents) else defaults[i]
                                    for i in range(count)]
    for i in range(count, 20):
        for field in FIELDS:
            st.session_state.pop(f"prod_{field}_{i}", None)


def reset():
    generation = st.session_state.prod_generation + 1
    for key in list(st.session_state):
        if key.startswith("prod_"):
            del st.session_state[key]
    st.session_state.prod_generation = generation
    st.session_state.prod_notice = "Reset to two agents. Start a new simulation when ready."


def select_period():
    # Keep the selection when Setup temporarily unmounts the selector widget.
    st.session_state.prod_period_focus = st.session_state.prod_selected


def start():
    capture()
    try:
        population = tuple(ProductionAgent(**agent) for agent in st.session_state.prod_agents)
        candidate = advance_period(population)
    except (ValueError, ArithmeticError, AssertionError) as error:
        st.session_state.prod_error = f"Could not start this setup: {error}"
        return
    st.session_state.prod_history = [candidate]
    st.session_state.prod_submitted = population
    st.session_state.prod_generation += 1
    st.session_state.prod_selected = 1
    st.session_state.prod_period_focus = 1
    st.session_state.prod_error = None
    st.session_state.prod_next_view = "Results"


def next_period():
    history = st.session_state.prod_history
    if not history or len(history) >= MAX_PERIODS:
        return
    try:
        candidate = advance_period(st.session_state.prod_submitted, previous=history[-1])
    except (ValueError, ArithmeticError, AssertionError) as error:
        st.session_state.prod_error = f"Could not advance this economy: {error}"
        return
    st.session_state.prod_history = [*history, candidate]
    st.session_state.prod_selected = len(history) + 1
    st.session_state.prod_period_focus = len(history) + 1
    st.session_state.prod_error = None


st.set_page_config(page_title="Tiny Economy — Production and Consumption", layout="centered",
                   initial_sidebar_state="collapsed")
for key, value in {"agents": default_production_agents(), "count": 2, "history": [],
                   "submitted": None, "generation": 0, "view": "Set up", "error": None}.items():
    st.session_state.setdefault(f"prod_{key}", value)
apply_workspace_style()
st.caption("TINY ECONOMY · PRODUCTION + CONSUMPTION")
st.page_link("streamlit_app.py", label="← Explore economies")
if target := st.session_state.pop("prod_next_view", None):
    st.session_state.prod_view = target
with st.container(key="economy04_mobile_nav"):
    view = st.pills("View", options=("Set up", "Results", "Ask why"), required=True,
                    key="prod_view", label_visibility="collapsed", width="stretch")
st.button("Reset", on_click=reset, width="stretch",
          help="Restore the starting setup and clear this simulation’s history.")
if notice := st.session_state.pop("prod_notice", None):
    st.success(notice)
if st.session_state.prod_error:
    st.error(st.session_state.prod_error)
history = st.session_state.prod_history
dirty = bool(history) and st.session_state.prod_agents != [asdict(a) for a in st.session_state.prod_submitted]

if view == "Set up":
    st.title("An economy, one period at a time.")
    st.write("Agents produce X, trade, and consume all their available X. Money carries into the next period.")
    st.caption("Starting point: two agents with 1 Money each, producing 1 X per period, with equal preferences. Initial X is a one-time stock; production repeats.")
    st.number_input("Number of agents", min_value=2, max_value=20, step=1,
                    key="prod_count", on_change=resize)
    for i, agent in enumerate(st.session_state.prod_agents):
        with st.container(key=f"agent_card_{i}"), st.expander(agent["name"], expanded=len(st.session_state.prod_agents) <= 4):
            for field, label in (("x", "initial X"), ("money", "initial Money"),
                                 ("production", "X produced per period"),
                                 ("alpha", "preference for consumption")):
                key = f"prod_{field}_{i}"
                st.session_state.setdefault(key, agent[field])
                st.number_input(f"{agent['name']} · {label}", min_value=.01 if field == "alpha" else 0.0,
                                max_value=.99 if field == "alpha" else 1_000_000.0,
                                step=.10, format="%.2f", key=key, on_change=capture)
            st.caption(f"Desired wealth shares: {agent['alpha']:.0%} in consumption · {1-agent['alpha']:.0%} in Money. Production is fixed, not a work decision.")
    with st.container(border=True):
        st.subheader("Starting totals")
        st.write(f"Agents · {len(st.session_state.prod_agents)}")
        for field, label in (("x", "Initial X"), ("money", "Initial Money"),
                             ("production", "X produced each period")):
            st.write(f"{label} · {fsum(a[field] for a in st.session_state.prod_agents):g}")
    if dirty:
        st.info("Setup changed · the existing timeline still uses its submitted setup. Start a new simulation to apply your edits.")
    if history:
        st.caption("Starting a new simulation replaces this timeline. Next period continues the existing one without applying draft edits.")
    st.button("Start new simulation", type="primary", on_click=start, width="stretch")
    st.caption("Produce → trade → consume → carry money forward. No goods storage, borrowing, banks or money creation. Agents value money directly and do not plan future purchases.")
elif not history:
    st.info("No periods yet. Set up your agents, then start a new simulation.")
else:
    if dirty:
        st.info("Setup changed · this timeline still uses its submitted setup. Next period does not apply draft edits.")
    st.session_state.setdefault("prod_selected", st.session_state.prod_period_focus)
    selected = st.selectbox("View period", options=list(range(1, len(history) + 1)),
                            format_func=lambda number: f"Period {number}", key="prod_selected",
                            on_change=select_period)
    st.button("Next period", type="primary", on_click=next_period, width="stretch",
              disabled=len(history) >= MAX_PERIODS,
              help="Continue from the latest period, even when viewing an earlier one.")
    if len(history) >= MAX_PERIODS:
        st.caption(f"Reached {MAX_PERIODS} periods. Start a new simulation to explore another setup.")
    elif selected != len(history):
        st.caption(f"Viewing history. Next period advances from Period {len(history)}, not this earlier period.")
    submitted = ProductionRun(history[selected - 1], history[selected - 2] if selected > 1 else None,
                              st.session_state.prod_generation)
    if view == "Results":
        st.subheader(f"Period {selected}")
        st.caption(f"Compared with Period {selected - 1}." if selected > 1 else "Your first period.")
        render_results(submitted.data)
        with st.expander("Timeline"):
            st.dataframe([{"Period": period.number, "X price": period.market.prices["X"],
                           "Produced X": fsum(period.produced.values()),
                           "Consumed X": fsum(period.consumed.values()),
                           "Money": fsum(s["Money"] for s in period.closing_stocks.values())}
                          for period in history], hide_index=True, width="stretch")
    else:
        render_chat(submitted)
