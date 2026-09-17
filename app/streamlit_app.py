"""The single Tiny Economy workspace: set up, explore results, and ask why."""

from math import fsum

import streamlit as st

from econ_agent_sim.comparison import compare_runs
from econ_agent_sim.experiment_view import (
    initialize_experiments,
    render_experiment_controls,
)
from econ_agent_sim.explanation_view import render_explanations
from econ_agent_sim.presets import PRESETS, build_preset
from econ_agent_sim.reporting import build_report
from econ_agent_sim.results_component import render_results
from econ_agent_sim.ui_text import literal
from econ_agent_sim.workspace import (
    FIRM_FIELDS,
    HOUSEHOLD_FIELDS,
    MAX_PERIODS,
    PERCENT_FIELDS,
    PREFERENCE_FIELDS,
    apply_household_preferences,
    apply_preset,
    capture,
    initialize,
    next_period,
    remember_expander,
    remember_report_scope,
    resize,
    select_period,
    start,
    submitted_settings,
)
from econ_agent_sim.workspace_style import apply_workspace_style


def setup_expander(label, name, *, expanded=False):
    """Keep disclosure state when widgets and navigation trigger a rerun."""
    key = f"te_open_{name}"
    st.session_state.setdefault(key, st.session_state.te_expanded.get(name, expanded))
    return st.expander(
        literal(label), expanded=expanded, key=key,
        on_change=remember_expander, args=(st.session_state, name),
    )


def compact_input(owner, field, label, *, minimum, maximum, step, index):
    """One mobile-sized label and a native accessible numeric stepper."""
    with st.container(key=f"te_compact_{owner}_{field}_{index}"):
        label_column, input_column = st.columns(
            [1, 1.45], gap="small", vertical_alignment="center"
        )
        label_column.markdown(f"**{label}**")
        with input_column:
            st.number_input(
                label, min_value=minimum, max_value=maximum, step=step,
                format="%.0f" if field in PERCENT_FIELDS else "%.2f",
                key=f"te_{owner}_{field}_{index}", on_change=capture,
                args=(st.session_state,), label_visibility="collapsed",
            )


def use_selected_preset():
    preset = PRESETS[st.session_state.te_preset_choice]
    households, firms = build_preset(preset.key)
    apply_preset(st.session_state, households, firms, preset.title)


def go_to_setup():
    st.session_state.te_view = "Set up"


def select_firm(firm_id):
    st.session_state.te_selected_firm = firm_id


