import streamlit as st

from econ_agent_sim.workspace_style import apply_workspace_style

st.set_page_config(page_title="Tiny Economy", layout="centered", initial_sidebar_state="collapsed")
apply_workspace_style()
st.caption("TINY ECONOMY")
st.title("Explore a tiny economy.")
st.write("Change one thing. Discover what follows.")
with st.container(key="economy_home_start"):
    st.page_link(
        "pages/6_Economy_0_5_Good_and_Money.py",
        label="Start exploring →", width="stretch",
    )
st.caption("Set up your agents. Press Run. Follow the goods and money.")
st.page_link("pages/10_Economy_0_9_Investment_and_Growth.py",
             label="New · Investment and growth →", width="stretch")
st.page_link("pages/9_Economy_0_8_Firms_and_Wages.py",
             label="Firms, wages and dividends →", width="stretch")
st.page_link("pages/8_Economy_0_7_Work_and_Leisure.py",
             label="Work, leisure and production →", width="stretch")
with st.expander("A first experiment"):
    st.write(
        "Start with two agents, each with 1 X, 1 Money, and equal preferences. "
        "Press Run: neither needs to trade. Then change one agent's quantities "
        "or preferences and Run again. What changes?"
    )
    st.write(
        "Results compare your latest run with the previous one. Inspect a trade, then use Ask why. "
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
    ("Good and money", "Choose between one good and holding money, without borrowing.",
     "0.5", "pages/6_Economy_0_5_Good_and_Money.py"),
    ("Production and consumption", "Produce, trade and consume across periods. Money carries forward.",
     "0.6", "pages/7_Economy_0_6_Production_and_Consumption.py"),
    ("Work and leisure", "Agents choose how much to work, produce and consume, keeping time for leisure.",
     "0.7", "pages/8_Economy_0_7_Work_and_Leisure.py"),
    ("Firms and wages", "Households supply labor to a firm, receive wages and share its delayed profits.",
     "0.8", "pages/9_Economy_0_8_Firms_and_Wages.py"),
    ("Investment and growth", "Use some production for capital. Explore consumption today and capacity tomorrow.",
     "0.9", "pages/10_Economy_0_9_Investment_and_Growth.py"),
]
for title, description, version, page in chapters:
    with st.container(border=True):
        st.page_link(page, label=title, width="stretch")
        st.write(description)
        st.caption(f"Economy {version}")

with st.expander("What the model includes"):
    st.write("In Investment and growth, the firm uses labor and capital to produce X. "
             "Households consume some X; the firm installs the rest as capital for the "
             "next period. Capital wears out. Dividends depend on prior net profit and "
             "available cash. Investment is your policy choice; there is no borrowing "
             "or money creation.")
    st.write("In Firms and wages, households choose work, consumption and money holdings. "
             "One representative price-taking firm hires labor, produces X and distributes "
             "realized profit to its equal owners at the start of the next period. Wages must "
             "be funded from the firm’s cash; there is no credit, inventory or investment yet.")
    st.write("In Work and leisure, agents choose work to balance consumption, holding money "
             "and leisure. Productivity turns their work into goods. Work and prices are "
             "solved together. There are no firms, wages or planning for future periods yet.")
    st.write("In Production and consumption, agents receive fixed output each period, "
             "trade and consume all their goods. Money carries forward. Production is "
             "automatic; work choices and planning for the future are not modeled yet.")
    st.write(
        "Every economy keeps opening stocks, agent choices, prices, trades, "
        "closing stocks, and the accounting ledger available for inspection."
    )
    st.write(
        "In Good and money, agents value both the good and holding money. "
        "Purchases must be affordable. This is an explicit money-in-utility assumption, "
        "not a model of why money emerges."
    )
    st.write(
        "In the Money chapter, money settles trades but does not limit purchases. "
        "There is no banking, credit, production, or money creation. Each experiment "
        "starts with fresh money; closing balances do not carry into the next experiment."
    )
