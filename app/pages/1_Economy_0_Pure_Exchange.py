import streamlit as st

from econ_agent_sim import Economy0Config, run_economy_0
from econ_agent_sim.reporting import accounting_rows, transaction_rows

st.set_page_config(page_title="Economy 0 — Pure Exchange", layout="wide")

if "economy0_config" not in st.session_state:
    st.session_state.economy0_config = Economy0Config()
if "economy0_step" not in st.session_state:
    st.session_state.economy0_step = 0

st.caption("SIMULATOR / ECONOMY 0 / FOUNDATION")
st.title("Economy 0 — Pure Exchange")
st.caption(
    "The smallest permanent economy: two optimizing agents, two goods, an analytic "
    "Walrasian equilibrium, explicit barter settlement, and stock-flow accounting."
)

nav_home, nav_next, nav_space = st.columns([1.2, 1.8, 5])
with nav_home:
    st.page_link("streamlit_app.py", label="← Simulator home", use_container_width=True)
with nav_next:
    st.page_link(
        "pages/2_Economy_0_1_Walrasian_Price_Discovery.py",
        label="Next: Economy 0.1 →",
        use_container_width=True,
    )

agents_col, goods_col, price_col, new_col = st.columns(4)
agents_col.metric("Agents", "2")
goods_col.metric("Goods", "2")
price_col.metric("Price formation", "Analytic")
new_col.metric("New mechanism", "Baseline")

with st.expander("What this version teaches", expanded=False):
    st.write(
        "Economy 0 isolates the core exchange problem. Agents optimize their desired "
        "bundles at equilibrium prices, every physical transfer is written to the "
        "ledger, and closing stocks must reconcile with opening stocks plus net flows."
    )

current_config = st.session_state.economy0_config

with st.sidebar:
    st.header("Experiment inputs")
    st.caption("Change the economy, then apply it. These are experiments, not calibration.")
    with st.form("economy0_inputs"):
        st.markdown("**Alice**")
        alice_x = st.number_input(
            "Alice: initial X", min_value=0.0, value=float(current_config.alice_x)
        )
        alice_y = st.number_input(
            "Alice: initial Y", min_value=0.0, value=float(current_config.alice_y)
        )
        alice_alpha = st.slider(
            "Alice: preference for X (alpha)",
            min_value=0.05,
            max_value=0.95,
            value=float(current_config.alice_alpha),
            step=0.05,
        )

        st.markdown("**Bob**")
        bob_x = st.number_input(
            "Bob: initial X", min_value=0.0, value=float(current_config.bob_x)
        )
        bob_y = st.number_input(
            "Bob: initial Y", min_value=0.0, value=float(current_config.bob_y)
        )
        bob_alpha = st.slider(
            "Bob: preference for X (alpha)",
            min_value=0.05,
            max_value=0.95,
            value=float(current_config.bob_alpha),
            step=0.05,
        )
        apply_scenario = st.form_submit_button("Apply scenario and reset")

    if apply_scenario:
        try:
            st.session_state.economy0_config = Economy0Config(
                alice_x=alice_x,
                alice_y=alice_y,
                alice_alpha=alice_alpha,
                bob_x=bob_x,
                bob_y=bob_y,
                bob_alpha=bob_alpha,
            )
        except ValueError as exc:
            st.error(str(exc))
        else:
            st.session_state.economy0_step = 0
            st.rerun()

config = st.session_state.economy0_config
result = run_economy_0(config)

steps = [
    "Setup",
    "Opening stocks",
    "Agent optimization",
    "Market clearing",
]
for index, transaction in enumerate(result.transactions, start=1):
    steps.append(f"Transaction {index}: {transaction.good}")
steps.append("Final reconciliation")

step_index = min(st.session_state.economy0_step, len(steps) - 1)
st.session_state.economy0_step = step_index

st.progress(step_index / max(len(steps) - 1, 1))
st.markdown(f"### Step {step_index + 1} of {len(steps)} — {steps[step_index]}")

back_col, next_col, reset_col, spacer_col = st.columns([1, 1, 1, 5])
with back_col:
    if st.button("← Previous", disabled=step_index == 0):
        st.session_state.economy0_step -= 1
        st.rerun()
with next_col:
    if st.button("Next →", disabled=step_index == len(steps) - 1):
        st.session_state.economy0_step += 1
        st.rerun()
with reset_col:
    if st.button("Reset steps"):
        st.session_state.economy0_step = 0
        st.rerun()

transaction_start = 4
if step_index < transaction_start:
    executed_transactions = 0
elif step_index < transaction_start + len(result.transactions):
    executed_transactions = step_index - transaction_start + 1
else:
    executed_transactions = len(result.transactions)

process_col, accounting_col = st.columns([1.25, 1.0], gap="large")

