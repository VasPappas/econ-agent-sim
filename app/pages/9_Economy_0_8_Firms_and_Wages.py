"""Hire labor, produce and distribute profit in a persistent tiny economy."""

from math import fsum

import streamlit as st

from econ_agent_sim.chat_view import render_chat
from econ_agent_sim.economy_0_8 import (
    Economy08Run,
    Firm,
    Household,
    advance_firm_period,
    default_firm,
    default_households,
    firm_report,
)
from econ_agent_sim.results_0_8_component import render_firm_results
from econ_agent_sim.workspace_style import apply_workspace_style

MAX_PERIODS = 100
HOUSEHOLD_FIELDS = (
    "money", "consumption_priority", "money_priority", "leisure_priority",
)
FIRM_FIELDS = ("money", "productivity")


def fresh_households(count=2):
    return default_households(count)


def household_from_draft(draft):
    return Household(**draft)


def firm_from_draft(draft):
    return Firm(**draft)


def capture():
    for index, household in enumerate(st.session_state.fw_households):
        for field in HOUSEHOLD_FIELDS:
            key = f"fw_household_{field}_{index}"
            household[field] = float(st.session_state.get(key, household[field]))
    for field in FIRM_FIELDS:
        key = f"fw_firm_{field}"
        st.session_state.fw_firm[field] = float(
            st.session_state.get(key, st.session_state.fw_firm[field])
        )


def resize():
    capture()
    households = st.session_state.fw_households
    count = st.session_state.fw_count
    defaults = fresh_households(count)
    st.session_state.fw_households = [
        households[index] if index < len(households) else defaults[index]
        for index in range(count)
    ]
    for index in range(count, 20):
        for field in HOUSEHOLD_FIELDS:
            st.session_state.pop(f"fw_household_{field}_{index}", None)


def reset():
    generation = st.session_state.fw_generation + 1
    for key in list(st.session_state):
        if key.startswith("fw_"):
            del st.session_state[key]
    st.session_state.fw_generation = generation
    st.session_state.fw_notice = "Reset to two equal households and one firm."


def select_period():
    st.session_state.fw_period_focus = st.session_state.fw_selected


def submitted_settings():
    return (
        tuple(household_from_draft(item) for item in st.session_state.fw_households),
        firm_from_draft(st.session_state.fw_firm),
    )


def start():
    capture()
    try:
        households, firm = submitted_settings()
        candidate = advance_firm_period(households, firm)
    except (ValueError, ArithmeticError, AssertionError) as error:
        st.session_state.fw_error = f"Could not start this setup: {error}"
        return
    st.session_state.fw_history = [candidate]
    st.session_state.fw_submitted = (households, firm)
    st.session_state.fw_generation += 1
    st.session_state.fw_selected = 1
    st.session_state.fw_period_focus = 1
    st.session_state.fw_error = None
    st.session_state.fw_next_view = "Results"


def next_period():
    history = st.session_state.fw_history
    if not history or len(history) >= MAX_PERIODS:
        return
    households, firm = st.session_state.fw_submitted
    try:
        candidate = advance_firm_period(households, firm, previous=history[-1])
    except (ValueError, ArithmeticError, AssertionError) as error:
        st.session_state.fw_error = f"Could not advance this economy: {error}"
        return
    st.session_state.fw_history = [*history, candidate]
    st.session_state.fw_selected = len(history) + 1
    st.session_state.fw_period_focus = len(history) + 1
    st.session_state.fw_error = None


def compact_input(owner, field, label, *, minimum, maximum, step, index=None):
    suffix = f"_{index}" if index is not None else ""
    key = f"fw_{owner}_{field}{suffix}"
    row_key = f"fw_compact_{owner}_{field}{suffix}"
    with st.container(key=row_key):
        label_column, input_column = st.columns(
            [1, 1.18], gap="small", vertical_alignment="center"
        )
        label_column.markdown(f"**{label}**")
        with input_column:
            st.number_input(
                label, min_value=minimum, max_value=maximum, step=step,
                format="%.2f", key=key, on_change=capture,
                label_visibility="collapsed",
            )


