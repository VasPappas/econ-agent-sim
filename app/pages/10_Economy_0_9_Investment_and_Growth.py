"""A compact workspace for capital, current consumption and linked periods."""

from math import fsum

import streamlit as st

from econ_agent_sim.economy_0_9 import (
    Firm,
    Household,
    advance_investment_period,
    default_firm,
    default_households,
    investment_report,
)
from econ_agent_sim.investment_chat_view import render_investment_chat
from econ_agent_sim.results_0_9_component import render_investment_results
from econ_agent_sim.workspace_style import apply_workspace_style

MAX_PERIODS = 100
HOUSEHOLD_FIELDS = (
    "money", "consumption_priority", "money_priority", "leisure_priority",
)
FIRM_FIELDS = (
    "money", "capital", "productivity", "reinvestment_rate", "depreciation_rate",
)
PERCENT_FIELDS = ("reinvestment_rate", "depreciation_rate")


def capture():
    """Keep the editable draft independently of transient widget state."""
    for index, household in enumerate(st.session_state.ig_households):
        for field in HOUSEHOLD_FIELDS:
            key = f"ig_household_{field}_{index}"
            household[field] = float(st.session_state.get(key, household[field]))
    for field in FIRM_FIELDS:
        key = f"ig_firm_{field}"
        if key in st.session_state:
            value = float(st.session_state[key])
            st.session_state.ig_firm[field] = (
                value / 100 if field in PERCENT_FIELDS else value
            )


def remember_expander(name):
    st.session_state.ig_expanded[name] = st.session_state[f"ig_open_{name}"]


def setup_expander(label, name, *, expanded=False):
    key = f"ig_open_{name}"
    st.session_state.setdefault(
        key, st.session_state.ig_expanded.get(name, expanded)
    )
    # The initial expanded argument stays constant, so the widget identity does
    # not change when a user opens a card or edits one of its children.
    return st.expander(
        label, expanded=expanded, key=key,
        on_change=remember_expander, args=(name,),
    )


def resize():
    capture()
    households = st.session_state.ig_households
    count = st.session_state.ig_count
    defaults = default_households(count)
    st.session_state.ig_households = [
        households[index] if index < len(households) else defaults[index]
        for index in range(count)
    ]
    for index in range(count, 20):
        for field in HOUSEHOLD_FIELDS:
            st.session_state.pop(f"ig_household_{field}_{index}", None)
        name = f"household_{index}"
        st.session_state.pop(f"ig_open_{name}", None)
        st.session_state.ig_expanded.pop(name, None)


def reset():
    generation = st.session_state.ig_generation + 1
    for key in list(st.session_state):
        if key.startswith("ig_"):
            del st.session_state[key]
    st.session_state.ig_generation = generation
    st.session_state.ig_notice = "Baseline restored. Ready for a fresh experiment."


def select_period():
    st.session_state.ig_period_focus = st.session_state.ig_selected


def submitted_settings():
    return (
        tuple(Household(**item) for item in st.session_state.ig_households),
        Firm(**st.session_state.ig_firm),
    )


def start():
    capture()
    try:
        households, firm = submitted_settings()
        candidate = advance_investment_period(households, firm)
    except (ValueError, ArithmeticError, AssertionError) as error:
        st.session_state.ig_error = f"Could not start this setup: {error}"
        return
    st.session_state.ig_history = [candidate]
    st.session_state.ig_submitted = (households, firm)
    st.session_state.ig_generation += 1
    st.session_state.ig_selected = 1
    st.session_state.ig_period_focus = 1
    st.session_state.ig_error = None
    st.session_state.ig_next_view = "Results"


def next_period(count=1):
    history = st.session_state.ig_history
    if not history or len(history) >= MAX_PERIODS:
        return
    households, firm = st.session_state.ig_submitted
    pending = []
    previous = history[-1]
    try:
        for _ in range(min(count, MAX_PERIODS - len(history))):
            previous = advance_investment_period(households, firm, previous=previous)
            pending.append(previous)
    except (ValueError, ArithmeticError, AssertionError) as error:
        st.session_state.ig_error = f"Could not advance this economy: {error}"
        return
    st.session_state.ig_history = [*history, *pending]
    st.session_state.ig_selected = len(history) + len(pending)
    st.session_state.ig_period_focus = len(history) + len(pending)
    st.session_state.ig_error = None


def compact_input(owner, field, label, *, minimum, maximum, step, index=None):
    suffix = f"_{index}" if index is not None else ""
    with st.container(key=f"ig_compact_{owner}_{field}{suffix}"):
        label_column, input_column = st.columns(
            [1, 1.45], gap="small", vertical_alignment="center"
        )
        label_column.markdown(f"**{label}**")
        with input_column:
            st.number_input(
                label, min_value=minimum, max_value=maximum, step=step,
                format="%.0f" if field in PERCENT_FIELDS else "%.2f",
                key=f"ig_{owner}_{field}{suffix}", on_change=capture,
                label_visibility="collapsed",
            )


