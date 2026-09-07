import streamlit as st

from econ_agent_sim.workspace_style import apply_workspace_style

st.set_page_config(page_title="Tiny Economy", layout="centered", initial_sidebar_state="collapsed")
apply_workspace_style()
st.caption("TINY ECONOMY")
st.title("Explore a tiny economy.")
st.write("Change one thing. Discover what follows.")
st.page_link(
    "pages/5_Economy_0_4_Monetary_Settlement.py",
    label="Start exploring →", width="stretch",
)
st.caption("Move a little Y. Watch prices respond. Follow the goods and money.")
with st.expander("A first experiment"):
    st.write(
        "Start with ten agents and move 0.10 Y from Agent 1 to Agent 2. "
        "Agent 1 prefers Y; Agent 2 prefers X. Which price do you expect to change?"
    )
    st.write(
        "Open Results to compare prices, inspect a trade, then use Ask why. "
        "The built-in explanations are instant; deeper questions use the AI assistant."
    )

st.divider()
st.subheader("Explore the building blocks")
st.caption("Each chapter adds one mechanism. Earlier economies remain fully runnable.")
chapters = [
    ("Exchange", "Two agents discover the gains from exchanging two goods.",
     "0", "pages/1_Economy_0_Pure_Exchange.py"),
    ("Price discovery", "Watch a trial price adjust until the market clears.",
     "0.1", "pages/2_Economy_0_1_Walrasian_Price_Discovery.py"),
    ("Many agents", "Different endowments and preferences meet in one market.",
     "0.2", "pages/3_Economy_0_2_Many_Agent_Exchange.py"),
    ("Redistribution", "Change who starts with Y and compare independent outcomes.",
     "0.3", "pages/4_Economy_0_3_Repeated_Exchange.py"),
    ("Money", "Follow each goods transfer and its reverse money payment.",
     "0.4", "pages/5_Economy_0_4_Monetary_Settlement.py"),
]
for title, description, version, page in chapters:
    with st.container(border=True):
        st.page_link(page, label=title, width="stretch")
        st.write(description)
        st.caption(f"Economy {version}")

with st.expander("What the model includes"):
    st.write(
        "Every economy keeps opening stocks, agent choices, prices, trades, "
        "closing stocks, and the accounting ledger available for inspection."
    )
    st.write(
        "In the Money chapter, money settles trades but does not limit purchases. "
        "There is no banking, credit, production, or money creation. Each experiment "
        "starts with fresh money; closing balances do not carry into the next experiment."
    )
