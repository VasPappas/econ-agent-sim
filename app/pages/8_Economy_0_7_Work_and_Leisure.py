"""Choose work, produce, trade and consume in a persistent economy."""

from dataclasses import asdict
from math import fsum

import streamlit as st

from econ_agent_sim.chat_view import render_chat
from econ_agent_sim.economy_0_7 import (
    WorkAgent,
    WorkRun,
    advance_work_period,
    default_work_agents,
    work_report,
)
from econ_agent_sim.results_component import render_results
from econ_agent_sim.workspace_style import apply_workspace_style

MAX_PERIODS = 100
FIELDS = ("x", "money", "alpha", "productivity", "leisure")


def capture():
    for i, agent in enumerate(st.session_state.work_agents):
        for field in FIELDS:
            agent[field] = float(st.session_state.get(f"work_{field}_{i}", agent[field]))


def resize():
    capture()
    agents, count = st.session_state.work_agents, st.session_state.work_count
    defaults = default_work_agents(count)
    st.session_state.work_agents = [agents[i] if i < len(agents) else defaults[i]
                                    for i in range(count)]
    for i in range(count, 20):
        for field in FIELDS:
            st.session_state.pop(f"work_{field}_{i}", None)


def reset():
    generation = st.session_state.work_generation + 1
    for key in list(st.session_state):
        if key.startswith("work_"):
            del st.session_state[key]
    st.session_state.work_generation = generation
    st.session_state.work_notice = "Reset to two agents with equal priorities. Start a new simulation when ready."


def select_period():
    st.session_state.work_period_focus = st.session_state.work_selected


def start():
    capture()
    try:
        population = tuple(WorkAgent(**agent) for agent in st.session_state.work_agents)
        candidate = advance_work_period(population)
    except (ValueError, ArithmeticError, AssertionError) as error:
        st.session_state.work_error = f"Could not start this setup: {error}"
        return
    st.session_state.work_history = [candidate]
    st.session_state.work_submitted = population
    st.session_state.work_generation += 1
    st.session_state.work_selected = 1
    st.session_state.work_period_focus = 1
    st.session_state.work_error = None
    st.session_state.work_next_view = "Results"


def next_period():
    history = st.session_state.work_history
    if not history or len(history) >= MAX_PERIODS:
        return
    try:
        candidate = advance_work_period(st.session_state.work_submitted, previous=history[-1])
    except (ValueError, ArithmeticError, AssertionError) as error:
        st.session_state.work_error = f"Could not advance this economy: {error}"
        return
    st.session_state.work_history = [*history, candidate]
    st.session_state.work_selected = len(history) + 1
    st.session_state.work_period_focus = len(history) + 1
    st.session_state.work_error = None


st.set_page_config(page_title="Tiny Economy — Work and Leisure", layout="centered",
                   initial_sidebar_state="collapsed")
for key, value in {"agents": default_work_agents(), "count": 2, "history": [],
                   "submitted": None, "generation": 0, "view": "Set up", "error": None}.items():
    st.session_state.setdefault(f"work_{key}", value)
apply_workspace_style()
st.caption("TINY ECONOMY · WORK + LEISURE")
st.page_link("streamlit_app.py", label="← Explore economies")
if target := st.session_state.pop("work_next_view", None):
    st.session_state.work_view = target
with st.container(key="economy04_mobile_nav"):
    view_column, reset_column = st.columns([4, 1], gap="small", vertical_alignment="center")
    with view_column:
        view = st.pills("View", options=("Set up", "Results", "Ask why"), required=True,
                        key="work_view", label_visibility="collapsed", width="stretch")
    with reset_column:
        st.button("Reset", on_click=reset, width="stretch",
                  help="Restore equal priorities and clear this simulation’s history.")
if notice := st.session_state.pop("work_notice", None):
    st.success(notice)
if st.session_state.work_error:
    st.error(st.session_state.work_error)
history = st.session_state.work_history
dirty = bool(history) and st.session_state.work_agents != [asdict(a) for a in st.session_state.work_submitted]

