import streamlit as st

from econ_agent_sim.economy_0 import Economy0Config
from econ_agent_sim.economy_0_1 import Economy01Config, run_economy_0_1
from econ_agent_sim.reporting import accounting_rows, transaction_rows

st.set_page_config(page_title="Economy 0.1 — Price Discovery", layout="wide")

if "economy01_config" not in st.session_state:
    st.session_state.economy01_config = Economy01Config()
if "economy01_stage" not in st.session_state:
    st.session_state.economy01_stage = 0

st.title("Economy 0.1 — Walrasian Price Discovery")
st.caption(
    "Same pure-exchange economy as Economy 0, now discovering the relative price "
    "through textbook tâtonnement."
)

current = st.session_state.economy01_config
exchange = current.exchange

with st.sidebar:
    st.header("Economy 0.1 experiment")
    st.caption("Change inputs, apply the scenario, then step through price discovery.")

    with st.form("economy01_inputs"):
        st.markdown("**Alice**")
        alice_x = st.number_input(
            "Alice: initial X",
            min_value=0.0,
            value=float(exchange.alice_x),
            key="e01_alice_x",
        )
        alice_y = st.number_input(
            "Alice: initial Y",
            min_value=0.0,
            value=float(exchange.alice_y),
            key="e01_alice_y",
        )
        alice_alpha = st.slider(
            "Alice: preference for X (alpha)",
            min_value=0.05,
            max_value=0.95,
            value=float(exchange.alice_alpha),
            step=0.05,
            key="e01_alice_alpha",
        )

        st.markdown("**Bob**")
        bob_x = st.number_input(
            "Bob: initial X",
            min_value=0.0,
            value=float(exchange.bob_x),
            key="e01_bob_x",
        )
        bob_y = st.number_input(
            "Bob: initial Y",
            min_value=0.0,
            value=float(exchange.bob_y),
            key="e01_bob_y",
        )
        bob_alpha = st.slider(
            "Bob: preference for X (alpha)",
            min_value=0.05,
            max_value=0.95,
            value=float(exchange.bob_alpha),
            step=0.05,
            key="e01_bob_alpha",
        )

        st.markdown("**Price discovery**")
        initial_price_x = st.number_input(
            "Initial trial price pX",
            min_value=0.01,
            value=float(current.initial_price_x),
            step=0.1,
            key="e01_initial_px",
        )
        adjustment_speed = st.slider(
            "Adjustment speed (lambda)",
            min_value=0.1,
            max_value=1.0,
            value=float(current.adjustment_speed),
            step=0.1,
            key="e01_lambda",
        )

        apply_scenario = st.form_submit_button("Apply scenario and reset")

    if apply_scenario:
        try:
            new_exchange = Economy0Config(
                alice_x=alice_x,
                alice_y=alice_y,
                alice_alpha=alice_alpha,
                bob_x=bob_x,
                bob_y=bob_y,
                bob_alpha=bob_alpha,
            )
            st.session_state.economy01_config = Economy01Config(
                exchange=new_exchange,
                initial_price_x=initial_price_x,
                adjustment_speed=adjustment_speed,
            )
        except ValueError as exc:
            st.error(str(exc))
        else:
            st.session_state.economy01_stage = 0
            st.rerun()

config = st.session_state.economy01_config
result = run_economy_0_1(config)

# Each tâtonnement iteration is a stage. The final extra stage is settlement.
settlement_stage = len(result.steps)
st.session_state.economy01_stage = min(
    st.session_state.economy01_stage,
    settlement_stage,
)
stage = st.session_state.economy01_stage

progress = stage / max(settlement_stage, 1)
st.progress(progress)

if stage < settlement_stage:
    step = result.steps[stage]
    st.markdown(
        f"### Price-discovery iteration {step.iteration} "
        f"— trial pX = {step.price_x:.6f}"
    )
else:
    st.markdown("### Price discovery converged — execute barter settlement")

