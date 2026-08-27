import streamlit as st

from econ_agent_sim.economy_0_2 import Economy02Config, run_economy_0_2
from econ_agent_sim.reporting import accounting_rows, transaction_rows

st.set_page_config(page_title="Economy 0.2 — Many-Agent Exchange", layout="wide")

if "economy02_config" not in st.session_state:
    st.session_state.economy02_config = Economy02Config()
if "economy02_stage" not in st.session_state:
    st.session_state.economy02_stage = 0

st.caption("SIMULATOR / ECONOMY 0.2 / MANY-AGENT EXCHANGE")
st.title("Economy 0.2 — Many-Agent Pure Exchange")
st.caption(
    "The same two-good exchange model now supports an arbitrary heterogeneous "
    "population; the canonical laboratory uses ten deterministic agents."
)

nav_home, nav_prev, nav_space = st.columns([1.2, 1.6, 5])
nav_home.page_link("streamlit_app.py", label="← Simulator home", width="stretch")
nav_prev.page_link(
    "pages/2_Economy_0_1_Walrasian_Price_Discovery.py",
    label="← Economy 0.1",
    width="stretch",
)

agents_col, goods_col, price_col, new_col = st.columns(4)
agents_col.metric("Canonical agents", "10")
goods_col.metric("Goods", "2")
price_col.metric("Price formation", "Tâtonnement")
new_col.metric("New mechanism", "Heterogeneity")

with st.expander("What changed from Economy 0.1", expanded=False):
    st.write(
        "Only population size and heterogeneity changed. The engine now works with "
        "an arbitrary collection of named agents instead of being built around Alice "
        "and Bob. Price discovery, optimization, settlement, the ledger, and stock-flow "
        "accounting keep the same logic."
    )

current = st.session_state.economy02_config

