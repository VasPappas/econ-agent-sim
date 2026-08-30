import altair as alt
import streamlit as st

from econ_agent_sim.economy_0_3 import (
    Economy03Config,
    baseline_period_populations,
    redistribute_y,
    run_economy_0_3,
)
from econ_agent_sim.reporting import accounting_rows, transaction_rows

UI_SCHEMA_VERSION = 2

st.set_page_config(
    page_title="Economy 0.3 — Redistribution Experiment",
    layout="centered",
    initial_sidebar_state="collapsed",
)

if st.session_state.get("economy03_ui_schema") != UI_SCHEMA_VERSION:
    st.session_state.economy03_ui_schema = UI_SCHEMA_VERSION
    st.session_state.economy03_period_populations = baseline_period_populations()
    st.session_state.economy03_initial_price_x = 0.5
    st.session_state.economy03_adjustment_speed = 1.0
    st.session_state.economy03_period_picker = "Baseline"
    st.session_state.economy03_view_picker = "Overview"

st.caption("ECONOMY 0.3")
st.title("Redistribution experiment")
st.caption("Same economy · same totals · you decide how Y is redistributed")

with st.container(horizontal=True, wrap=False, gap="small"):
    st.page_link("streamlit_app.py", label="← Home", width="content")
    st.page_link(
        "pages/3_Economy_0_2_Many_Agent_Exchange.py",
        label="← Economy 0.2",
        width="content",
    )
    with st.popover("Settings", icon=":material/tune:"):
        st.caption(
            "Initial pX and λ change the numerical price-search path, not the "
            "underlying equilibrium."
        )
        with st.form("economy03_settings"):
            initial_price_x = st.number_input(
                "Initial trial pX",
                min_value=0.01,
                value=float(st.session_state.economy03_initial_price_x),
                step=0.1,
            )
            adjustment_speed = st.slider(
                "Adjustment speed (lambda)",
                min_value=0.1,
                max_value=1.0,
                value=float(st.session_state.economy03_adjustment_speed),
                step=0.1,
            )
            apply_settings = st.form_submit_button("Apply", width="stretch")
        reset_experiment = st.button(
            "Reset to baseline",
            key="economy03_reset_experiment",
            width="stretch",
        )

if apply_settings:
    st.session_state.economy03_initial_price_x = initial_price_x
    st.session_state.economy03_adjustment_speed = adjustment_speed
    st.rerun()

if reset_experiment:
    st.session_state.economy03_period_populations = baseline_period_populations()
    st.session_state.economy03_period_picker = "Baseline"
    st.session_state.economy03_view_picker = "Overview"
    st.rerun()

period_populations = st.session_state.economy03_period_populations
latest_population = period_populations[-1]
agent_names = [agent.name for agent in latest_population]

