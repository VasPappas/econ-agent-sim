"""Independent one-good, valued-money experiments."""

from dataclasses import asdict

import streamlit as st

from econ_agent_sim.chat_view import render_chat
from econ_agent_sim.economy_0_5 import (
    MoneyAgent,
    MoneyRun,
    default_money_agents,
    run_money_economy,
)
from econ_agent_sim.results_component import render_results
from econ_agent_sim.workspace_style import apply_workspace_style


def capture():
    for i, a in enumerate(st.session_state.cash_agents):
        for field in ("x", "money", "alpha"):
            a[field] = float(st.session_state.get(f"cash_{field}_{i}", a[field]))


def resize():
    capture()
    agents = st.session_state.cash_agents
    count = st.session_state.cash_count
    st.session_state.cash_agents = [agents[i] if i < len(agents) else default_money_agents(count)[i]
                                    for i in range(count)]
    for i in range(count, 20):
        for field in ("x", "money", "alpha"):
            st.session_state.pop(f"cash_{field}_{i}", None)


def reset():
    generation = st.session_state.cash_generation + 1
    for key in list(st.session_state):
        if key.startswith("cash_"):
            del st.session_state[key]
    st.session_state.cash_generation = generation
    st.session_state.cash_notice = "Reset to two agents with 1 X and 1 Money each. Press Run."


@st.cache_data(show_spinner=False, max_entries=32)
def calculate(population):
    return run_money_economy(population)


def run():
    capture()
    try:
        candidate = calculate(tuple(MoneyAgent(**a) for a in st.session_state.cash_agents))
    except (ValueError, ArithmeticError, AssertionError) as error:
        st.session_state.cash_error = f"Could not run this setup: {error}"
        return
    st.session_state.cash_previous = st.session_state.cash_result
    st.session_state.cash_result = candidate
    st.session_state.cash_number += 1
    st.session_state.cash_generation += 1
    st.session_state.cash_error = None
    st.session_state.cash_next_view = "Results"


st.set_page_config(page_title="Tiny Economy — Good and Money", layout="centered", initial_sidebar_state="collapsed")
for key, value in {"agents": default_money_agents(), "count": 2, "result": None,
                   "previous": None, "number": 0, "generation": 0,
                   "view": "Set up", "error": None}.items():
    st.session_state.setdefault(f"cash_{key}", value)
apply_workspace_style()
st.caption("TINY ECONOMY · ONE GOOD + MONEY")
st.page_link("streamlit_app.py", label="← Explore economies")
if target := st.session_state.pop("cash_next_view", None):
    st.session_state.cash_view = target
with st.container(key="economy04_mobile_nav"):
    view = st.pills("View", options=("Set up", "Results", "Ask why"), required=True,
                    key="cash_view", label_visibility="collapsed", width="stretch")
st.button("Reset", on_click=reset, width="stretch", help="Restore the starting setup and clear results.")
if notice := st.session_state.pop("cash_notice", None):
    st.success(notice)
result = st.session_state.cash_result
dirty = result is not None and st.session_state.cash_agents != [asdict(a) for a in result.population]
if dirty and view != "Set up":
    st.info(f"Setup changed · Run {st.session_state.cash_number} still shows your last submitted setup. Press Run to calculate your edits.")
if st.session_state.cash_error:
    st.error(st.session_state.cash_error)
if view == "Set up":
    st.title("A good, or money to keep?")
    st.write("Choose what each agent starts with and how much they prefer the good versus holding money.")
    st.caption("Starting point: two agents, each with 1 X, 1 Money and equal preferences. Neither needs to trade at a price of 1.")
    st.number_input("Number of agents", min_value=2, max_value=20, step=1,
                    key="cash_count", on_change=resize)
    for i, a in enumerate(st.session_state.cash_agents):
        with st.container(key=f"agent_card_{i}"), st.expander(a["name"], expanded=len(st.session_state.cash_agents) <= 4):
            for field, label in (("x", "starting X"), ("money", "starting Money"), ("alpha", "preference for the good")):
                key = f"cash_{field}_{i}"
                st.session_state.setdefault(key, a[field])
                st.number_input(f"{a['name']} · {label}", min_value=.01 if field == "alpha" else 0.0,
                                max_value=.99 if field == "alpha" else 1_000_000.0,
                                step=.10, format="%.2f", key=key, on_change=capture)
            st.caption(f"Desired wealth shares: {a['alpha']:.0%} in X · {1-a['alpha']:.0%} in Money. This is not the share of starting cash spent.")
    with st.container(border=True):
        st.subheader("Starting totals")
        st.write(f"Agents · {len(st.session_state.cash_agents)}")
        for field, label in (("x", "X"), ("money", "Money")):
            st.write(f"{label} · {sum(a[field] for a in st.session_state.cash_agents):g}")
    if dirty:
        st.info(f"Setup changed · Run {st.session_state.cash_number} still shows your last submitted setup. Press Run to calculate your edits.")
    st.button("Run", type="primary", on_click=run, width="stretch")
    st.caption("Money is valued directly in this experiment. No borrowing, production or money creation. Each run starts from your setup, not the previous outcome.")
elif result is None:
    st.info("No run yet. Set up your agents, then press Run.")
else:
    submitted = MoneyRun(result, st.session_state.cash_previous,
                         st.session_state.cash_number, st.session_state.cash_generation)
    if view == "Results":
        st.subheader(submitted.data["label"])
        st.caption(f"Compared with Run {submitted.number - 1}." if submitted.previous else "Your first calculated result.")
        render_results(submitted.data)
    else:
        render_chat(submitted)
