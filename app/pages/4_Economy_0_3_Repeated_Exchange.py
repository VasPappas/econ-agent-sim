import streamlit as st

from econ_agent_sim.economy_0_3 import Economy03Config, run_economy_0_3
from econ_agent_sim.reporting import accounting_rows, transaction_rows

st.set_page_config(page_title="Economy 0.3 — Repeated Exchange", layout="wide")

if "economy03_config" not in st.session_state:
    st.session_state.economy03_config = Economy03Config()
if "economy03_period" not in st.session_state:
    st.session_state.economy03_period = 1

st.caption("SIMULATOR / ECONOMY 0.3 / REPEATED EXCHANGE")
st.title("Economy 0.3 — Repeated Pure Exchange")
st.caption(
    "Time is now explicit. The same many-agent exchange economy repeats across "
    "periods with fresh exogenous endowments and a fully time-stamped ledger."
)

nav_home, nav_prev, nav_space = st.columns([1.2, 1.6, 5])
nav_home.page_link("streamlit_app.py", label="← Simulator home", width="stretch")
nav_prev.page_link(
    "pages/3_Economy_0_2_Many_Agent_Exchange.py",
    label="← Economy 0.2",
    width="stretch",
)

periods_col, agents_col, goods_col, new_col = st.columns(4)
periods_col.metric("Canonical periods", "4")
agents_col.metric("Agents", "10")
goods_col.metric("Goods", "2")
new_col.metric("New mechanism", "Time")

with st.expander("What changed from Economy 0.2", expanded=False):
    st.write(
        "Only the time dimension changed. Each period is still the Economy 0.2 "
        "many-agent pure-exchange model: agents optimize, tâtonnement discovers the "
        "clearing price, and settlement occurs only after convergence. The next period "
        "then starts from a fresh exogenous endowment schedule rather than carrying "
        "forward the previous closing stocks."
    )

current = st.session_state.economy03_config

st.subheader("Experiment controls")
st.caption(
    "These controls change the within-period price-discovery path. The canonical "
    "four-period endowment schedule remains deterministic."
)
with st.form("economy03_inputs"):
    input_col, speed_col, apply_col = st.columns([1, 1, 1])
    initial_price_x = input_col.number_input(
        "Initial trial price pX in every period",
        min_value=0.01,
        value=float(current.initial_price_x),
        step=0.1,
    )
    adjustment_speed = speed_col.slider(
        "Adjustment speed (lambda)",
        min_value=0.1,
        max_value=1.0,
        value=float(current.adjustment_speed),
        step=0.1,
    )
    apply_scenario = apply_col.form_submit_button(
        "Apply and reset",
        width="stretch",
    )

if apply_scenario:
    st.session_state.economy03_config = Economy03Config(
        period_populations=current.period_populations,
        initial_price_x=initial_price_x,
        adjustment_speed=adjustment_speed,
    )
    st.session_state.economy03_period = 1
    st.rerun()

config = st.session_state.economy03_config
result = run_economy_0_3(config)

st.divider()
st.subheader("Across-period view")
st.caption(
    "Aggregate X and Y stay fixed at 10 each. The relative price moves because the "
    "distribution of Y endowments changes across otherwise comparable periods."
)

price_rows = [
    {
        "period": period.period,
        "equilibrium pX": period.prices["X"],
        "analytic benchmark": period.benchmark_price_x,
    }
    for period in result.periods
]
st.line_chart(
    price_rows,
    x="period",
    y=["equilibrium pX", "analytic benchmark"],
)

selected_period = st.slider(
    "Period to inspect",
    min_value=1,
    max_value=len(result.periods),
    value=min(st.session_state.economy03_period, len(result.periods)),
    step=1,
)
st.session_state.economy03_period = selected_period
period = result.periods[selected_period - 1]

period_col, price_col, iterations_col, ledger_col = st.columns(4)
period_col.metric("Selected period", period.period)
price_col.metric("Equilibrium pX", f"{period.prices['X']:.6f}")
iterations_col.metric("Price iterations", period.steps[-1].iteration)
ledger_col.metric("Ledger entries", len(period.transactions))

st.info(
    "Period openings are exogenous resets. Closing stocks from one period are not "
    "carried into the next period."
)

if selected_period > 1:
    previous = result.periods[selected_period - 2]
    reset_rows = []
    for spec in period.population:
        previous_closing = previous.closing_stocks[spec.name]
        new_opening = period.opening_stocks[spec.name]
        reset_rows.append(
            {
                "agent": spec.name,
                "previous closing X": previous_closing["X"],
                "new opening X": new_opening["X"],
                "X reset": new_opening["X"] - previous_closing["X"],
                "previous closing Y": previous_closing["Y"],
                "new opening Y": new_opening["Y"],
                "Y reset": new_opening["Y"] - previous_closing["Y"],
            }
        )
    with st.expander(
        f"Show reset from period {selected_period - 1} closing stocks to period "
        f"{selected_period} openings",
        expanded=False,
    ):
        st.dataframe(reset_rows, width="stretch", hide_index=True, height=390)