with st.expander("Add a redistribution", expanded=len(period_populations) == 1):
    st.caption(
        "Create the next period by moving Y from one agent to another. Total Y stays "
        "fixed, so this is redistribution rather than creation or destruction."
    )
    sender_name = st.selectbox("Move Y from", agent_names, key="economy03_sender")
    receiver_name = st.selectbox(
        "Move Y to",
        agent_names,
        index=1,
        key="economy03_receiver",
    )
    sender = next(agent for agent in latest_population if agent.name == sender_name)
    amount = st.number_input(
        "Amount of Y",
        min_value=0.01,
        value=0.1,
        step=0.1,
        key="economy03_redistribution_amount",
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
    st.session_state.economy03_period_populations = (*period_populations, new_population)
    st.session_state.economy03_period_picker = (
        f"Redistribution {len(period_populations)}"
    )
    st.session_state.economy03_view_picker = "Overview"
    st.rerun()

if len(period_populations) > 1 and st.button(
    "Remove last redistribution", width="stretch"
):
    st.session_state.economy03_period_populations = period_populations[:-1]
    st.session_state.economy03_period_picker = (
        "Baseline"
        if len(period_populations) == 2
        else f"Redistribution {len(period_populations) - 2}"
    )
    st.rerun()

config = Economy03Config(
    period_populations=st.session_state.economy03_period_populations,
    initial_price_x=float(st.session_state.economy03_initial_price_x),
    adjustment_speed=float(st.session_state.economy03_adjustment_speed),
)
result = run_economy_0_3(config)

step_labels = ["Baseline"] + [
    f"Redistribution {index}" for index in range(1, len(result.periods))
]
if st.session_state.get("economy03_period_picker") not in step_labels:
    st.session_state.economy03_period_picker = step_labels[-1]

selected_label = st.pills(
    "Experiment step",
    options=step_labels,
    default="Baseline",
    required=True,
    key="economy03_period_picker",
    width="stretch",
)
selected_index = step_labels.index(selected_label)
period = result.periods[selected_index]
final_step = period.steps[-1]

view = st.pills(
    "View",
    options=("Overview", "Market", "Audit"),
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
previous_period = result.periods[selected_index - 1] if selected_index > 0 else None
previous_price = previous_period.prices["X"] if previous_period else None
price_change = (
    (period.prices["X"] / previous_price - 1.0) * 100.0
    if previous_price is not None
    else None
)

with st.container(horizontal=True, wrap=False, gap="small"):
    st.metric("Step", selected_label, border=True, width=160)
    st.metric("pX", f"{period.prices['X']:.4f}", border=True, width=115)
    st.metric(
        "Δ pX",
        "—" if price_change is None else f"{price_change:+.1f}%",
        border=True,
        width=115,
    )
    st.metric("Market", "✓" if market_ok else "!", border=True, width=105)
    st.metric("Accounts", "✓" if accounting_ok else "!", border=True, width=115)

if view == "Overview":
    st.subheader("Overview")
    price_history = [
        {"step": index, "equilibrium pX": item.prices["X"]}
        for index, item in enumerate(result.periods)
    ]
    if len(price_history) > 1:
        st.line_chart(price_history, x="step", y="equilibrium pX", height=210)

    current_pressure = sum(agent.alpha * agent.y for agent in period.population)
    if previous_period is None:
        st.write(
            "**Baseline:** this is the Economy 0.2 endowment distribution. Nothing "
            "changes through time until you add a redistribution."
        )
        st.markdown(
            f"**Equilibrium pX {period.prices['X']:.4f}** · "
            f"**X-demand pressure {current_pressure:.3f}**"
        )
        if len(result.periods) == 1:
            st.info(
                "Try moving some Y between two agents above. The next period will "
                "show whether the equilibrium relative price changes."
            )
    else:
        previous_pressure = sum(
            agent.alpha * agent.y for agent in previous_period.population
        )
        pressure_change = current_pressure - previous_pressure
        if pressure_change > 1e-12:
            pressure_direction = "increased"
        elif pressure_change < -1e-12:
            pressure_direction = "decreased"
        else:
            pressure_direction = "left unchanged"

        if price_change > 1e-12:
            price_direction = "rose"
        elif price_change < -1e-12:
            price_direction = "fell"
        else:
            price_direction = "was unchanged"

        st.markdown(
            f"**pX {previous_price:.4f} → {period.prices['X']:.4f}** "
            f"({price_change:+.1f}%)"
        )
        st.write(
            f"The redistribution {pressure_direction} the Y-weighted demand pressure "
            f"for X from {previous_pressure:.3f} to {current_pressure:.3f}. "
            f"Equilibrium pX {price_direction}."
        )
        previous_by_name = {agent.name: agent for agent in previous_period.population}
        changed_agents = []
        for agent in period.population:
            before = previous_by_name[agent.name]
            delta_y = agent.y - before.y
            if abs(delta_y) > 1e-12:
                changed_agents.append(
                    {
                        "agent": agent.name,
                        "alpha": agent.alpha,
                        "Y before": round(before.y, 4),
                        "Y after": round(agent.y, 4),
                        "ΔY": round(delta_y, 4),
                    }
                )
        st.dataframe(changed_agents, width="stretch", hide_index=True)
        st.caption(
            "Higher α means a stronger preference for X. Moving Y toward high-α "
            "agents tends to raise demand pressure on X; moving it away tends to "
            "lower that pressure."
        )

    st.markdown(
        f"**Market clearing {'✓' if market_ok else '!'}** · "
        f"**Stock-flow balance {'✓' if accounting_ok else '!'}** · "
        f"**Final error {final_step.market_error:.1e}**"
    )

elif view == "Market":
    st.subheader("Market")
    total_x = sum(spec.x for spec in period.population)
    total_y = sum(spec.y for spec in period.population)
    with st.container(horizontal=True, wrap=False, gap="small"):
        st.metric("Start pX", f"{start_price_x:.3f}", border=True, width=120)
        st.metric("Equilibrium", f"{period.prices['X']:.4f}", border=True, width=130)
        st.metric("λ", f"{config.adjustment_speed:.1f}", border=True, width=85)
        st.metric("Adjustments", adjustments, border=True, width=125)

    comparison_ceiling = max(2.0, start_price_x, period.benchmark_price_x) * 1.05
    comparison_iterations = max(400, adjustments) * 1.05
    convergence_rows = []
    for step in period.steps:
        convergence_rows.extend(
            [
                {"iteration": step.iteration, "series": "Trial pX", "pX": step.price_x},
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
                scale=alt.Scale(domain=[0.0, comparison_iterations]),
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
        .properties(height=235)
    )
    st.altair_chart(convergence_chart, width="stretch")
    st.caption(
        "Initial pX changes where the search starts. λ changes how quickly it moves. "
        "Neither changes the equilibrium implied by this period's endowments and "
        "preferences."
    )
    st.markdown("**Final clearing check**")
    st.dataframe(
        [
            {
                "good": "X",
                "supply": round(total_x, 6),
                "demand": round(final_step.demand_x, 6),
                "excess": round(final_step.excess_demand_x, 10),
            },
            {
                "good": "Y",
                "supply": round(total_y, 6),
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

else:
    st.subheader("Audit")
    st.caption("Full traceability is still here, but it is no longer the default view.")
    with st.expander("Agent decisions"):
        decision_rows = []
        for spec in period.population:
            desired = period.desired_bundles[spec.name]
            decision_rows.append(
                {
                    "agent": spec.name,
                    "alpha": spec.alpha,
                    "opening X": spec.x,
                    "opening Y": spec.y,
                    "desired X": desired["X"],
                    "desired Y": desired["Y"],
                    "net X": desired["X"] - spec.x,
                    "net Y": desired["Y"] - spec.y,
                }
            )
        st.dataframe(decision_rows, width="stretch", hide_index=True)
    with st.expander("Stock-flow accounts"):
        st.caption("Identity: closing stock = opening stock + ledgered net flow.")
        st.dataframe(rows, width="stretch", hide_index=True)
    with st.expander("Period settlement ledger"):
        st.dataframe(transaction_rows(period), width="stretch", hide_index=True)

    if previous_period is not None:
        with st.expander("Exogenous period reset"):
            reset_rows = []
            for spec in period.population:
                previous_closing = previous_period.closing_stocks[spec.name]
                new_opening = period.opening_stocks[spec.name]
                reset_rows.append(
                    {
                        "agent": spec.name,
                        "previous close X": round(previous_closing["X"], 4),
                        "new open X": round(new_opening["X"], 4),
                        "previous close Y": round(previous_closing["Y"], 4),
                        "new open Y": round(new_opening["Y"], 4),
                    }
                )
            st.caption(
                "The user-defined redistribution sets the next period's exogenous "
                "opening endowments. It is not a market transaction."
            )
            st.dataframe(reset_rows, width="stretch", hide_index=True)

    if len(result.periods) > 1:
        with st.expander("Full multi-period ledger"):
            st.caption("Transaction IDs remain unique across the entire experiment.")
            st.dataframe(transaction_rows(result), width="stretch", hide_index=True)

with st.expander("Model boundary"):
    st.write(
        "Economy 0.3 adds repeated periods with user-chosen exogenous redistribution. "
        "There is still no carry-over inventory, consumption, saving, production, "
        "money, credit, banking, government, or randomness."
    )
    st.caption(
        "Each added period starts from the latest user-defined endowment schedule, "
        "not from the previous period's market closing stocks."
    )
