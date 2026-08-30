import altair as alt
import streamlit as st

from econ_agent_sim.economy_0_3 import Economy03Config, run_economy_0_3
from econ_agent_sim.reporting import accounting_rows, transaction_rows

st.set_page_config(
    page_title="Economy 0.3 — Repeated Exchange",
    layout="centered",
    initial_sidebar_state="collapsed",
)

if "economy03_config" not in st.session_state:
    st.session_state.economy03_config = Economy03Config()

st.caption("ECONOMY 0.3")
st.title("Repeated pure exchange")
st.caption("10 agents · 2 goods · 4 periods · fresh exogenous endowments")

current = st.session_state.economy03_config

with st.container(horizontal=True, wrap=False, gap="small"):
    st.page_link("streamlit_app.py", label="← Home", width="content")
    st.page_link(
        "pages/3_Economy_0_2_Many_Agent_Exchange.py",
        label="← Economy 0.2",
        width="content",
    )
    with st.popover("Settings", icon=":material/tune:"):
        st.caption(
            "These controls change the tâtonnement path and iteration count, not the "
            "equilibrium itself. Endowments stay deterministic."
        )
        with st.form("economy03_inputs"):
            initial_price_x = st.number_input(
                "Initial trial pX",
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
            apply_scenario = st.form_submit_button("Apply and reset", width="stretch")

if apply_scenario:
    st.session_state.economy03_config = Economy03Config(
        period_populations=current.period_populations,
        initial_price_x=initial_price_x,
        adjustment_speed=adjustment_speed,
    )
    st.session_state.economy03_period_picker = 1
    st.session_state.economy03_view_picker = "Overview"
    st.rerun()

config = st.session_state.economy03_config
result = run_economy_0_3(config)

selected_period = st.pills(
    "Period",
    options=range(1, len(result.periods) + 1),
    default=1,
    required=True,
    key="economy03_period_picker",
    width="stretch",
)
period = result.periods[selected_period - 1]
final_step = period.steps[-1]

view = st.pills(
    "View",
    options=("Overview", "Market", "Agents", "Accounts", "Ledger"),
    default="Overview",
    required=True,
    key="economy03_view_picker",
    width="stretch",
)

rows = accounting_rows(period)
accounting_ok = all(abs(row["check"]) < 1e-12 for row in rows)
market_ok = final_step.market_error <= config.tolerance
start_price_x = period.steps[0].price_x
adjustments = period.steps[-1].iteration

with st.container(horizontal=True, wrap=False, gap="small"):
    st.metric(
        "Start pX",
        f"{start_price_x:.3f}",
        border=True,
        width=120,
    )
    st.metric(
        "Equilibrium pX",
        f"{period.prices['X']:.4f}",
        border=True,
        width=145,
    )
    st.metric(
        "Adjustments",
        adjustments,
        border=True,
        width=130,
    )
    st.metric(
        "Trades",
        len(period.transactions),
        border=True,
        width=110,
    )
    st.metric(
        "Market",
        "✓" if market_ok else "!",
        border=True,
        width=110,
    )
    st.metric(
        "Accounts",
        "✓" if accounting_ok else "!",
        border=True,
        width=120,
    )

if view == "Overview":
    st.subheader("Overview")
    st.line_chart(
        [
            {"period": item.period, "equilibrium pX": item.prices["X"]}
            for item in result.periods
        ],
        x="period",
        y="equilibrium pX",
        height=230,
    )

    st.caption(
        "This chart shows equilibrium prices across periods, so it does not change "
        "when only the initial trial price or lambda changes."
    )
    st.caption(
        f"Selected period price search: pX {start_price_x:.3f} → "
        f"{period.prices['X']:.4f} · λ {config.adjustment_speed:.1f} · "
        f"{adjustments} adjustments"
    )

    if period.period == 1:
        st.write(
            "The first period reproduces the Economy 0.2 benchmark. Later periods "
            "change only how Y endowments are distributed across the same agents."
        )
    else:
        previous_price = result.periods[period.period - 2].prices["X"]
        change = (period.prices["X"] / previous_price - 1.0) * 100.0
        direction = "rose" if change > 0 else "fell"
        st.write(
            f"pX {direction} {abs(change):.1f}% from period {period.period - 1}. "
            "Aggregate X and Y are unchanged; only the distribution of Y changed."
        )

    st.markdown(
        f"**Market clearing {'✓' if market_ok else '!' }** · "
        f"**Stock-flow balance {'✓' if accounting_ok else '!' }** · "
        f"**Final error {final_step.market_error:.1e}**"
    )

    if selected_period > 1:
        previous = result.periods[selected_period - 2]
        with st.expander("Inspect the exogenous period reset"):
            reset_rows = []
            for spec in period.population:
                previous_closing = previous.closing_stocks[spec.name]
                new_opening = period.opening_stocks[spec.name]
                reset_rows.append(
                    {
                        "agent": spec.name,
                        "previous X": round(previous_closing["X"], 4),
                        "new X": round(new_opening["X"], 4),
                        "previous Y": round(previous_closing["Y"], 4),
                        "new Y": round(new_opening["Y"], 4),
                    }
                )
            st.caption(
                "These are resets, not economic flows. Previous closing stocks are "
                "not carried into the new period."
            )
            st.dataframe(reset_rows, width="stretch", hide_index=True)

elif view == "Market":
    st.subheader("Market")
    total_x = sum(spec.x for spec in period.population)
    total_y = sum(spec.y for spec in period.population)

    with st.container(horizontal=True, wrap=False, gap="small"):
        st.metric("X supply", f"{total_x:.1f}", border=True, width=120)
        st.metric("Y supply", f"{total_y:.1f}", border=True, width=120)
        st.metric(
            "Analytic pX",
            f"{period.benchmark_price_x:.4f}",
            border=True,
            width=140,
        )
        st.metric(
            "λ",
            f"{config.adjustment_speed:.1f}",
            border=True,
            width=90,
        )
        st.metric(
            "Adjustments",
            adjustments,
            border=True,
            width=130,
        )

    st.caption(
        f"Within-period Walrasian price discovery starts at pX = {start_price_x:.3f}. "
        "A smaller λ makes each price move smaller, so convergence takes more "
        "adjustments; it does not change the equilibrium."
    )

    comparison_ceiling = max(2.0, start_price_x, period.benchmark_price_x) * 1.05
    comparison_adjustment_ceiling = max(400, adjustments)
    convergence_rows = []
    for step in period.steps:
        convergence_rows.extend(
            [
                {
                    "iteration": step.iteration,
                    "series": "Trial pX",
                    "pX": step.price_x,
                },
                {
                    "iteration": step.iteration,
                    "series": "Equilibrium benchmark",
                    "pX": period.benchmark_price_x,
                },
            ]
        )

    convergence_chart = (
        alt.Chart(alt.Data(values=convergence_rows))
        .mark_line(point=True)
        .encode(
            x=alt.X(
                "iteration:Q",
                title="Adjustment",
                axis=alt.Axis(tickMinStep=1),
                scale=alt.Scale(domain=[0, comparison_adjustment_ceiling]),
            ),
            y=alt.Y(
                "pX:Q",
                title="pX",
                scale=alt.Scale(domain=[0.0, comparison_ceiling]),
            ),
            color=alt.Color("series:N", title=None),
            tooltip=[
                alt.Tooltip("iteration:Q", title="Adjustment", format=".0f"),
                alt.Tooltip("series:N", title="Series"),
                alt.Tooltip("pX:Q", title="pX", format=".6f"),
            ],
        )
        .properties(height=240)
    )
    st.altair_chart(convergence_chart, width="stretch")
    st.caption(
        "The price scale stays comparable for ordinary starting prices, and the "
        "adjustment axis stays at 0–400 for ordinary runs. This prevents automatic "
        "rescaling from hiding the effects of either Initial pX or λ."
    )

    st.markdown("**Final clearing check**")
    st.dataframe(
        [
            {
                "good": "X",
                "supply": round(final_step.supply_x, 6),
                "demand": round(final_step.demand_x, 6),
                "excess": round(final_step.excess_demand_x, 10),
            },
            {
                "good": "Y",
                "supply": round(final_step.supply_y, 6),
                "demand": round(final_step.demand_y, 6),
                "excess": round(final_step.excess_demand_y, 10),
            },
        ],
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

elif view == "Agents":
    st.subheader("Agents")
    st.caption("Compact view: opening stocks and the trade each agent wants to make.")

    compact_rows = []
    full_rows = []
    for spec in period.population:
        desired = period.desired_bundles[spec.name]
        compact_rows.append(
            {
                "agent": spec.name,
                "X": round(spec.x, 3),
                "Y": round(spec.y, 3),
                "net X": round(desired["X"] - spec.x, 4),
                "net Y": round(desired["Y"] - spec.y, 4),
            }
        )
        full_rows.append(
            {
                "agent": spec.name,
                "alpha": spec.alpha,
                "wealth": period.wealths[spec.name],
                "opening X": spec.x,
                "opening Y": spec.y,
                "desired X": desired["X"],
                "desired Y": desired["Y"],
                "net X": desired["X"] - spec.x,
                "net Y": desired["Y"] - spec.y,
            }
        )

    st.dataframe(compact_rows, width="stretch", hide_index=True)
    with st.expander("Full agent decision table"):
        st.dataframe(full_rows, width="stretch", hide_index=True)

elif view == "Accounts":
    st.subheader("Accounts")
    balanced_rows = sum(abs(row["check"]) < 1e-12 for row in rows)
    opening_x = sum(item["X"] for item in period.opening_stocks.values())
    closing_x = sum(item["X"] for item in period.closing_stocks.values())
    opening_y = sum(item["Y"] for item in period.opening_stocks.values())
    closing_y = sum(item["Y"] for item in period.closing_stocks.values())

    st.markdown(
        f"**{balanced_rows}/{len(rows)} identities balanced ✓** · "
        f"**X conserved {'✓' if abs(opening_x - closing_x) < 1e-12 else '!'}** · "
        f"**Y conserved {'✓' if abs(opening_y - closing_y) < 1e-12 else '!'}**"
    )

    compact_accounting = [
        {
            "agent": row["agent"],
            "good": row["good"],
            "open": round(row["opening_stock"], 4),
            "flow": round(row["net_flow_so_far"], 4),
            "close": round(row["current_stock"], 4),
        }
        for row in rows
    ]
    st.dataframe(compact_accounting, width="stretch", hide_index=True)

    with st.expander("Full stock-flow audit"):
        st.caption("Identity: closing stock = opening stock + ledgered net flow.")
        st.dataframe(rows, width="stretch", hide_index=True)

else:
    st.subheader("Ledger")
    transactions = transaction_rows(period)
    transfer_x = sum(
        transaction["quantity"]
        for transaction in transactions
        if transaction["good"] == "X"
    )
    transfer_y = sum(
        transaction["quantity"]
        for transaction in transactions
        if transaction["good"] == "Y"
    )

    with st.container(horizontal=True, wrap=False, gap="small"):
        st.metric("Entries", len(transactions), border=True, width=110)
        st.metric("X moved", f"{transfer_x:.3f}", border=True, width=120)
        st.metric("Y moved", f"{transfer_y:.3f}", border=True, width=120)

    compact_ledger = [
        {
            "#": transaction["transaction_id"],
            "good": transaction["good"],
            "from → to": (
                f"{transaction['sender']} → {transaction['receiver']}"
            ),
            "qty": round(transaction["quantity"], 5),
        }
        for transaction in transactions
    ]
    st.dataframe(compact_ledger, width="stretch", hide_index=True)

    with st.expander("Full period ledger"):
        st.dataframe(transactions, width="stretch", hide_index=True)

    final_rows = []
    full_final_rows = []
    for spec in period.population:
        closing = period.closing_stocks[spec.name]
        target = period.desired_bundles[spec.name]
        final_rows.append(
            {
                "agent": spec.name,
                "X": round(closing["X"], 4),
                "Y": round(closing["Y"], 4),
            }
        )
        full_final_rows.append(
            {
                "agent": spec.name,
                "closing X": closing["X"],
                "target X": target["X"],
                "X error": closing["X"] - target["X"],
                "closing Y": closing["Y"],
                "target Y": target["Y"],
                "Y error": closing["Y"] - target["Y"],
            }
        )

    st.markdown("**Final allocation**")
    st.dataframe(final_rows, width="stretch", hide_index=True)
    with st.expander("Full allocation audit"):
        st.dataframe(full_final_rows, width="stretch", hide_index=True)

    with st.expander("Full multi-period ledger"):
        st.caption("Transaction IDs remain unique across all four periods.")
        st.dataframe(transaction_rows(result), width="stretch", hide_index=True)

with st.expander("Model boundary"):
    st.write(
        "Economy 0.3 adds repeated periods and ledger time stamps only. There is no "
        "carry-over inventory, consumption, saving, production, money, credit, "
        "banking, government, or randomness."
    )
    st.caption(
        "Each period starts from a fresh exogenous endowment schedule, so time is "
        "visible without intertemporal wealth accumulation."
    )