st.set_page_config(
    page_title="Tiny Economy — Firms and Wages", layout="centered",
    initial_sidebar_state="collapsed",
)
for key, value in {
    "households": fresh_households(), "firm": default_firm(), "count": 2,
    "history": [], "submitted": None, "generation": 0, "view": "Set up",
    "error": None,
}.items():
    st.session_state.setdefault(f"fw_{key}", value)

apply_workspace_style()
st.markdown(
    """<style>
    .st-key-fw_mobile_nav [data-testid="stHorizontalBlock"],
    [class*="st-key-fw_compact_"] [data-testid="stHorizontalBlock"] {
        flex-direction: row !important; flex-wrap: nowrap !important; gap: .5rem;
    }
    .st-key-fw_mobile_nav [data-testid="stColumn"],
    [class*="st-key-fw_compact_"] [data-testid="stColumn"] { min-width: 0; }
    [class*="st-key-fw_compact_"] { margin-bottom: -.45rem; }
    [class*="st-key-fw_compact_"] [data-testid="stMarkdownContainer"] p {
        font-size: .86rem; margin: 0;
    }
    </style>""",
    unsafe_allow_html=True,
)
st.caption("TINY ECONOMY · FIRMS + WAGES")
st.page_link("streamlit_app.py", label="← Explore economies")
if target := st.session_state.pop("fw_next_view", None):
    st.session_state.fw_view = target
with st.container(key="fw_mobile_nav"):
    view_column, reset_column = st.columns(
        [4, 1], gap="small", vertical_alignment="center"
    )
    with view_column:
        view = st.pills(
            "View", options=("Set up", "Results", "Ask why"), required=True,
            key="fw_view", label_visibility="collapsed", width="stretch",
        )
    with reset_column:
        st.button(
            "Reset", on_click=reset, width="stretch",
            help="Restore the baseline and clear this simulation’s history.",
        )

if notice := st.session_state.pop("fw_notice", None):
    st.success(notice)
if st.session_state.fw_error:
    st.error(st.session_state.fw_error)

history = st.session_state.fw_history
try:
    draft_settings = submitted_settings()
except ValueError:
    draft_settings = None
dirty = bool(history) and draft_settings != st.session_state.fw_submitted