st.subheader("Experiment controls")
st.caption(
    "These controls change only the price-discovery path. The canonical ten-agent "
    "population stays fixed in this interface."
)
with st.form("economy02_inputs"):
    input_col, speed_col, apply_col = st.columns([1, 1, 1])
    initial_price_x = input_col.number_input(
        "Initial trial price pX",
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
    st.session_state.economy02_config = Economy02Config(
        agents=current.agents,
        initial_price_x=initial_price_x,
        adjustment_speed=adjustment_speed,
    )
    st.session_state.economy02_stage = 0
    st.rerun()

config = st.session_state.economy02_config
result = run_economy_0_2(config)

settlement_stage = len(result.steps)
st.session_state.economy02_stage = min(
    st.session_state.economy02_stage,
    settlement_stage,
)
stage = st.session_state.economy02_stage
visible_step_count = min(stage + 1, len(result.steps))

if stage < settlement_stage:
    step = result.steps[stage]
    phase = "Price discovery"
    current_price_x = step.price_x
    current_market_error = step.market_error
else:
    step = result.steps[-1]
    phase = "Settlement"
    current_price_x = result.prices["X"]
    current_market_error = step.market_error

st.divider()
st.subheader("Simulation stage")

stage_col, phase_col, current_price_col, error_col = st.columns(4)
stage_col.metric("Stage", f"{stage + 1} / {settlement_stage + 1}")
phase_col.metric("Phase", phase)
current_price_col.metric("Current pX", f"{current_price_x:.6f}")
error_col.metric("Market error", f"{current_market_error:.2e}")

st.progress(stage / max(settlement_stage, 1))

if stage < settlement_stage:
    st.markdown(f"### Iteration {step.iteration}: test pX = {step.price_x:.6f}")
else:
    st.markdown("### Markets cleared: execute many-agent settlement")

previous_col, next_col, finish_col = st.columns(3)
if previous_col.button("← Previous", disabled=stage == 0, width="stretch"):
    st.session_state.economy02_stage -= 1
    st.rerun()
if next_col.button(
    "Next →",
    disabled=stage == settlement_stage,
    width="stretch",
):
    st.session_state.economy02_stage += 1
    st.rerun()
if finish_col.button(
    "Jump to settlement",
    disabled=stage == settlement_stage,
    width="stretch",
):
    st.session_state.economy02_stage = settlement_stage
    st.rerun()

market_tab, agents_tab = st.tabs(["Market process", "Agent decisions"])

with market_tab:
    benchmark_col, count_col, numeraire_col = st.columns(3)
    benchmark_col.metric(
        "Analytic benchmark pX",
        f"{result.benchmark_price_x:.6f}",
    )
    count_col.metric("Agents", len(config.agents))
    numeraire_col.metric("Numeraire pY", "1.000000")
    st.caption(
        "The analytic benchmark is shown only for validation. Tâtonnement does not "
        "use it when changing the trial price."
    )

    path_rows = [
        {
            "iteration": item.iteration,
            "trial pX": item.price_x,
            "analytic benchmark": result.benchmark_price_x,
        }
        for item in result.steps[:visible_step_count]
    ]
    st.line_chart(
        path_rows,
        x="iteration",
        y=["trial pX", "analytic benchmark"],
    )

    balance_rows = [
        {
            "good": "X",
            "supply": step.supply_x,
            "demand": step.demand_x,
            "excess demand": step.excess_demand_x,
        },
        {
            "good": "Y",
            "supply": step.supply_y,
            "demand": step.demand_y,
            "excess demand": step.excess_demand_y,
        },
    ]
    st.markdown("#### Market balance at this stage")
    st.dataframe(balance_rows, width="stretch", hide_index=True)

    if stage < settlement_stage:
        if step.next_price_x is None:
            st.success(
                "Both markets are within the clearing tolerance. The next stage "
                "settles the agents' net trades."
            )
        elif step.excess_demand_x > 0:
            st.info(
                f"Aggregate X demand exceeds supply, so pX rises to "
                f"{step.next_price_x:.6f}."
            )
        else:
            st.info(
                f"Aggregate X supply exceeds demand, so pX falls to "
                f"{step.next_price_x:.6f}."
            )
    else:
        st.success(
            f"Tâtonnement converged after {result.steps[-1].iteration} price "
            f"adjustments at pX = {result.prices['X']:.10f}."
        )
        st.write(
            "Only now does the clearing system match net sellers to net buyers. "
            "Every physical transfer becomes a ledger entry."
        )

with agents_tab:
    st.caption(
        "Positive net demand means an agent wants to acquire that good; negative net "
        "demand means the agent wants to give some up at the current price."
    )
    population_rows = []
    for spec in config.agents:
        wealth = current_price_x * spec.x + spec.y
        desired_x = spec.alpha * wealth / current_price_x
        desired_y = (1.0 - spec.alpha) * wealth
        population_rows.append(
            {
                "agent": spec.name,
                "alpha": spec.alpha,
                "opening X": spec.x,
                "opening Y": spec.y,
                "wealth": wealth,
                "desired X": desired_x,
                "desired Y": desired_y,
                "net X": desired_x - spec.x,
                "net Y": desired_y - spec.y,
            }
        )
    st.dataframe(
        population_rows,
        width="stretch",
        hide_index=True,
        height=390,
    )

st.divider()
st.subheader("Stock-flow checkpoint")
if stage < settlement_stage:
    st.caption(
        "No trade occurs during tâtonnement. Every agent still holds the opening "
        "endowment, so all flows are zero."
    )
    rows = accounting_rows(result, 0)
else:
    st.caption(
        "Settlement has executed. Every closing stock must equal opening stock plus "
        "ledgered net flows."
    )
    rows = accounting_rows(result)

st.dataframe(rows, width="stretch", hide_index=True, height=390)
if all(abs(row["check"]) < 1e-12 for row in rows):
    st.success("All stock-flow checks = 0")

st.divider()

if stage == settlement_stage:
    st.subheader("Settlement results")
    transactions = result.transactions
    transfer_x = sum(
        transaction.quantity
        for transaction in transactions
        if transaction.good == "X"
    )
    transfer_y = sum(
        transaction.quantity
        for transaction in transactions
        if transaction.good == "Y"
    )

    entries_col, x_transfer_col, y_transfer_col = st.columns(3)
    entries_col.metric("Ledger entries", len(transactions))
    x_transfer_col.metric("X transferred", f"{transfer_x:.6f}")
    y_transfer_col.metric("Y transferred", f"{transfer_y:.6f}")

    ledger_tab, allocation_tab = st.tabs(["Settlement ledger", "Final allocation"])

    with ledger_tab:
        st.caption(
            "All entries share trade_id 1 because they are legs of one market-clearing "
            "event; transaction_id uniquely identifies each transfer."
        )
        st.dataframe(
            transaction_rows(result),
            width="stretch",
            hide_index=True,
            height=420,
        )

    with allocation_tab:
        final_rows = []
        for spec in config.agents:
            closing = result.closing_stocks[spec.name]
            desired = result.desired_bundles[spec.name]
            final_rows.append(
                {
                    "agent": spec.name,
                    "closing X": closing["X"],
                    "target X": desired["X"],
                    "X error": closing["X"] - desired["X"],
                    "closing Y": closing["Y"],
                    "target Y": desired["Y"],
                    "Y error": closing["Y"] - desired["Y"],
                }
            )
        st.dataframe(
            final_rows,
            width="stretch",
            hide_index=True,
            height=390,
        )
else:
    with st.expander("Price-discovery history so far"):
        history_rows = [
            {
                "iteration": item.iteration,
                "pX": item.price_x,
                "X excess demand": item.excess_demand_x,
                "Y excess demand": item.excess_demand_y,
                "market error": item.market_error,
                "next pX": item.next_price_x,
            }
            for item in result.steps[:visible_step_count]
        ]
        st.dataframe(history_rows, width="stretch", hide_index=True)

st.divider()
st.subheader("Version boundary")
st.write(
    "Economy 0.2 changes population size and heterogeneity only. There is still no "
    "money, production, time, banking, government, saving, or randomness."
)
st.caption(
    "The canonical ten-agent population is deterministic so the economy remains "
    "exactly reproducible."
)
