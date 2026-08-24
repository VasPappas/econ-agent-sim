import streamlit as st

from econ_agent_sim import run_economy_0
from econ_agent_sim.reporting import stock_flow_rows, transaction_rows

st.set_page_config(page_title="Agent Economy Simulator", layout="wide")
st.title("Agent Economy Simulator")
st.caption("Economy 0 — two agents, two goods, pure exchange")

result = run_economy_0()
steps = [
    "1. Opening stocks",
    "2. Prices and optimization",
    "3. Transactions",
    "4. Stock-flow reconciliation",
]
step = st.radio("Inspect the economy step by step", steps)

if step == steps[0]:
    st.write(result.opening_stocks)
elif step == steps[1]:
    st.write("Equilibrium prices", result.prices)
    st.write("Optimal bundles", result.desired_bundles)
elif step == steps[2]:
    st.dataframe(transaction_rows(result), use_container_width=True)
else:
    st.dataframe(stock_flow_rows(result), use_container_width=True)
    st.success("All stock-flow checks equal zero; both goods are conserved.")