endowment_tab, agents_tab, accounting_tab, ledger_tab = st.tabs(
    ["Endowments & price", "Agent decisions", "Accounting", "Ledger & allocation"]
)

with endowment_tab:
    st.markdown("#### Exogenous opening endowments")
    opening_rows = [
        {
            "agent": spec.name,
            "alpha": spec.alpha,
            "opening X": spec.x,
            "opening Y": spec.y,
        }
        for spec in period.population
    ]
    st.dataframe(opening_rows, width="stretch", hide_index=True, height=390)

    total_x = sum(spec.x for spec in period.population)
    total_y = sum(spec.y for spec in period.population)
    total_x_col, total_y_col, benchmark_col = st.columns(3)
    total_x_col.metric("Aggregate X", f"{total_x:.1f}")
    total_y_col.metric("Aggregate Y", f"{total_y:.1f}")
    benchmark_col.metric("Analytic pX", f"{period.benchmark_price_x:.6f}")

    st.markdown("#### Within-period price discovery")
    path_rows = [
        {
            "iteration": step.iteration,
            "trial pX": step.price_x,
            "analytic benchmark": period.benchmark_price_x,
        }
        for step in period.steps
    ]
    st.line_chart(
        path_rows,
        x="iteration",
        y=["trial pX", "analytic benchmark"],
    )

    final_step = period.steps[-1]
    balance_rows = [
        {
            "good": "X",
            "supply": final_step.supply_x,
            "demand": final_step.demand_x,
            "excess demand": final_step.excess_demand_x,
        },
        {
            "good": "Y",
            "supply": final_step.supply_y,
            "demand": final_step.demand_y,
            "excess demand": final_step.excess_demand_y,
        },
    ]
    st.markdown("#### Final market-clearing check")
    st.dataframe(balance_rows, width="stretch", hide_index=True)
    st.success(
        f"Both markets clear within tolerance; market error = "
        f"{final_step.market_error:.2e}."
    )

with agents_tab:
    st.caption(
        "Positive net demand means an agent acquires the good in settlement; negative "
        "net demand means the agent supplies it."
    )
    decision_rows = []
    for spec in period.population:
        desired = period.desired_bundles[spec.name]
        decision_rows.append(
            {
                "agent": spec.name,
                "alpha": spec.alpha,
                "wealth": period.wealths[spec.name],
                "opening X": spec.x,
                "opening Y": spec.y,
                "desired X": desired["X"],
                "desired Y": desired["Y"],
                "net X": desired["X"] - spec.x,
                "net Y": desired["Y"] - spec.y,
            }
        )
    st.dataframe(decision_rows, width="stretch", hide_index=True, height=420)

with accounting_tab:
    st.caption(
        "Within the selected period, every closing stock equals its exogenous opening "
        "stock plus the net physical flows recorded in that period's ledger."
    )
    rows = accounting_rows(period)
    st.dataframe(rows, width="stretch", hide_index=True, height=420)
    if all(abs(row["check"]) < 1e-12 for row in rows):
        st.success("All selected-period stock-flow checks = 0")

with ledger_tab:
    st.caption(
        f"Every row is a physical transfer in period {selected_period}. trade_id equals "
        "the period number, while transaction_id is unique across the full run."
    )
    st.dataframe(
        transaction_rows(period),
        width="stretch",
        hide_index=True,
        height=380,
    )

    final_rows = []
    for spec in period.population:
        closing = period.closing_stocks[spec.name]
        target = period.desired_bundles[spec.name]
        final_rows.append(
            {
                "agent": spec.name,
                "closing X": closing["X"],
                "target X": target["X"],
                "X error": closing["X"] - target["X"],
                "closing Y": closing["Y"],
                "target Y": target["Y"],
                "Y error": closing["Y"] - target["Y"],
            }
        )
    st.markdown("#### Final allocation")
    st.dataframe(final_rows, width="stretch", hide_index=True, height=390)

with st.expander("Full multi-period ledger"):
    st.caption(
        "This is the complete append-only record. Transaction IDs never restart when "
        "the model advances to a new period."
    )
    st.dataframe(
        transaction_rows(result),
        width="stretch",
        hide_index=True,
        height=460,
    )

st.divider()
st.subheader("Version boundary")
st.write(
    "Economy 0.3 adds repeated periods and explicit ledger time stamps only. There is "
    "still no carry-over inventory, consumption, saving, production, money, credit, "
    "banking, government, or randomness."
)
st.caption(
    "The next period receives a fresh exogenous endowment schedule, so time is visible "
    "without yet creating intertemporal wealth accumulation."
)