if view == "Set up":
    st.title("How much is worth working for?")
    st.write("Agents choose how much to work, balancing consumption, money and leisure. They produce X, trade, and consume all their X; money carries forward.")
    st.caption("Starting point: two agents with 1 Money each and equal priorities. Each works half the available time, produces and consumes 1 X, and keeps 1 Money at price 1.")
    st.number_input("Number of agents", min_value=2, max_value=20, step=1,
                    key="work_count", on_change=resize)
    for i, agent in enumerate(st.session_state.work_agents):
        with st.container(key=f"agent_card_{i}"), st.expander(agent["name"], expanded=len(st.session_state.work_agents) <= 4):
            for field, label in (("x", "initial X"), ("money", "initial Money"),
                                 ("productivity", "X produced at full effort"),
                                 ("alpha", "consumption vs money"),
                                 ("leisure", "preference for leisure")):
                key = f"work_{field}_{i}"
                st.session_state.setdefault(key, agent[field])
                preference = field in ("alpha", "leisure")
                st.number_input(f"{agent['name']} · {label}",
                                min_value=.01 if preference else (.1 if field == "productivity" else 0.0),
                                max_value=.99 if preference else (100.0 if field == "productivity" else 1_000_000.0),
                                step=.10, format="%.4f" if field == "leisure" else "%.2f",
                                key=key, on_change=capture)
            alpha, leisure = agent["alpha"], agent["leisure"]
            st.caption("The starting leisure preference is exactly ⅓, displayed as 0.3333. Each +/− changes the preference by 0.10.")
            st.caption(f"Preference weights: {(1-leisure)*alpha:.1%} consumption · {(1-leisure)*(1-alpha):.1%} Money · {leisure:.1%} leisure.")
            st.caption("Consumption vs money divides the priority left after leisure. Leisure preference is a weight; actual leisure is chosen by the agent.")
    with st.container(border=True):
        st.subheader("Starting totals")
        st.write(f"Agents · {len(st.session_state.work_agents)}")
        for field, label in (("x", "Initial X"), ("money", "Initial Money"),
                             ("productivity", "X capacity at full effort")):
            st.write(f"{label} · {fsum(a[field] for a in st.session_state.work_agents):g}")
        st.caption("Actual production depends on chosen effort. Initial X is a one-time stock.")
    if dirty:
        st.info("Setup changed · the existing timeline still uses its submitted setup. Start a new simulation to apply your edits.")
    if history:
        st.caption("Starting a new simulation replaces this timeline. Next period continues the existing one without applying draft edits.")
    st.button("Start new simulation", type="primary", on_click=start, width="stretch")
    st.caption("Work and price are determined together. All X is consumed each period. No goods storage, borrowing or money creation. Agents value money’s purchasing power directly and do not plan future purchases.")
elif not history:
    st.info("No periods yet. Set up your agents, then start a new simulation.")
else:
    if dirty:
        st.info("Setup changed · this timeline still uses its submitted setup. Next period does not apply draft edits.")
    st.session_state.setdefault("work_selected", st.session_state.work_period_focus)
    selected = st.selectbox("View period", options=list(range(1, len(history) + 1)),
                            format_func=lambda number: f"Period {number}", key="work_selected",
                            on_change=select_period)
    report_scope = None
    if view == "Results":
        report_scope = st.pills("Report range", options=("This period", "Cumulative"),
                                default="This period", key="work_report_scope",
                                width="stretch")
        if report_scope == "Cumulative":
            st.caption(f"Cumulative from Period 1 through Period {selected}.")
    st.button("Next period", type="primary", on_click=next_period, width="stretch",
              disabled=len(history) >= MAX_PERIODS,
              help="Continue from the latest period, even when viewing an earlier one.")
    if len(history) >= MAX_PERIODS:
        st.caption(f"Reached {MAX_PERIODS} periods. Start a new simulation to explore another setup.")
    elif selected != len(history):
        st.caption(f"Viewing history. Next period advances from Period {len(history)}, not this earlier period.")
    submitted = WorkRun(history[selected - 1], history[selected - 2] if selected > 1 else None,
                        st.session_state.work_generation)
    if view == "Results":
        st.subheader(f"Period {selected}")
        st.caption(f"Compared with Period {selected - 1}." if selected > 1 else "Your first period.")
        result_data = dict(submitted.data)
        result_data["reporting"] = work_report(
            tuple(history[:selected]), cumulative=report_scope == "Cumulative"
        )
        render_results(result_data)
    else:
        render_chat(submitted)
