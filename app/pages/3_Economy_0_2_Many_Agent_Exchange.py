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
with nav_home:
    st.page_link("streamlit_app.py", label="← Simulator home", use_container_width=True)
with nav_prev:
    st.page_link(
        "pages/2_Economy_0_1_Walrasian_Price_Discovery.py",
        label="← Economy 0.1",
        use_container_width=True,
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

with st.sidebar:
    st.header("Economy 0.2 experiment")
    st.caption(
        "The canonical population is fixed at ten agents in this first interface. "
        "Change only the price-discovery path."
    )

    with st.form("economy02_inputs"):
        initial_price_x = st.number_input(
            "Initial trial price pX",
            min_value=0.01,
            value=float(current.initial_price_x),
            step=0.1,
        )
        adjustment_speed = st.slider(
            "Adjustment speed (lambda)",
            min_value=0.1,
            max_value=1.0,
            value=float(current.adjustment_speed),
            step=0.1,
        )
        apply_scenario = st.form_submit_button("Apply and reset")

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

st.progress(stage / max(settlement_stage, 1))

if stage < settlement_stage:
    step = result.steps[stage]
    st.markdown(
        f"### Price-discovery iteration {step.iteration} "
        f"— trial pX = {step.price_x:.6f}"
    )
else:
    st.markdown("### Markets cleared — execute many-agent settlement")

previous_col, next_col, finish_col, spacer_col = st.columns([1, 1, 1.5, 5])
with previous_col:
    if st.button("← Previous", disabled=stage == 0):
        st.session_state.economy02_stage -= 1
        st.rerun()
with next_col:
    if st.button("Next →", disabled=stage == settlement_stage):
        st.session_state.economy02_stage += 1
        st.rerun()
with finish_col:
    if st.button("Jump to settlement", disabled=stage == settlement_stage):
        st.session_state.economy02_stage = settlement_stage
        st.rerun()

market_col, accounting_col = st.columns([1.35, 1.0], gap="large")

with market_col:
    st.subheader("Many-agent market")

    benchmark_col, count_col, numeraire_col = st.columns(3)
    benchmark_col.metric(
        "Analytic benchmark pX",
        f"{result.benchmark_price_x:.6f}",
    )
    count_col.metric("Agents", len(config.agents))
    numeraire_col.metric("Numeraire pY", "1.000000")
    st.caption(
        "The analytic benchmark validates the experiment; tâtonnement does not "
        "use it when changing prices."
    )

    visible_step_count = min(stage + 1, len(result.steps))
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

    if stage < settlement_stage:
        step = result.steps[stage]
        x_supply_col, x_demand_col, x_excess_col = st.columns(3)
        x_supply_col.metric("X supply", f"{step.supply_x:.6f}")
        x_demand_col.metric("X demand", f"{step.demand_x:.6f}")
        x_excess_col.metric("X excess demand", f"{step.excess_demand_x:+.6f}")

        y_supply_col, y_demand_col, y_excess_col = st.columns(3)
        y_supply_col.metric("Y supply", f"{step.supply_y:.6f}")
        y_demand_col.metric("Y demand", f"{step.demand_y:.6f}")
        y_excess_col.metric("Y excess demand", f"{step.excess_demand_y:+.6f}")

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

        price_x = step.price_x
    else:
        st.success(
            f"Tâtonnement converged after {result.steps[-1].iteration} price "
            f"adjustments at pX = {result.prices['X']:.10f}."
        )
        st.write(
            "The clearing system now matches net sellers to net buyers, good by "
            "good. Every physical transfer becomes a ledger entry."
        )
        price_x = result.prices["X"]

    st.markdown("#### Agent decisions at this price")
    population_rows = []
    for spec in config.agents:
        wealth = price_x * spec.x + spec.y
        desired_x = spec.alpha * wealth / price_x
        desired_y = (1.0 - spec.alpha) * wealth
        population_rows.append(
            {
                "agent": spec.name,
                "opening X": spec.x,
                "opening Y": spec.y,
                "alpha": spec.alpha,
                "wealth": wealth,
                "desired X": desired_x,
                "desired Y": desired_y,
            }
        )
    st.dataframe(population_rows, use_container_width=True, hide_index=True)

with accounting_col:
    st.subheader("Stock-flow accounting")
    if stage < settlement_stage:
        st.caption(
            "No trade during tâtonnement. All ten agents still hold their "
            "opening endowments."
        )
        rows = accounting_rows(result, 0)
    else:
        st.caption(
            "Settlement executed. Every closing stock is opening stock plus "
            "ledgered net flows."
        )
        rows = accounting_rows(result)

    st.dataframe(rows, use_container_width=True, hide_index=True)
    if all(abs(row["check"]) < 1e-12 for row in rows):
        st.success("All accounting checks = 0")

st.divider()

if stage == settlement_stage:
    st.subheader("Settlement ledger")
    st.caption(
        "All entries share trade_id 1 because they are legs of one market-clearing "
        "settlement event; transaction_id uniquely identifies each transfer."
    )
    st.dataframe(
        transaction_rows(result),
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Final allocation")
    final_rows = []
    for spec in config.agents:
        closing = result.closing_stocks[spec.name]
        desired = result.desired_bundles[spec.name]
        final_rows.append(
            {
                "agent": spec.name,
                "closing X": closing["X"],
                "target X": desired["X"],
                "closing Y": closing["Y"],
                "target Y": desired["Y"],
            }
        )
    st.dataframe(final_rows, use_container_width=True, hide_index=True)
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
        st.dataframe(history_rows, use_container_width=True, hide_index=True)

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
