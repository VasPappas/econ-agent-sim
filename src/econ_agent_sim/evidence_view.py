"""Detailed accounting, available beneath the experiment results."""

from dataclasses import asdict

import streamlit as st

from econ_agent_sim.economy_0_4 import MONEY


def render_evidence(result, selected_index, rows):
    period = result.periods[selected_index]
    config = result.config
    final_step = period.steps[-1]
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

