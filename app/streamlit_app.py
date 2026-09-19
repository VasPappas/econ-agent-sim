"""One workspace for the forward-looking monetary Tiny Economy."""

from dataclasses import asdict

import streamlit as st

from econ_agent_sim.comparison import compare_runs
from econ_agent_sim.domain import MAX_PERIODS, Settings
from econ_agent_sim.experiments import dumps_experiment, restore_experiment
from econ_agent_sim.explanations import QUESTIONS, amount, explain
from econ_agent_sim.presets import PRESETS, build_preset
from econ_agent_sim.reporting import build_report, export_csv
from econ_agent_sim.ui_text import literal
from econ_agent_sim.workspace import (
    advance,
    clear_baseline,
    edit_baseline_copy,
    initialize,
    rename,
    reset,
    save_baseline,
    select_period,
    set_draft,
    start,
)
from econ_agent_sim.workspace_style import apply_workspace_style

# Percentages are a display choice only. Persisted settings use decimal values.
CONTROLS = (
    ("beta", "Future importance (%)", 50., 99., 1., 100.,
     ("A value of 95 means an equally enjoyable period one step ahead receives "
     "95% of today's weight. Higher values give future consumption more importance.")),
    ("depreciation", "Capital wear each period (%)", 1., 100., 1., 100.,
     ("The share of opening capital that wears out each period. "
     "Investment adds capital for the next period.")),
    ("leisure_weight", "Value of leisure", .05, 10., .05, 1.,
     "Importance of free time relative to consumption. Higher values favor leisure."),
    ("money_weight", "Value of keeping money", .001, 5., .01, 1.,
     ("Importance of purchasing power held as cash. Money provides a service "
     "in this model; this is a preference weight, not an interest rate.")),
    ("initial_capital", "Capital per firm", .01, 1000., .1, 1.,
     "Each of the two identical firms begins with this much productive capital."),
    ("initial_firm_cash_share", "Money held by firms (%)", 1., 99., 1., 100.,
     ("The two firms share this fraction of the economy's fixed one unit of money. "
     "Households share the rest. Firms must fund wages before goods sales.")),
)


def sync_widgets():
    """Refresh UI copies only from callbacks, before widgets are instantiated."""
    state = st.session_state
    for field, _, _, _, _, scale, _ in CONTROLS:
        state[f"te_input_{field}"] = float(getattr(state.te_draft, field) * scale)
    state.te_period_picker = state.te_selected_period
    state.te_scope_picker = state.te_scope
    state.te_name_input = state.te_name


def capture_draft():
    state = st.session_state
    values = asdict(state.te_draft)
    for field, _, _, _, _, scale, _ in CONTROLS:
        if f"te_input_{field}" in state:
            values[field] = state[f"te_input_{field}"] / scale
    set_draft(state, Settings(**values))


def use_preset():
    set_draft(st.session_state, build_preset(st.session_state.te_preset_choice))
    sync_widgets()


def start_run():
    capture_draft()
    with st.spinner("Finding a forward-looking path and checking its payments…"):
        start(st.session_state)
    sync_widgets()


def advance_run(count):
    advance(st.session_state, count)
    st.session_state.te_period_picker = st.session_state.te_selected_period


def change_period():
    select_period(st.session_state, st.session_state.te_period_picker)


def change_scope():
    st.session_state.te_scope = st.session_state.te_scope_picker


def rename_run():
    rename(st.session_state, st.session_state.te_name_input)
    st.session_state.te_name_input = st.session_state.te_name


def reset_run():
    reset(st.session_state)
    sync_widgets()


def copy_baseline():
    edit_baseline_copy(st.session_state)
    sync_widgets()


def open_experiment():
    upload = st.session_state.get("te_upload")
    if upload is not None:
        with st.spinner("Opening the experiment and verifying its path…"):
            restore_experiment(st.session_state, upload.getvalue())
        sync_widgets()


def go_to_setup():
    st.session_state.te_view = "Set up"


