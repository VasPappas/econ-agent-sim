import streamlit as st

st.set_page_config(page_title="Agent Economy Simulator", layout="wide")

st.caption("AGENT-BASED ECONOMIC SIMULATOR")
st.title("Build the economy one mechanism at a time")
st.write(
    "This simulator starts from the smallest textbook exchange economy and adds one "
    "economic mechanism at a time. Every completed version remains permanently "
    "runnable, traceable, and stock-flow consistent."
)

version_col, assets_col, frontier_col, accounting_col = st.columns(4)
version_col.metric("Permanent economies", "5")
assets_col.metric("Assets so far", "X · Y · Money")
frontier_col.metric("Current frontier", "Economy 0.4")
accounting_col.metric("Accounting rule", "Stock = opening + flows")

st.divider()
st.subheader("Choose an economy")
st.caption(
    "Each version changes one structural feature while preserving the mechanisms "
    "that came before it."
)

row_one_left, row_one_right = st.columns(2, gap="large")

with row_one_left, st.container(border=True):
    st.markdown("### Economy 0")
    st.markdown("**Pure exchange foundation**")
    st.write(
        "Two agents, two goods, Cobb-Douglas optimization, analytic equilibrium "
        "prices, explicit barter settlement, and a fully traceable ledger."
    )
    st.caption("New mechanism: the baseline exchange economy")
    st.page_link(
        "pages/1_Economy_0_Pure_Exchange.py",
        label="Open Economy 0 →",
        width="stretch",
    )

with row_one_right, st.container(border=True):
    st.markdown("### Economy 0.1")
    st.markdown("**Walrasian price discovery**")
    st.write(
        "The same two-agent economy, but the relative price is now discovered "
        "iteratively through textbook tâtonnement before any trade occurs."
    )
    st.caption("New mechanism: endogenous price discovery")
    st.page_link(
        "pages/2_Economy_0_1_Walrasian_Price_Discovery.py",
        label="Open Economy 0.1 →",
        width="stretch",
    )

row_two_left, row_two_right = st.columns(2, gap="large")

with row_two_left, st.container(border=True):
    st.markdown("### Economy 0.2")
    st.markdown("**Many-agent pure exchange**")
    st.write(
        "The market expands to a deterministic heterogeneous population while "
        "retaining the same optimization, price discovery, ledger, and accounting."
    )
    st.caption("New mechanism: population size and heterogeneity")
    st.page_link(
        "pages/3_Economy_0_2_Many_Agent_Exchange.py",
        label="Open Economy 0.2 →",
        width="stretch",
    )

with row_two_right, st.container(border=True):
    st.markdown("### Economy 0.3")
    st.markdown("**Redistribution across periods**")
    st.write(
        "Start from the Economy 0.2 baseline, then create as many new periods as you "
        "want by redistributing Y between agents and observing the new equilibrium."
    )
    st.caption("New mechanism: time through user-chosen exogenous redistribution")
    st.page_link(
        "pages/4_Economy_0_3_Repeated_Exchange.py",
        label="Open Economy 0.3 →",
        width="stretch",
    )

with st.container(border=True):
    st.markdown("### Economy 0.4")
    st.markdown("**Money and monetary settlement**")
    st.write(
        "Keep the same real X/Y exchange economy and repeated redistribution "
        "experiment, but settle every goods transfer with an explicit reverse money "
        "payment. Money appears on every agent balance sheet and in the ledger."
    )
    st.caption("New mechanism: money as a settlement asset")
    st.page_link(
        "pages/5_Economy_0_4_Monetary_Settlement.py",
        label="Open Economy 0.4 →",
        width="stretch",
    )

st.divider()
st.subheader("How the simulator evolves")

comparison_rows = [
    {
        "version": "Economy 0",
        "agents": "2",
        "price formation": "Analytic equilibrium",
        "settlement": "Two-agent barter ledger",
        "time": "No",
        "money": "No",
    },
    {
        "version": "Economy 0.1",
        "agents": "2",
        "price formation": "Walrasian tâtonnement",
        "settlement": "After convergence",
        "time": "No",
        "money": "No",
    },
    {
        "version": "Economy 0.2",
        "agents": "10 canonical / arbitrary engine",
        "price formation": "Walrasian tâtonnement",
        "settlement": "Many-agent clearing ledger",
        "time": "No",
        "money": "No",
    },
    {
        "version": "Economy 0.3",
        "agents": "10 canonical / fixed identities",
        "price formation": "Tâtonnement each period",
        "settlement": "Time-stamped goods ledger",
        "time": "User-added redistribution periods",
        "money": "No",
    },
    {
        "version": "Economy 0.4",
        "agents": "10 canonical / arbitrary engine populations",
        "price formation": "Tâtonnement each period",
        "settlement": "Goods leg + reverse money payment",
        "time": "User-added redistribution periods",
        "money": "Settlement asset; no liquidity constraint yet",
    },
]
st.dataframe(comparison_rows, use_container_width=True, hide_index=True)

left, right = st.columns([1.25, 1], gap="large")
with left:
    st.subheader("What never gets hidden")
    st.write(
        "At every stage, the simulator keeps the economic process inspectable: "
        "opening stocks, agent choices, market-clearing logic, transfers and payments, "
        "closing stocks, and accounting checks."
    )
    st.info(
        "A completed economy is never overwritten by a later one. Use the pages in "
        "the sidebar or the cards above to move backward and forward through versions."
    )

with right:
    st.subheader("Current boundary")
    st.write(
        "Economy 0.4 has explicit money balances and monetary payment legs, but money "
        "does not enter utility or constrain purchases yet. The real X/Y equilibrium "
        "is therefore unchanged by the amount of opening money."
    )
    st.caption(
        "There is still no cash-in-advance constraint, banking, credit, interest, "
        "production, government, money creation, or intertemporal saving."
    )