st.set_page_config(
    page_title="Tiny Economy — Investment and Growth", layout="centered",
    initial_sidebar_state="collapsed",
)
for key, value in {
    "households": default_households(), "firm": default_firm(), "count": 2,
    "history": [], "submitted": None, "generation": 0, "view": "Set up",
    "error": None, "expanded": {}, "period_focus": 1,
}.items():
    st.session_state.setdefault(f"ig_{key}", value)

apply_workspace_style()
st.markdown(
    """<style>
    .st-key-ig_mobile_nav [data-testid="stHorizontalBlock"],
    .st-key-ig_period_controls [data-testid="stHorizontalBlock"],
    [class*="st-key-ig_compact_"] [data-testid="stHorizontalBlock"] {
        flex-direction: row !important; flex-wrap: nowrap !important; gap: .5rem;
    }
    .st-key-ig_mobile_nav [data-testid="stColumn"],
    .st-key-ig_period_controls [data-testid="stColumn"],
    [class*="st-key-ig_compact_"] [data-testid="stColumn"] { min-width: 0; }
    .st-key-ig_mobile_nav [data-testid="stButtonGroup"] { width: 100%; }
    .st-key-ig_mobile_nav button {
        min-height: 44px; padding: .4rem .45rem; border-radius: 12px;
        flex: 1; white-space: nowrap;
    }
    .st-key-ig_mobile_nav button p { font-size: .8rem; }
    .st-key-ig_mobile_nav button[aria-checked="true"],
    .st-key-ig_report_scope button[aria-checked="true"] {
        background: #174e44 !important; color: white !important;
        border-color: #174e44 !important;
    }
    .st-key-ig_report_scope button { min-height: 44px; }
    [class*="st-key-ig_compact_"] { margin-bottom: -.5rem; }
    [class*="st-key-ig_compact_"] [data-testid="stMarkdownContainer"] p {
        font-size: .85rem; line-height: 1.25; margin: 0;
    }
    [class*="st-key-ig_compact_"] [data-testid="stNumberInput"] button {
        min-width: 44px; min-height: 44px; width: 44px;
    }
    [class*="st-key-ig_compact_"] [data-testid="stNumberInput"] input {
        min-width: 0; padding-left: .5rem; padding-right: .2rem;
    }
    [class*="st-key-ig_open_"] summary { min-height: 48px; }
    .st-key-ig_open_firm details { background: #fffdf5; border-color: #e6d8ad; }
    .st-key-ig_starting_totals {
        border: 1px solid #dce4d7; background: #edf3ea;
        border-radius: 14px; padding: .8rem 1rem;
    }
    .st-key-ig_starting_totals p { margin: 0; }
    @media(max-width: 360px) {
        .st-key-ig_mobile_nav [data-testid="stHorizontalBlock"] { gap: .3rem; }
        .st-key-ig_mobile_nav button { padding-inline: .3rem; }
        .st-key-ig_mobile_nav button p { font-size: .75rem; }
    }
    </style>""", unsafe_allow_html=True,
)
st.caption("TINY ECONOMY · 0.9 · INVESTMENT + GROWTH")
st.page_link("streamlit_app.py", label="← Explore economies")
if target := st.session_state.pop("ig_next_view", None):
    st.session_state.ig_view = target
with st.container(key="ig_mobile_nav"):
    view_column, reset_column = st.columns(
        [4.2, 1], gap="small", vertical_alignment="center"
    )
    with view_column:
        view = st.pills(
            "View", options=("Set up", "Results", "Ask why"), required=True,
            key="ig_view", label_visibility="collapsed", width="stretch",
        )
    with reset_column:
        st.button(
            "Reset", on_click=reset, width="stretch",
            help="Restore the baseline and clear this chapter’s simulation.",
        )

if notice := st.session_state.pop("ig_notice", None):
    st.success(notice)
if st.session_state.ig_error:
    st.error(st.session_state.ig_error)

history = st.session_state.ig_history
try:
    draft_settings = submitted_settings()
except ValueError:
    draft_settings = None
dirty = bool(history) and draft_settings != st.session_state.ig_submitted