def render_setup(dirty):
    st.title("An economy that looks ahead.")
    st.write(
        "Households plan work, spending and saving. Firms plan investment and "
        "dividends. Their choices must fit together, today and in the future."
    )
    with st.expander("Choose a starting experiment"):
        key = st.selectbox(
            "Starting experiment", options=tuple(PRESETS), key="te_preset_choice",
            format_func=lambda value: PRESETS[value].title,
        )
        st.write(PRESETS[key].description)
        st.button("Use this setup", on_click=use_preset, width="stretch")
        st.caption("Applying a preset edits your draft. Start a simulation to use it.")

    st.subheader("Six choices to explore")
    for field, label, minimum, maximum, step, scale, help_text in CONTROLS:
        st.session_state.setdefault(
            f"te_input_{field}", float(getattr(st.session_state.te_draft, field) * scale)
        )
        st.number_input(
            label, min_value=minimum, max_value=maximum, step=step, format="%.12g",
            key=f"te_input_{field}", help=help_text,
            on_change=capture_draft,
        )
    settings = st.session_state.te_draft
    with st.container(key="te_starting_totals"):
        st.markdown("**Two identical households · two identical firms**")
        st.write(
            f"Total starting capital: {2 * settings.initial_capital:.5g} · "
            "Total money: 1"
        )
        st.caption(
            f"Each firm holds {settings.initial_firm_cash_share / 2:.5g} Money; "
            f"each household holds {(1 - settings.initial_firm_cash_share) / 2:.5g}. "
            "Each household owns half of each firm."
        )
    if dirty:
        st.info("Draft changed. Start a new simulation to apply these settings.")
    if st.session_state.te_run is not None:
        st.caption("Starting again replaces these results. Save a baseline to compare.")
    st.button(
        "Start new simulation", type="primary", width="stretch", on_click=start_run,
    )
    st.caption(
        "Choose a tested preset if a custom setup cannot be solved. "
        "Your draft stays saved when you switch views."
    )


def render_experiments():
    state = st.session_state
    with st.expander("Save, open and compare experiments"):
        state.setdefault("te_name_input", state.te_name)
        st.text_input("Experiment name", key="te_name_input", on_change=rename_run)
        st.download_button(
            "Download experiment", data=dumps_experiment(state),
            file_name="tiny-economy.json", mime="application/json", width="stretch",
        )
        st.file_uploader("Choose a saved experiment", type=["json"], key="te_upload")
        st.button(
            "Open experiment", on_click=open_experiment, width="stretch",
            disabled=state.get("te_upload") is None,
        )
        st.caption(
            "Files from the earlier one-period model cannot be opened in this model. "
            "Start a new experiment with these six settings."
        )
        st.button(
            "Save as baseline", on_click=save_baseline, args=(state,),
            disabled=state.te_run is None, width="stretch",
        )
        if state.te_baseline is not None:
            baseline = state.te_baseline
            st.caption(
                f"Baseline: {literal(baseline.name)} · "
                f"{baseline.visible_periods} periods. Compare the same period in both runs."
            )
            st.button("Copy baseline setup", on_click=copy_baseline, width="stretch")
            st.button(
                "Clear baseline", on_click=clear_baseline, args=(state,), width="stretch",
            )
        st.button("Reset to default", on_click=reset_run, width="stretch")
        st.caption("Reset clears the current draft and run. A saved baseline stays available.")


def render_model():
    with st.expander("How this economy works"):
        st.markdown(
            "**One good, a fixed amount of money, and plans that look ahead.** "
            "Households value consumption, leisure and the purchasing power of cash. "
            "Firms use capital and work to produce the good; output can be consumed "
            "or kept as new capital."
        )
        st.write(
            "Firms pay dividends and wages from opening cash, before households buy "
            "goods. There is no borrowing or money creation. Money and productive "
            "capital carry into the next period. Firms can pause investment or dividends."
        )
        st.write(
            "This is a symmetric teaching model with perfect foresight: agents know "
            "the future path, and prices and wages clear markets. The two households "
            "make identical choices, as do the two firms. It does not yet model "
            "uncertainty, unemployment from rationing, inventory or price adjustment."
        )
        st.caption(
            "A run reveals up to 100 periods from one plan with a checked longer "
            "continuation. Reaching the displayed end does not make firms liquidate "
            "capital. Cases where firms optimally retain unused opening cash are "
            "not yet supported; an unsuccessful setup leaves existing results intact."
        )


def account_table(entries, columns):
    st.dataframe(
        [{label: (entry[field] if field == "name" else amount(entry[field]))
          for field, label in columns} for entry in entries],
        hide_index=True, width="stretch",
    )


def render_comparison(selected, cumulative):
    state = st.session_state
    baseline = state.te_baseline
    if baseline is None:
        return
    with st.expander("Compare with baseline", expanded=True):
        st.caption(f"Baseline: {literal(baseline.name)}")
        if selected > baseline.visible_periods:
            st.info(
                f"Both experiments need Period {selected} to compare it. "
                f"The baseline currently has {baseline.visible_periods} periods. "
                "Select an earlier period to compare equal ranges."
            )
            return
        comparison = compare_runs(
            state.te_run, baseline.run, selected_period=selected,
            cumulative=cumulative, current_name=state.te_name,
            baseline_name=baseline.name,
        )
        st.dataframe(
            [{"Measure": metric["label"], "Unit": metric["unit"],
              "Baseline": amount(metric["baseline"]),
              "Current": amount(metric["current"]),
              "Change": amount(metric["change"]),
              "Change unit": metric["change_unit"]} for metric in comparison["metrics"]],
            hide_index=True, width="stretch",
        )
        st.caption(comparison["note"])
        if comparison["settings_changes"]:
            st.caption("Changed settings (percentage controls are shown as decimals here).")
            st.dataframe(
                [{"Setting": change["label"], "Baseline": amount(change["baseline"]),
                  "Current": amount(change["current"])}
                 for change in comparison["settings_changes"]],
                hide_index=True, width="stretch",
            )