previous_col, next_col, finish_col, spacer_col = st.columns([1, 1, 1.4, 5])
with previous_col:
    if st.button("← Previous", disabled=stage == 0):
        st.session_state.economy01_stage -= 1
        st.rerun()
with next_col:
    if st.button("Next →", disabled=stage == settlement_stage):
        st.session_state.economy01_stage += 1
        st.rerun()
with finish_col:
    if st.button("Jump to settlement", disabled=stage == settlement_stage):
        st.session_state.economy01_stage = settlement_stage
        st.rerun()

left, right = st.columns([1.25, 1.0], gap="large")

with left:
    st.subheader("Price discovery")

    benchmark_col, discovered_col = st.columns(2)
    benchmark_col.metric("Economy 0 analytic benchmark pX", f"{result.benchmark_price_x:.6f}")
    discovered_col.metric("Numeraire pY", "1.000000")
    st.caption(
        "The benchmark is displayed for validation only. The tâtonnement update "
        "does not use it."
    )

    visible_step_count = min(stage + 1, len(result.steps))
    path_rows = [
        {
            "iteration": step.iteration,
            "trial pX": step.price_x,
            "analytic benchmark": result.benchmark_price_x,
        }
        for step in result.steps[:visible_step_count]
    ]
    st.line_chart(
        path_rows,
        x="iteration",
        y=["trial pX", "analytic benchmark"],
    )

    if stage < settlement_stage:
        step = result.steps[stage]
        supply_col, demand_col, excess_col = st.columns(3)
        supply_col.metric("Supply of X", f"{step.supply_x:.6f}")
        demand_col.metric("Demand for X", f"{step.demand_x:.6f}")
        excess_col.metric("Excess demand", f"{step.excess_demand_x:+.6f}")

        if step.next_price_x is None:
            st.success(
                "Excess demand is within the numerical tolerance. Price discovery "
                "has converged; the next stage executes the trade."
            )
        elif step.excess_demand_x > 0:
            st.info(
                f"Demand exceeds supply, so pX rises to {step.next_price_x:.6f}."
            )
        else:
            st.info(
                f"Supply exceeds demand, so pX falls to {step.next_price_x:.6f}."
            )

        st.latex(
            r"p_{t+1}=p_t\left(1+\lambda\frac{z_X(p_t)}{\bar X}\right)"
        )
    else:
        st.success(
            f"Tâtonnement converged after {result.steps[-1].iteration} price "
            f"adjustments at pX = {result.prices['X']:.10f}."
        )
        st.write(
            "Only now does barter settlement occur. The price-search phase itself "
            "did not change anybody's holdings."
        )
        st.dataframe(
            transaction_rows(result),
            use_container_width=True,
            hide_index=True,
        )

    with st.expander("Iteration history"):
        history_rows = [
            {
                "iteration": step.iteration,
                "pX": step.price_x,
                "supply_X": step.supply_x,
                "demand_X": step.demand_x,
                "excess_demand_X": step.excess_demand_x,
                "normalized_excess": step.normalized_excess_demand_x,
                "next_pX": step.next_price_x,
            }
            for step in result.steps[:visible_step_count]
        ]
        st.dataframe(history_rows, use_container_width=True, hide_index=True)

with right:
    st.subheader("Stock-flow accounting")
    if stage < settlement_stage:
        st.caption("No trade during tâtonnement: holdings remain at opening stocks.")
        rows = accounting_rows(result, 0)
    else:
        st.caption("Settlement executed: flows now reconcile opening and closing stocks.")
        rows = accounting_rows(result)

    st.dataframe(rows, use_container_width=True, hide_index=True)
    if all(abs(row["check"]) < 1e-12 for row in rows):
        st.success("All accounting checks = 0")

st.divider()
st.subheader("What Economy 0.1 added")
st.write(
    "Only price discovery changed. Preferences, endowments, optimization, barter "
    "settlement, the ledger, and stock-flow accounting are inherited from the "
    "Economy 0 framework."
)
st.caption(
    "Walrasian tâtonnement is a textbook theoretical benchmark, not a literal "
    "description of how all real markets operate."
)