def render_setup(dirty):
    st.title("Build your tiny economy.")
    st.write(
        "Households choose work, consumption and leisure. "
        "Two firms produce X and decide how much to reinvest."
    )
    with setup_expander("Choose a starting experiment", "presets"):
        preset_key = st.selectbox(
            "Starting experiment", options=tuple(PRESETS),
            format_func=lambda key: PRESETS[key].title, key="te_preset_choice",
        )
        st.write(PRESETS[preset_key].description)
        st.button(
            "Use this setup", on_click=use_selected_preset, width="stretch",
            help="Replace the editable setup. Existing results and the baseline stay saved.",
        )
        st.caption(
            "Each preset fills the draft with two households and two firms. "
            "Start a new simulation when you are ready."
        )

    st.number_input(
        "Households", min_value=2, max_value=20, step=1,
        key="te_count", on_change=resize, args=(st.session_state,),
    )
    st.caption("Two firms share one goods market and one labor market.")

    for index, firm in enumerate(st.session_state.te_firms):
        for field in FIRM_FIELDS:
            value = firm[field]
            st.session_state.setdefault(
                f"te_firm_{field}_{index}",
                value * 100 if field in PERCENT_FIELDS else value,
            )
        with setup_expander(firm["name"], f"firm_{index}", expanded=index == 0):
            st.caption("STARTING RESOURCES")
            for field, label, minimum, maximum in (
                ("money", "Operating money", .01, 1_000_000.0),
                ("capital", "Starting capital", .10, 1_000_000.0),
                ("productivity", "Productivity", .10, 100.0),
            ):
                compact_input(
                    "firm", field, label, minimum=minimum,
                    maximum=maximum, step=.10, index=index,
                )
            st.caption("Productivity: X produced with 1 capital and 1 unit of work.")
            st.caption("EACH PERIOD")
            compact_input(
                "firm", "reinvestment_rate", "Reinvest surplus %", minimum=0.0,
                maximum=90.0, step=10.0, index=index,
            )
            compact_input(
                "firm", "depreciation_rate", "Capital wear %", minimum=0.0,
                maximum=90.0, step=5.0, index=index,
            )
            st.caption(
                "Reinvestment uses a share of output value after wages. "
                "Wear uses a share of opening capital. Equal percentages need not balance."
            )

    for index, household in enumerate(st.session_state.te_households):
        for field in HOUSEHOLD_FIELDS:
            st.session_state.setdefault(
                f"te_household_{field}_{index}", household[field]
            )
        with setup_expander(household["name"], f"household_{index}"):
            compact_input(
                "household", "money", "Starting money", minimum=0.0,
                maximum=1_000_000.0, step=.10, index=index,
            )
            compact_input(
                "household", "consumption_target", "Target · X per period",
                minimum=0.0, maximum=100.0, step=.10, index=index,
            )
            st.caption(
                "Below the target, consuming more becomes more urgent. "
                "The target is not guaranteed; 0 turns it off."
            )
            st.caption("PREFERENCES · HIGHER MEANS MORE IMPORTANT")
            for field, label in (
                ("consumption_priority", "Consume X"),
                ("money_priority", "Keep money"),
                ("leisure_priority", "Leisure"),
            ):
                compact_input(
                    "household", field, label, minimum=.01,
                    maximum=100.0, step=.10, index=index,
                )
            total = fsum(household[field] for field in PREFERENCE_FIELDS)
            st.caption(
                f"Relative importance: {household['consumption_priority'] / total:.0%} "
                f"consumption · {household['money_priority'] / total:.0%} money · "
                f"{household['leisure_priority'] / total:.0%} leisure. "
                "These are preferences, not spending or time shares."
            )
            if index == 0:
                st.button(
                    "Copy preferences and target to all",
                    key="te_copy_preferences", on_click=apply_household_preferences,
                    args=(st.session_state,), width="stretch",
                    help="Copy Household 1’s three preferences and target to every household. "
                         "Keep each household’s starting money.",
                )
                st.caption("Copies Household 1 only; starting money stays unchanged.")

    count = len(st.session_state.te_households)
    household_money = fsum(item["money"] for item in st.session_state.te_households)
    firm_money = fsum(item["money"] for item in st.session_state.te_firms)
    capital = fsum(item["capital"] for item in st.session_state.te_firms)
    target = fsum(item["consumption_target"] for item in st.session_state.te_households)
    with st.container(key="te_starting_totals"):
        st.markdown("**Starting economy**")
        st.write(
            f"{count} households · 2 firms · "
            f"{household_money + firm_money:.2f} Money · {capital:.2f} capital"
        )
        st.write(f"Consumption targets · {target:.2f} X each period")
        st.caption(
            f"Money: {household_money:g} with households + {firm_money:g} with firms. "
            f"Each household owns {1 / count:.1%} of each firm."
        )
    if dirty:
        st.info("Draft changed. Start a new simulation to apply these settings.")
    if st.session_state.te_history:
        st.caption(
            "Starting again replaces this simulation’s history. "
            "Save it as a baseline in Experiment if you want to compare."
        )
    st.button(
        "Start new simulation", type="primary", on_click=start,
        args=(st.session_state,), width="stretch",
    )
    st.caption("Your setup stays saved when you switch tabs.")