def render_trends(run, selected):
    if selected < 2:
        st.caption("Advance a few periods to see trends.")
        return
    with st.expander("Trends through this period", expanded=True):
        quantities, capital, prices, work = st.tabs(
            ("Production", "Capital", "Prices", "Work")
        )
        records = run.periods[:selected]
        with quantities:
            st.line_chart(
                [{"Period": row.number, "Output": 2 * row.output,
                  "Consumption": 2 * row.consumption, "Investment": 2 * row.investment}
                 for row in records], x="Period", y=["Output", "Consumption", "Investment"],
                x_label="Period", y_label="X per period",
            )
        with capital:
            st.line_chart(
                [{"Period": row.number, "Capital": 2 * row.next_capital}
                 for row in records], x="Period", y="Capital",
                x_label="Period", y_label="Total capital at period end",
            )
        with prices:
            st.line_chart(
                [{"Period": row.number, "Goods price": row.goods_price,
                  "Money wage": row.money_wage} for row in records],
                x="Period", y=["Goods price", "Money wage"],
                x_label="Period", y_label="Money per X / work unit",
            )
            st.caption("A price is Money per X; a wage is Money per unit of work.")
        with work:
            st.line_chart(
                [{"Period": row.number, "Work": 100 * row.labor,
                  "Leisure": 100 * (1 - row.labor)} for row in records],
                x="Period", y=["Work", "Leisure"],
                x_label="Period", y_label="% of each household's time",
            )


def render_results(report, selected):
    state = st.session_state
    economy = report["economy"]
    st.subheader(report["label"])
    output, consumption = st.columns(2)
    output.metric("Total output · X", amount(economy["produced_x"]))
    consumption.metric("Total consumption · X", amount(economy["consumed_x"]))
    investment, capital = st.columns(2)
    investment.metric("Total investment · X", amount(economy["investment_quantity"]))
    capital.metric("Closing capital · units", amount(economy["capital_close"]))
    st.caption(
        "Output, consumption and investment cover the selected range. "
        "Capital and cash are balances at its end. Money flows use each period's prices."
    )
    st.write(
        f"Period {selected} · X price **{amount(report['price'])} Money** · "
        f"Wage **{amount(report['wage'])} Money per work unit**"
    )
    st.caption(
        f"One unit of work buys {amount(report['real_wage'])} X. "
        "A work unit is one household working for a full period."
    )
    st.subheader("Households")
    st.caption("Each row is one household. Identical households make identical choices.")
    account_table(report["households"], (
        ("name", "Household"), ("consumed_x", "Consumption · X"),
        ("total_work", "Work · periods"), ("closing_money", "Closing cash · Money"),
    ))
    st.caption(
        f"Each household works {economy['average_work']:.1%} of its available time "
        f"and has {economy['average_leisure']:.1%} leisure"
        + (" on average over this range." if report["period_count"] > 1 else ".")
    )
    with st.expander("Household cash and ownership"):
        account_table(report["households"], (
            ("name", "Household"), ("opening_money", "Opening cash"),
            ("wages_received", "Wages received"), ("dividends_received", "Dividends received"),
            ("purchases_paid", "Goods purchases"), ("closing_money", "Closing cash"),
        ))
        account_table(report["households"], (
            ("name", "Household"), ("ownership_value_close", "Firm ownership value"),
            ("assets_close", "Cash + ownership value"),
        ))
        st.caption(
            "Money units. Opening cash + wages + dividends − purchases = closing cash. "
            "Each household owns half of both firms; ownership value is not spendable cash."
        )
    st.subheader("Firms")
    st.caption("Each row is one firm. Both firms share the same technology and starting resources.")
    account_table(report["firms"], (
        ("name", "Firm"), ("produced_x", "Output · X"), ("sold_x", "Sold · X"),
        ("investment_quantity", "Investment · X"), ("capital_close", "Closing capital"),
    ))
    first = report["firms"][0]
    if first["zero_investment_periods"]:
        st.info(
            f"Both firms invest zero in {first['zero_investment_periods']} "
            "period(s) of this range. Existing capital can keep producing while it wears out."
        )
    if first["zero_dividend_periods"]:
        st.info(
            f"Both firms pay no dividend in {first['zero_dividend_periods']} "
            "period(s) of this range. Available opening cash must also fund wages."
        )
    with st.expander("Firm cash, capital and profit"):
        account_table(report["firms"], (
            ("name", "Firm"), ("opening_money", "Opening cash"),
            ("sales_received", "Sales receipts"), ("wages_paid", "Wages paid"),
            ("dividends_paid", "Dividends paid"), ("closing_money", "Closing cash"),
        ))
        account_table(report["firms"], (
            ("name", "Firm"), ("capital_open", "Opening capital"),
            ("investment_quantity", "Added"), ("depreciation_quantity", "Worn out"),
            ("capital_close", "Closing capital"),
        ))
        account_table(report["firms"], (
            ("name", "Firm"), ("net_operating_profit", "Operating profit"),
            ("holding_gain", "Capital revaluation"), ("equity_close", "Closing equity"),
        ))
        st.caption(
            "Cash and profit use Money; the capital bridge uses physical units. "
            "Retained output becomes capital without a cash purchase. Operating profit "
            "includes retained output and deducts wages and wear. Price changes revalue "
            "capital separately and do not create cash."
        )
    render_trends(state.te_run, selected)
    render_comparison(selected, report["scope"] == "cumulative")
    st.download_button(
        "Download results · CSV", export_csv(state.te_run, state.te_visible_periods),
        file_name="tiny-economy-results.csv", mime="text/csv", width="stretch",
    )
    st.caption(f"Exports all {state.te_visible_periods} revealed periods with full precision.")
    with st.expander("Check the accounts"):
        if all(report["checks"].values()):
            st.success("Money, goods, capital and ownership accounts balance.")
        else:
            st.error("An account check failed. Do not rely on these results.")
        st.write(f"Total closing money: {amount(economy['closing_money'])} Money.")
        st.caption(
            "The accepted plan also passed household and firm optimality, funded-payment "
            "and longer-horizon checks. These are numerical checks within the model's assumptions."
        )