if view == "Set up":
    st.title("Who works—and who earns what?")
    st.write(
        "Households choose work, consumption, money and leisure. One firm hires "
        "their labor, produces X and pays its owners last period’s profit."
    )
    st.caption(
        "Starting point: two equal households, 1 Money each, and equal priorities. "
        "The firm starts with 1 Money and productivity 2."
    )
    st.number_input(
        "Number of households", min_value=2, max_value=20, step=1,
        key="fw_count", on_change=resize,
    )
    for index, household in enumerate(st.session_state.fw_households):
        for field in HOUSEHOLD_FIELDS:
            st.session_state.setdefault(
                f"fw_household_{field}_{index}", household[field]
            )
        with st.container(key=f"fw_household_card_{index}"), st.expander(
            household["name"], expanded=index == 0
        ):
            compact_input(
                "household", "money", "Initial money", minimum=0.0,
                maximum=1_000_000.0, step=.10, index=index,
            )
            st.caption("WHAT MATTERS MOST? · RELATIVE SCORES")
            compact_input(
                "household", "consumption_priority", "Consume X", minimum=.01,
                maximum=100.0, step=.10, index=index,
            )
            compact_input(
                "household", "money_priority", "Keep money", minimum=.01,
                maximum=100.0, step=.10, index=index,
            )
            compact_input(
                "household", "leisure_priority", "Enjoy leisure", minimum=.01,
                maximum=100.0, step=.10, index=index,
            )
            total = fsum(household[field] for field in HOUSEHOLD_FIELDS[1:])
            st.caption(
                "Priorities · "
                f"{household['consumption_priority'] / total:.0%} consume · "
                f"{household['money_priority'] / total:.0%} money · "
                f"{household['leisure_priority'] / total:.0%} leisure."
            )

    for field in FIRM_FIELDS:
        st.session_state.setdefault(f"fw_firm_{field}", st.session_state.fw_firm[field])
    with st.container(key="fw_firm_card"), st.expander("Firm", expanded=True):
        compact_input(
            "firm", "money", "Operating money", minimum=.01,
            maximum=1_000_000.0, step=.10,
        )
        compact_input(
            "firm", "productivity", "Productivity", minimum=.10,
            maximum=100.0, step=.10,
        )
        st.caption(
            "Productivity is X produced with one full unit of total labor. "
            "Production has decreasing returns."
        )

    household_money = fsum(item["money"] for item in st.session_state.fw_households)
    firm_money = st.session_state.fw_firm["money"]
    st.markdown(
        f"**Economy starts with** · {len(st.session_state.fw_households)} households · "
        f"{household_money:g} household Money · {firm_money:g} firm Money · "
        f"{household_money + firm_money:g} total Money"
    )
    st.caption(
        f"Each household owns {1 / len(st.session_state.fw_households):.0%} of the firm. "
        "Ownership is equal and fixed."
    )
    if dirty:
        st.info(
            "Setup changed · the existing simulation still uses its submitted setup. "
            "Start a new simulation to apply your edits."
        )
    if history:
        st.caption(
            "Starting a new simulation replaces its history. Next period continues "
            "the existing one without applying draft edits."
        )
    st.button("Start new simulation", type="primary", on_click=start, width="stretch")
    st.caption(
        "The firm cannot borrow. Households consume all X. Money carries forward; "
        "current profit is distributed at the start of the next period."
    )
elif not history:
    st.info("No periods yet. Set up the households and firm, then start a new simulation.")
else:
    if dirty:
        st.info(
            "Setup changed · this simulation still uses its submitted setup. "
            "Next period does not apply draft edits."
        )
    st.session_state.setdefault("fw_selected", st.session_state.fw_period_focus)
    selected = st.selectbox(
        "View period", options=list(range(1, len(history) + 1)),
        format_func=lambda number: f"Period {number}", key="fw_selected",
        on_change=select_period,
    )
    report_scope = None
    if view == "Results":
        report_scope = st.pills(
            "Report range", options=("This period", "Cumulative"),
            default="This period", key="fw_report_scope", width="stretch",
        )
        if report_scope == "Cumulative":
            st.caption(f"Cumulative from Period 1 through Period {selected}.")
    st.button(
        "Next period", type="primary", on_click=next_period, width="stretch",
        disabled=len(history) >= MAX_PERIODS,
        help="Continue from the latest period, even when viewing an earlier one.",
    )
    if len(history) >= MAX_PERIODS:
        st.caption(f"Reached {MAX_PERIODS} periods. Start a new simulation to explore another setup.")
    elif selected != len(history):
        st.caption(
            f"Viewing history. Next period advances from Period {len(history)}, "
            "not this earlier period."
        )
    submitted = Economy08Run(
        history[selected - 1], history[selected - 2] if selected > 1 else None,
        st.session_state.fw_generation,
    )
    if view == "Results":
        st.subheader(f"Period {selected}")
        st.caption(
            f"Compared with Period {selected - 1}." if selected > 1
            else "Your first period."
        )
        result_data = dict(submitted.data)
        result_data["reporting"] = firm_report(
            tuple(history[:selected]), cumulative=report_scope == "Cumulative"
        )
        result_data["diagnostics"] = history[selected - 1].solution
        render_firm_results(result_data)
    else:
        render_chat(submitted)