def render_run(view, history, dirty):
    if dirty:
        st.info("Draft changed. This simulation continues with its original settings.")
    st.session_state.setdefault("te_selected", st.session_state.te_period_focus)
    selected = st.selectbox(
        "View period", options=list(range(1, len(history) + 1)),
        format_func=lambda number: f"Period {number}", key="te_selected",
        on_change=select_period, args=(st.session_state,),
        label_visibility="collapsed",
    )
    with st.container(key="te_period_controls"):
        advance_column, batch_column = st.columns([1, 1], gap="small")
        with advance_column:
            st.button(
                "Next period →", type="primary", on_click=next_period,
                args=(st.session_state,), width="stretch",
                disabled=len(history) >= MAX_PERIODS,
                help="Continue from the latest period in this simulation.",
            )
        with batch_column:
            st.button(
                "+10 periods", on_click=next_period,
                args=(st.session_state, 10), width="stretch",
                disabled=len(history) >= MAX_PERIODS,
                help="Continue ten linked periods from the latest result, up to 100.",
            )
    if len(history) >= MAX_PERIODS:
        st.caption(f"Reached {MAX_PERIODS} periods. Start a new simulation for another experiment.")
    elif selected != len(history):
        st.caption(f"Viewing history. Next period continues from Period {len(history)}.")
    st.session_state.setdefault("te_report_scope", st.session_state.te_saved_scope)
    report_scope = st.pills(
        "Report range", options=("This period", "Cumulative"), required=True,
        key="te_report_scope", width="stretch", label_visibility="collapsed",
        on_change=remember_report_scope, args=(st.session_state,),
    )
    report = build_report(
        tuple(history[:selected]), cumulative=report_scope == "Cumulative"
    )
    baseline = st.session_state.te_baseline
    comparison = compare_runs(
        tuple(history), baseline.periods,
        selected_period=selected, cumulative=report_scope == "Cumulative",
        current_name=st.session_state.te_experiment_name,
        baseline_name=baseline.name,
    ) if baseline is not None else None
    if view == "Results":
        solution = history[selected - 1].solution
        diagnostics = {
            key: solution[key] for key in (
                "method", "iterations", "relative_market_error",
                "resting_households", "tolerance", "candidate_count",
                "selected_candidate", "selection_rule", "reference_price",
                "root_search_complete",
            ) if key in solution and isinstance(solution[key], (str, int, float, bool))
        }
        if "candidate_prices" in solution:
            diagnostics["candidate_prices"] = list(solution["candidate_prices"])
        render_results(
            {
                "reporting": report,
                "diagnostics": diagnostics,
                "comparison": comparison,
                "selected_firm": st.session_state.te_selected_firm,
            },
            on_select_firm=select_firm,
        )
    else:
        render_explanations(history[selected - 1], report, comparison=comparison)


st.set_page_config(
    page_title="Tiny Economy", layout="centered", initial_sidebar_state="collapsed",
)
initialize(st.session_state)
initialize_experiments()
apply_workspace_style()
st.caption(f"TINY ECONOMY · {literal(st.session_state.te_experiment_name)}")
if target_view := st.session_state.pop("te_next_view", None):
    st.session_state.te_view = target_view
with st.container(key="te_mobile_nav"):
    view = st.pills(
        "View", options=("Set up", "Results", "Ask why"), required=True,
        key="te_view", label_visibility="collapsed", width="stretch",
    )

if notice := st.session_state.pop("te_notice", None):
    st.success(literal(notice))
if st.session_state.te_error:
    st.error(literal(st.session_state.te_error))
history = st.session_state.te_history
try:
    draft_settings = submitted_settings(st.session_state)
except ValueError:
    draft_settings = None
dirty = bool(history) and draft_settings != st.session_state.te_submitted

if view == "Set up":
    render_setup(dirty)
elif not history:
    st.info("Start a simulation to see what your households and firms do.")
    st.button("Go to set up", on_click=go_to_setup, width="stretch")
else:
    render_run(view, history, dirty)

render_experiment_controls(setup_expander)
with setup_expander("How this economy works", "model"):
    st.markdown(
        "**One good, two firms, a fixed amount of money.** "
        "Households own equal shares of both firms. Each period, they choose work, "
        "consumption and money to keep. Firms hire, produce X and reinvest part of their surplus."
    )
    st.write(
        "Prices and wages clear the markets each period. Households consume all the X "
        "they buy. Money and capital carry forward; there is no borrowing or money creation."
    )
    st.caption(
        "The model uses textbook economic building blocks with explicit teaching "
        "assumptions: households plan one period at a time, money enters their preferences, "
        "firms use a chosen reinvestment rate, and consumption targets add urgency below "
        "the target. Preferences can affect work as well as spending."
    )