def render_run(view, dirty):
    state = st.session_state
    if dirty:
        st.info("Draft changed. This simulation continues with its original settings.")
    state.setdefault("te_period_picker", state.te_selected_period)
    st.selectbox(
        "View period", options=list(range(1, state.te_visible_periods + 1)),
        format_func=lambda value: f"Period {value}", key="te_period_picker",
        on_change=change_period,
    )
    selected = state.te_selected_period
    with st.container(key="te_period_controls"):
        one, ten = st.columns(2, gap="small")
        one.button(
            "Next period →", type="primary", on_click=advance_run, args=(1,),
            width="stretch", disabled=state.te_visible_periods >= MAX_PERIODS,
        )
        ten.button(
            "+10 periods", on_click=advance_run, args=(10,),
            width="stretch", disabled=state.te_visible_periods >= MAX_PERIODS,
        )
    if state.te_visible_periods >= MAX_PERIODS:
        st.caption("All 100 periods are revealed. You can review them or start a new experiment.")
    elif selected != state.te_visible_periods:
        st.caption(f"Viewing history. Advance continues from Period {state.te_visible_periods}.")
    state.setdefault("te_scope_picker", state.te_scope)
    st.pills(
        "Report range", options=("This period", "Cumulative"), required=True,
        key="te_scope_picker", on_change=change_scope, width="stretch",
    )
    cumulative = state.te_scope == "Cumulative"
    if view == "Results":
        render_results(build_report(state.te_run, selected, cumulative), selected)
    else:
        st.title("Ask why")
        st.caption("Explanations use your selected period and the model's equations.")
        question = st.selectbox("Explore a question", options=QUESTIONS, key="te_question")
        st.write(explain(question, state.te_run, selected, cumulative=cumulative))


st.set_page_config(
    page_title="Tiny Economy", layout="centered", initial_sidebar_state="collapsed",
)
initialize(st.session_state)
apply_workspace_style()
st.caption(f"TINY ECONOMY · {literal(st.session_state.te_name)}")
with st.container(key="te_mobile_nav"):
    view = st.pills(
        "View", options=("Set up", "Results", "Ask why"), required=True,
        key="te_view", label_visibility="collapsed", width="stretch",
    )
if notice := st.session_state.pop("te_notice", None):
    st.success(literal(notice))
if error := st.session_state.te_error:
    st.error(literal(error))
run = st.session_state.te_run
dirty = run is not None and st.session_state.te_draft != run.settings
if view == "Set up":
    render_setup(dirty)
elif run is None:
    st.info("Start a simulation to explore what households and firms choose.")
    st.button("Go to set up", on_click=go_to_setup, width="stretch")
else:
    render_run(view, dirty)
render_experiments()
render_model()
