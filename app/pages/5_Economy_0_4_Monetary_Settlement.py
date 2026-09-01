from dataclasses import asdict

import streamlit as st

from econ_agent_sim.economy_0_3 import baseline_period_populations, redistribute_y
from econ_agent_sim.economy_0_4 import ASSETS, MONEY, Economy04Config, run_economy_0_4

UI_SCHEMA_VERSION = 1


def apply_settings() -> None:
    st.session_state.economy04_opening_money = float(
        st.session_state.economy04_opening_money_input
    )
    st.session_state.economy04_initial_price_x = float(
        st.session_state.economy04_initial_price_input
    )
    st.session_state.economy04_adjustment_speed = float(
        st.session_state.economy04_adjustment_speed_input
    )
    st.session_state.economy04_settings_open = False


def accounting_rows(period) -> list[dict[str, float | str]]:
    rows = []
    for name, opening in period.opening_stocks.items():
        for asset in ASSETS:
            flow = period.flows[name][asset]
            closing = period.closing_stocks[name][asset]
            rows.append(
                {
                    "agent": name,
                    "asset": asset,
                    "opening": opening[asset],
                    "net flow": flow,
                    "closing": closing,
                    "check": opening[asset] + flow - closing,
                }
            )
    return rows


st.set_page_config(
    page_title="Economy 0.4 — Monetary Settlement",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    @media (max-width: 768px) {
        .st-key-economy04_mobile_nav {
            position: fixed;
            left: max(1rem, env(safe-area-inset-left));
            right: max(1rem, env(safe-area-inset-right));
            bottom: calc(5.25rem + env(safe-area-inset-bottom));
            z-index: 1000000;
            padding: 0.4rem;
            border: 1px solid rgba(128, 128, 128, 0.28);
            border-radius: 1rem;
            background: var(--background-color);
            background: color-mix(in srgb, var(--background-color) 94%, transparent);
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.14);
            -webkit-backdrop-filter: blur(14px);
            backdrop-filter: blur(14px);
        }

        .st-key-economy04_mobile_nav [data-testid="stPills"] {
            margin: 0;
        }

        [data-testid="stAppViewContainer"] .main .block-container {
            padding-bottom: calc(12rem + env(safe-area-inset-bottom));
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

if st.session_state.get("economy04_ui_schema") != UI_SCHEMA_VERSION:
    st.session_state.economy04_ui_schema = UI_SCHEMA_VERSION
    st.session_state.economy04_period_populations = baseline_period_populations()
    st.session_state.economy04_opening_money = 10.0
    st.session_state.economy04_initial_price_x = 0.5
    st.session_state.economy04_adjustment_speed = 1.0
    st.session_state.economy04_opening_money_input = 10.0
    st.session_state.economy04_initial_price_input = 0.5
    st.session_state.economy04_adjustment_speed_input = 1.0
    st.session_state.economy04_period_picker = "Baseline"
    st.session_state.economy04_view_picker = "Overview"
    st.session_state.economy04_settings_open = False

st.caption("ECONOMY 0.4")
st.title("Money settles the trade")
st.caption("Same real exchange economy · every goods transfer now has a money payment")

with st.container(horizontal=True, wrap=False, gap="small"):
    st.page_link("streamlit_app.py", label="← Home", width="content")
    st.page_link(
        "pages/4_Economy_0_3_Repeated_Exchange.py",
        label="← Economy 0.3",
        width="content",
    )

settings_placeholder = st.empty()
settings_panel = settings_placeholder.expander(
    "Settings",
    key="economy04_settings_open",
    on_change="rerun",
)
with settings_panel:
    st.caption(
        "Opening money changes the balance sheet only. Initial pX and λ change the "
        "numerical search path. None of these settings changes preferences."
    )
    with st.form("economy04_settings"):
        st.number_input(
            "Opening money per agent",
            min_value=0.1,
            step=1.0,
            format="%.2f",
            key="economy04_opening_money_input",
        )
        st.number_input(
            "Initial trial pX",
            min_value=0.01,
            step=0.1,
            key="economy04_initial_price_input",
        )
        st.number_input(
            "Adjustment speed (lambda)",
            min_value=0.1,
            max_value=1.0,
            step=0.1,
            format="%.1f",
            key="economy04_adjustment_speed_input",
        )
        st.form_submit_button(
            "Apply and close",
            width="stretch",
            on_click=apply_settings,
        )
    if st.button(
        "Reset experiment to baseline",
        key="economy04_reset_experiment",
        width="stretch",
    ):
        st.session_state.economy04_period_populations = baseline_period_populations()
        st.session_state.economy04_period_picker = "Baseline"
        st.session_state.economy04_view_picker = "Overview"
        st.session_state.economy04_settings_open = False
        st.rerun()

period_populations = st.session_state.economy04_period_populations
latest_population = period_populations[-1]
agent_names = [agent.name for agent in latest_population]

redistribution_placeholder = st.empty()
with redistribution_placeholder.expander(
    "Add a redistribution", expanded=len(period_populations) == 1
):
    st.caption(
        "As in Economy 0.3, create the next period by moving Y between agents. "
        "Money settlement is then applied to the new market outcome."
    )
    sender_name = st.selectbox("Move Y from", agent_names, key="economy04_sender")
    receiver_name = st.selectbox(
        "Move Y to",
        agent_names,
        index=1,
        key="economy04_receiver",
    )
    sender = next(agent for agent in latest_population if agent.name == sender_name)
    amount = st.number_input(
        "Amount of Y",
        min_value=0.01,
        value=0.1,
        step=0.1,
        key="economy04_redistribution_amount",
    )
    st.caption(f"{sender_name} currently has {sender.y:.2f} Y in the latest period.")
    invalid_pair = sender_name == receiver_name
    insufficient_y = amount > sender.y
    add_redistribution = st.button(
        "Add as next period",
        type="primary",
        disabled=invalid_pair or insufficient_y or sender.y < 0.01,
        width="stretch",
    )
    if invalid_pair:
        st.caption("Choose two different agents.")
    if insufficient_y:
        st.caption("The redistribution cannot exceed the sender's current Y.")

if add_redistribution:
    new_population = redistribute_y(
        latest_population,
        sender_name=sender_name,
        receiver_name=receiver_name,
        amount=float(amount),
    )
    st.session_state.economy04_period_populations = (*period_populations, new_population)
    st.session_state.economy04_period_picker = (
        f"Redistribution {len(period_populations)}"
    )
    st.session_state.economy04_view_picker = "Overview"
    st.rerun()

remove_redistribution_placeholder = st.empty()
if len(period_populations) > 1 and remove_redistribution_placeholder.button(
    "Remove last redistribution", width="stretch"
):
    st.session_state.economy04_period_populations = period_populations[:-1]
    st.session_state.economy04_period_picker = (
        "Baseline"
        if len(period_populations) == 2
        else f"Redistribution {len(period_populations) - 2}"
    )
    st.rerun()

config = Economy04Config(
    period_populations=st.session_state.economy04_period_populations,
    opening_money_per_agent=float(st.session_state.economy04_opening_money),
    initial_price_x=float(st.session_state.economy04_initial_price_x),
    adjustment_speed=float(st.session_state.economy04_adjustment_speed),
)
result = run_economy_0_4(config)

step_labels = ["Baseline"] + [
    f"Redistribution {index}" for index in range(1, len(result.periods))
]
if st.session_state.get("economy04_period_picker") not in step_labels:
    st.session_state.economy04_period_picker = step_labels[-1]

if len(step_labels) > 1:
    selected_label = st.pills(
        "Experiment step",
        options=step_labels,
        default="Baseline",
        required=True,
        key="economy04_period_picker",
        width="stretch",
    )
    selected_index = step_labels.index(selected_label)
else:
    selected_label = "Baseline"
    selected_index = 0

period = result.periods[selected_index]
final_step = period.steps[-1]

with st.container(key="economy04_mobile_nav"):
    view = st.pills(
        "View",
        options=("Overview", "Settlement", "Audit"),
        default="Overview",
        required=True,
        key="economy04_view_picker",
        width="stretch",
        label_visibility="collapsed",
    )

if view != "Overview":
    settings_placeholder.empty()
    redistribution_placeholder.empty()
    remove_redistribution_placeholder.empty()

rows = accounting_rows(period)
accounting_ok = all(abs(row["check"]) < 1e-10 for row in rows)
market_ok = final_step.market_error <= config.tolerance
opening_money_total = sum(row[MONEY] for row in period.opening_stocks.values())
closing_money_total = sum(row[MONEY] for row in period.closing_stocks.values())
money_conserved = abs(opening_money_total - closing_money_total) < 1e-10
previous_period = result.periods[selected_index - 1] if selected_index > 0 else None
previous_price = previous_period.prices["X"] if previous_period else None
price_change = (
    (period.prices["X"] / previous_price - 1.0) * 100.0
    if previous_price is not None
    else None
)

if view == "Overview":
    with st.container(border=True):
        st.caption("SELECTED RESULT")
        if price_change is None:
            st.markdown(f"### pX {period.prices['X']:.4f} money per X")
            result_change = "Baseline"
        else:
            st.markdown(
                f"### pX {period.prices['X']:.4f} money per X · {price_change:+.1f}%"
            )
            result_change = f"vs {previous_price:.4f} in the previous step"
        st.caption(
            f"pY 1.0000 · {len(period.population)} agents · {result_change} · "
            f"Market cleared {'✓' if market_ok else '!'} · "
            f"Money conserved {'✓' if money_conserved else '!'} · "
            f"Accounts balanced {'✓' if accounting_ok else '!'}"
        )

    st.subheader("What changed in 0.4?")
    st.write(
        "The real X/Y market is unchanged. The new mechanism is settlement: whenever "
        "a buyer receives a good, the buyer sends money back to the seller at the "
        "discovered market price."
    )

    if period.trades:
        trade = period.trades[0]
        with st.container(border=True):
            st.caption(f"EXAMPLE · TRADE {trade.trade_id}")
            st.markdown(
                f"**{trade.seller} → {trade.buyer}: {trade.quantity:.4f} {trade.good}**"
            )
            st.markdown(
                f"**{trade.buyer} → {trade.seller}: {trade.payment:.4f} Money**"
            )
            st.caption(
                f"Price: {trade.unit_price:.4f} money per {trade.good}. The two legs "
                "share one trade ID."
            )

    st.info(
        "Money does not enter utility or restrict purchases yet. Change the opening "
        "money balance in Settings: the real equilibrium price and allocation stay "
        "the same in Economy 0.4."
    )

    with st.expander("Model boundary"):
        st.write(
            "Money is a settlement asset only. Agents still optimize Cobb-Douglas "
            "utility over X and Y, and their real demand budget is the market value "
            "of their X/Y endowments. Money does not create extra demand."
        )
        st.caption(
            "Payment legs are cleared as one settlement batch, so there is no "
            "cash-in-advance or intraday liquidity constraint yet. There are also no "
            "banks, loans, interest, production, government, or money creation. Each "
            "exogenous period starts with the configured opening money balance."
        )

elif view == "Settlement":
    st.subheader("Settlement")
    with st.container(border=True):
        st.markdown(
            f"**Price search:** pX {period.steps[0].price_x:.3f} → "
            f"{period.prices['X']:.4f}"
        )
        st.caption(
            f"λ {config.adjustment_speed:.1f} · {period.steps[-1].iteration} "
            f"adjustments · final market error {final_step.market_error:.1e}"
        )

    st.markdown("**Monetary trades**")
    st.caption(
        "Each row is one goods trade. In the audit ledger it appears as two legs: "
        "the good moves to the buyer and Money moves back to the seller."
    )
    st.dataframe(
        [
            {
                "trade": trade.trade_id,
                "good": trade.good,
                "quantity": round(trade.quantity, 6),
                "price": round(trade.unit_price, 6),
                "seller": trade.seller,
                "buyer": trade.buyer,
                "money payment": round(trade.payment, 6),
            }
            for trade in period.trades
        ],
        width="stretch",
        hide_index=True,
    )
    st.caption(
        f"{len(period.trades)} trades · {len(period.transactions)} ledger legs · "
        f"gross money payments {period.gross_money_payments:.4f}"
    )

    total_x = sum(spec.x for spec in period.population)
    total_y = sum(spec.y for spec in period.population)
    st.markdown("**Final clearing check**")
    st.dataframe(
        [
            {
                "good": "X",
                "supply": round(total_x, 6),
                "demand": round(final_step.demand_x, 6),
                "excess": round(final_step.excess_demand_x, 8),
            },
            {
                "good": "Y",
                "supply": round(total_y, 6),
                "demand": round(final_step.demand_y, 6),
                "excess": round(final_step.excess_demand_y, 8),
            },
        ],
        width="stretch",
        hide_index=True,
    )

else:
    st.subheader("Audit")
    st.caption("Every real transfer and every money payment remains inspectable.")

    with st.expander("Agent decisions"):
        st.dataframe(
            [
                {
                    "agent": spec.name,
                    "alpha": spec.alpha,
                    "opening X": spec.x,
                    "opening Y": spec.y,
                    "opening Money": period.opening_stocks[spec.name][MONEY],
                    "desired X": period.desired_bundles[spec.name]["X"],
                    "desired Y": period.desired_bundles[spec.name]["Y"],
                    "closing Money": period.closing_stocks[spec.name][MONEY],
                }
                for spec in period.population
            ],
            width="stretch",
            hide_index=True,
        )
        st.caption(
            "Opening Money is shown on the balance sheet but is deliberately excluded "
            "from Cobb-Douglas demand in Economy 0.4."
        )

    with st.expander("Stock-flow accounts"):
        st.caption("Identity: closing stock = opening stock + ledgered net flow.")
        st.dataframe(rows, width="stretch", hide_index=True)

    with st.expander("Settlement ledger"):
        st.dataframe(
            [asdict(transaction) for transaction in period.transactions],
            width="stretch",
            hide_index=True,
        )

    with st.expander("Price-discovery iterations"):
        st.dataframe(
            [
                {
                    "iteration": step.iteration,
                    "pX": step.price_x,
                    "X excess": step.excess_demand_x,
                    "Y excess": step.excess_demand_y,
                    "market error": step.market_error,
                    "next pX": step.next_price_x,
                }
                for step in period.steps
            ],
            width="stretch",
            hide_index=True,
        )

    if len(result.periods) > 1:
        with st.expander("Full multi-period monetary ledger"):
            st.caption("Transaction and trade IDs remain unique across the experiment.")
            st.dataframe(
                [asdict(transaction) for transaction in result.transactions],
                width="stretch",
                hide_index=True,
            )