if view == "Set up":
    st.title("Build tomorrow’s economy.")
    st.write(
        "Households work and consume. The firm turns some output into capital "
        "that can produce more next period."
    )
    st.number_input(
        "Households", min_value=2, max_value=20, step=1,
        key="ig_count", on_change=resize,
    )

    for field in FIRM_FIELDS:
        value = st.session_state.ig_firm[field]
        st.session_state.setdefault(
            f"ig_firm_{field}", value * 100 if field in PERCENT_FIELDS else value
        )
    with setup_expander("Firm · production and investment", "firm", expanded=True):
        st.caption("STARTING RESOURCES")
        compact_input(
            "firm", "money", "Operating money", minimum=.01,
            maximum=1_000_000.0, step=.10,
        )
        compact_input(
            "firm", "capital", "Starting capital", minimum=.10,
            maximum=1_000_000.0, step=.10,
        )
        compact_input(
            "firm", "productivity", "Productivity", minimum=.10,
            maximum=100.0, step=.10,
        )
        st.caption("Productivity: X produced with 1 capital and 1 unit of work.")
        st.caption("EACH PERIOD")
        compact_input(
            "firm", "reinvestment_rate", "Reinvest surplus %", minimum=0.0,
            maximum=90.0, step=10.0,
        )
        compact_input(
            "firm", "depreciation_rate", "Capital wear %", minimum=0.0,
            maximum=90.0, step=5.0,
        )
        st.caption(
            "Surplus is output value minus wages, before wear. "
            f"Keep {st.session_state.ig_firm['reinvestment_rate']:.0%} of that "
            "value as new capital. Wear applies to opening capital only."
        )

    for index, household in enumerate(st.session_state.ig_households):
        for field in HOUSEHOLD_FIELDS:
            st.session_state.setdefault(
                f"ig_household_{field}_{index}", household[field]
            )
        with setup_expander(household["name"], f"household_{index}"):
            compact_input(
                "household", "money", "Starting money", minimum=0.0,
                maximum=1_000_000.0, step=.10, index=index,
            )
            st.caption("WHAT MATTERS MOST? · RELATIVE SCORES")
            for field, label in (
                ("consumption_priority", "Consume X"),
                ("money_priority", "Keep money"),
                ("leisure_priority", "Enjoy leisure"),
            ):
                compact_input(
                    "household", field, label, minimum=.01,
                    maximum=100.0, step=.10, index=index,
                )
            total = fsum(household[field] for field in HOUSEHOLD_FIELDS[1:])
            st.caption(
                f"{household['consumption_priority'] / total:.0%} consume · "
                f"{household['money_priority'] / total:.0%} money · "
                f"{household['leisure_priority'] / total:.0%} leisure. "
                "Equal scores give equal importance."
            )

    count = len(st.session_state.ig_households)
    household_money = fsum(item["money"] for item in st.session_state.ig_households)
    firm_money = st.session_state.ig_firm["money"]
    capital = st.session_state.ig_firm["capital"]
    with st.container(key="ig_starting_totals"):
        st.markdown("**Starting economy**")
        st.write(f"{count} households · {household_money + firm_money:g} Money · {capital:g} capital")
        st.caption(
            f"Money: {household_money:g} with households + {firm_money:g} with the firm. "
            f"Each household owns {1 / count:.0%} of the firm."
        )
    if dirty:
        st.info("Draft changed. Start a new simulation to apply these settings.")
    if history:
        st.caption("Starting again replaces this simulation’s history. Your draft stays saved when you switch tabs.")
    st.button("Start new simulation", type="primary", on_click=start, width="stretch")
    st.caption("Reset restores two equal households, 1 capital, 40% reinvestment and 10% wear.")
elif not history:
    st.info("Your economy is ready to set up. Start a simulation to see its first period.")
else:
    if dirty:
        st.info("Draft changed. This simulation continues with its original settings.")
    st.session_state.setdefault("ig_selected", st.session_state.ig_period_focus)
    selected = st.selectbox(
        "View period", options=list(range(1, len(history) + 1)),
        format_func=lambda number: f"Period {number}", key="ig_selected",
        on_change=select_period, label_visibility="collapsed",
    )
    with st.container(key="ig_period_controls"):
        advance_column, batch_column = st.columns([1, 1], gap="small")
        with advance_column:
            st.button(
                "Next period →", type="primary", on_click=next_period,
                width="stretch", disabled=len(history) >= MAX_PERIODS,
                help="Continue from the latest period in this simulation.",
            )
        with batch_column:
            st.button(
                "+10 periods", on_click=next_period, args=(10,), width="stretch",
                disabled=len(history) >= MAX_PERIODS,
                help="Continue ten linked periods from the latest result, up to 100.",
            )
    if len(history) >= MAX_PERIODS:
        st.caption(f"Reached {MAX_PERIODS} periods. Start a new simulation for another experiment.")
    elif selected != len(history):
        st.caption(f"Viewing history. Next period continues from Period {len(history)}.")
    report_scope = st.pills(
        "Report range", options=("This period", "Cumulative"), required=True,
        default="This period", key="ig_report_scope", width="stretch",
        label_visibility="collapsed",
    )
    report = investment_report(
        tuple(history[:selected]), cumulative=report_scope == "Cumulative"
    )
    if view == "Results":
        render_investment_results({
            "reporting": report,
            "diagnostics": dict(history[selected - 1].solution),
        })
    else:
        render_investment_chat(
            history[selected - 1], report,
            st.session_state.ig_generation, "ig_chat",
        )