with process_col:
    st.subheader("Economic process")

    if step_index == 0:
        st.write(
            "Two agents own X and Y. There is no money, production, government, "
            "banking, or randomness. Each agent maximizes Cobb-Douglas utility."
        )
        st.latex(r"U_i(X,Y)=X^{\alpha_i}Y^{1-\alpha_i}")
        st.info(
            "Use the controls on the left to change endowments or preferences. "
            "The engine then solves the same textbook economy again."
        )

    elif step_index == 1:
        opening_rows = [
            {
                "agent": agent,
                "X": stocks["X"],
                "Y": stocks["Y"],
            }
            for agent, stocks in result.opening_stocks.items()
        ]
        st.write("These stocks exist before any decisions or trades occur.")
        st.dataframe(opening_rows, use_container_width=True, hide_index=True)

    elif step_index == 2:
        st.write(
            "At the equilibrium prices, each agent values the initial endowment "
            "and chooses the utility-maximizing affordable bundle."
        )
        alpha_by_agent = {
            "Alice": config.alice_alpha,
            "Bob": config.bob_alpha,
        }
        for agent in ("Alice", "Bob"):
            desired = result.desired_bundles[agent]
            st.markdown(f"**{agent}**")
            st.write(
                f"alpha = {alpha_by_agent[agent]:.2f}; "
                f"wealth = {result.wealths[agent]:.4f}; "
                f"optimal bundle = ({desired['X']:.4f} X, {desired['Y']:.4f} Y)."
            )
        st.latex(
            r"X_i^*=\alpha_i\frac{w_i}{p_X},\quad "
            r"Y_i^*=(1-\alpha_i)\frac{w_i}{p_Y}"
        )

    elif step_index == 3:
        total_x = sum(stocks["X"] for stocks in result.opening_stocks.values())
        total_y = sum(stocks["Y"] for stocks in result.opening_stocks.values())
        demand_x = sum(bundle["X"] for bundle in result.desired_bundles.values())
        demand_y = sum(bundle["Y"] for bundle in result.desired_bundles.values())
        st.write(
            "Only relative prices matter, so Y is the numeraire: pY = 1. "
            "The model solves pX analytically so both markets clear."
        )
        st.latex(
            r"p_X=\frac{\sum_i \alpha_i y_i^0}"
            r"{\sum_i (1-\alpha_i)x_i^0},\qquad p_Y=1"
        )
        price_col, numeraire_col = st.columns(2)
        price_col.metric("Equilibrium pX", f"{result.prices['X']:.4f}")
        numeraire_col.metric("Numeraire pY", f"{result.prices['Y']:.4f}")
        market_rows = [
            {
                "good": "X",
                "supply": total_x,
                "demand": demand_x,
                "excess_demand": demand_x - total_x,
            },
            {
                "good": "Y",
                "supply": total_y,
                "demand": demand_y,
                "excess_demand": demand_y - total_y,
            },
        ]
        st.dataframe(market_rows, use_container_width=True, hide_index=True)

    elif step_index < transaction_start + len(result.transactions):
        transaction_number = step_index - transaction_start + 1
        transaction = result.transactions[transaction_number - 1]
        st.write(
            f"Ledger entry {transaction.transaction_id}: {transaction.sender} "
            f"transfers {transaction.quantity:.4f} {transaction.good} to "
            f"{transaction.receiver}."
        )
        st.info(
            "The simulator changes holdings only through explicit ledger entries. "
            "The accounting panel updates immediately after this transfer."
        )

    else:
        st.success("Economy 0 reconciles exactly.")
        st.write(
            "Every closing stock equals its opening stock plus cumulative net flows. "
            "Total X and total Y are conserved across the whole economy."
        )
        final_rows = [
            {
                "agent": agent,
                "X": stocks["X"],
                "Y": stocks["Y"],
            }
            for agent, stocks in result.closing_stocks.items()
        ]
        st.dataframe(final_rows, use_container_width=True, hide_index=True)

with accounting_col:
    st.subheader("Stock-flow accounting")
    st.caption("This panel is displayed at every step.")
    current_rows = accounting_rows(result, executed_transactions)
    st.dataframe(current_rows, use_container_width=True, hide_index=True)
    if all(abs(row["check"]) < 1e-12 for row in current_rows):
        st.success("All row-level accounting checks = 0")

st.divider()
st.subheader("Transaction ledger — executed so far")
ledger_rows = transaction_rows(result, executed_transactions)
if ledger_rows:
    st.dataframe(ledger_rows, use_container_width=True, hide_index=True)
else:
    st.caption("No transaction has been executed yet.")

st.caption(
    "Economy 0 is deterministic and runs entirely in memory. No database is used yet."
)
