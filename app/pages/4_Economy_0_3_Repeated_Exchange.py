from dataclasses import replace

import altair as alt
import streamlit as st

from econ_agent_sim.economy_0_2 import canonical_population
from econ_agent_sim.economy_0_3 import Economy03Config, run_economy_0_3
from econ_agent_sim.reporting import accounting_rows, transaction_rows

UI_SCHEMA_VERSION = 5
DEFAULT_PAIR_ALPHAS = (0.20, 0.30, 0.40, 0.35, 0.45, 0.20, 0.30, 0.40, 0.35, 0.45)


def baseline_period_populations(
    agent_count: int = 10,
    pair_alphas: tuple[float, ...] | None = None,
):
    """Build a balanced UI population from complete mirrored pairs."""

    if agent_count < 2 or agent_count > 20 or agent_count % 2:
        raise ValueError("agent count must be an even number from 2 through 20")

    templates = canonical_population()
    alphas = pair_alphas or DEFAULT_PAIR_ALPHAS[: agent_count // 2]
    if len(alphas) != agent_count // 2:
        raise ValueError("one alpha is required for each mirrored pair")

    population = []
    for index in range(agent_count):
        template = templates[index % len(templates)]
        pair_alpha = float(alphas[index // 2])
        if not 0.0 < pair_alpha < 1.0:
            raise ValueError("pair alpha must lie strictly between 0 and 1")
        alpha = pair_alpha if index % 2 == 0 else 1.0 - pair_alpha
        population.append(
            replace(
                template,
                name=f"Agent {index + 1}",
                alpha=alpha,
            )
        )

    return (tuple(population),)


def redistribute_y(population, *, sender_name: str, receiver_name: str, amount: float):
    """Move Y between agents while leaving identities, X, and preferences unchanged."""

    if amount <= 0:
        raise ValueError("redistribution amount must be strictly positive")
    if sender_name == receiver_name:
        raise ValueError("sender and receiver must be different agents")

    sender = next((agent for agent in population if agent.name == sender_name), None)
    if sender is None:
        raise ValueError(f"unknown sender: {sender_name}")
    if not any(agent.name == receiver_name for agent in population):
        raise ValueError(f"unknown receiver: {receiver_name}")
    if amount > sender.y + 1e-12:
        raise ValueError(f"{sender_name} only has {sender.y:.6g} units of Y available")

    return tuple(
        replace(
            agent,
            y=(
                agent.y - amount
                if agent.name == sender_name
                else agent.y + amount
                if agent.name == receiver_name
                else agent.y
            ),
        )
        for agent in population
    )


def apply_settings() -> None:
    """Apply settings and reset redistributions when population choices change."""

    new_agent_count = int(st.session_state.economy03_agent_count_input)
    new_pair_alphas = tuple(
        float(st.session_state[f"economy03_pair_alpha_{pair_index}_input"])
        for pair_index in range(new_agent_count // 2)
    )
    population_changed = (
        new_agent_count != st.session_state.economy03_agent_count
        or new_pair_alphas != tuple(st.session_state.economy03_pair_alphas)
    )

    st.session_state.economy03_agent_count = new_agent_count
    st.session_state.economy03_pair_alphas = new_pair_alphas
    st.session_state.economy03_initial_price_x = float(
        st.session_state.economy03_initial_price_input
    )
    st.session_state.economy03_adjustment_speed = float(
        st.session_state.economy03_adjustment_speed_input
    )

    if population_changed:
        st.session_state.economy03_period_populations = baseline_period_populations(
            new_agent_count,
            new_pair_alphas,
        )
        st.session_state.economy03_period_picker = "Baseline"
        st.session_state.economy03_view_picker = "Overview"
        for key in (
            "economy03_sender",
            "economy03_receiver",
            "economy03_redistribution_amount",
        ):
            st.session_state.pop(key, None)

    st.session_state.economy03_settings_open = False


st.set_page_config(
    page_title="Economy 0.3 — Redistribution Experiment",
    layout="centered",
    initial_sidebar_state="collapsed",
)

if st.session_state.get("economy03_ui_schema") != UI_SCHEMA_VERSION:
    st.session_state.economy03_ui_schema = UI_SCHEMA_VERSION
    st.session_state.economy03_agent_count = 10
    st.session_state.economy03_agent_count_input = 10
    st.session_state.economy03_pair_alphas = DEFAULT_PAIR_ALPHAS[:5]
    for pair_index, pair_alpha in enumerate(DEFAULT_PAIR_ALPHAS):
        st.session_state[f"economy03_pair_alpha_{pair_index}_input"] = pair_alpha
    st.session_state.economy03_period_populations = baseline_period_populations(
        10,
        st.session_state.economy03_pair_alphas,
    )
    st.session_state.economy03_initial_price_x = 0.5
    st.session_state.economy03_adjustment_speed = 1.0
    st.session_state.economy03_period_picker = "Baseline"
    st.session_state.economy03_view_picker = "Overview"
    st.session_state.economy03_settings_open = False
    st.session_state.economy03_initial_price_input = 0.5
    st.session_state.economy03_adjustment_speed_input = 1.0

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

settings_panel = st.expander(
    "Settings",
    key="economy03_settings_open",
    on_change="rerun",
)
with settings_panel:
    st.caption(
        "Use the − / + controls throughout. Initial pX and λ change the numerical "
        "price-search path. Pair α changes preferences and therefore the economy."
    )
    with st.form("economy03_settings"):
        st.number_input(
            "Number of agents",
            min_value=2,
            max_value=20,
            step=2,
            key="economy03_agent_count_input",
        )
        st.caption(
            "Agents always come in mirrored pairs, so the count changes by two. "
            "Changing the population resets the experiment to Baseline."
        )
        st.number_input(
            "Initial trial pX",
            min_value=0.01,
            step=0.1,
            key="economy03_initial_price_input",
        )
        st.number_input(
            "Adjustment speed (lambda)",
            min_value=0.1,
            max_value=1.0,
            step=0.1,
            format="%.1f",
            key="economy03_adjustment_speed_input",
        )
        st.markdown("**Pair preferences — α for X**")
        st.caption(
            "For each pair, choose the first agent's α. The partner automatically "
            "gets 1 − α, preserving the mirrored pair and baseline pX = 1."
        )
        for pair_index in range(st.session_state.economy03_agent_count // 2):
            first_agent = pair_index * 2 + 1
            second_agent = first_agent + 1
            st.number_input(
                f"Pair {pair_index + 1}: Agent {first_agent} α for X",
                min_value=0.05,
                max_value=0.95,
                step=0.05,
                format="%.2f",
                key=f"economy03_pair_alpha_{pair_index}_input",
            )
            st.caption(f"Agent {second_agent} automatically uses 1 − α.")
        st.form_submit_button(
            "Apply and close",
            width="stretch",
            on_click=apply_settings,
        )
    if st.button(
        "Reset experiment to baseline",
        key="economy03_reset_experiment",
        width="stretch",
    ):
        st.session_state.economy03_period_populations = baseline_period_populations(
            int(st.session_state.economy03_agent_count),
            tuple(st.session_state.economy03_pair_alphas),
        )
        st.session_state.economy03_period_picker = "Baseline"
        st.session_state.economy03_view_picker = "Overview"
        st.session_state.economy03_settings_open = False
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

with st.container(border=True):
    st.caption("SELECTED RESULT")
    if price_change is None:
        st.markdown(f"### pX {period.prices['X']:.4f}")
        result_change = "Baseline"
    else:
        st.markdown(f"### pX {period.prices['X']:.4f} · {price_change:+.1f}%")
        result_change = f"vs {previous_price:.4f} in the previous step"
    st.caption(
        f"{len(period.population)} agents · {result_change} · "
        f"Market cleared {'✓' if market_ok else '!'} · "
        f"Accounts balanced {'✓' if accounting_ok else '!'}"
    )

if view == "Overview":
    st.subheader("Overview")
    price_history = [
        {
            "step": "Baseline" if index == 0 else f"R{index}",
            "equilibrium pX": item.prices["X"],
        }
        for index, item in enumerate(result.periods)
    ]
    if len(price_history) > 1:
        history_prices = [row["equilibrium pX"] for row in price_history]
        price_low = min(history_prices)
        price_high = max(history_prices)
        price_span = price_high - price_low
        scale_reference = max(abs(price_low), abs(price_high), 1.0)
        price_padding = max(price_span * 0.25, scale_reference * 0.005)
        overview_floor = max(0.0, price_low - price_padding)
        overview_ceiling = price_high + price_padding
        overview_chart = (
            alt.Chart(alt.Data(values=price_history))
            .mark_line(point=True)
            .encode(
                x=alt.X(
                    "step:N",
                    title=None,
                    sort=[row["step"] for row in price_history],
                ),
                y=alt.Y(
                    "equilibrium pX:Q",
                    title="equilibrium pX",
                    scale=alt.Scale(
                        domain=[overview_floor, overview_ceiling],
                        zero=False,
                    ),
                ),
                tooltip=[
                    alt.Tooltip("step:N", title="Step"),
                    alt.Tooltip(
                        "equilibrium pX:Q",
                        title="pX",
                        format=".4f",
                    ),
                ],
            )
            .properties(height=210)
        )
        st.altair_chart(overview_chart, width="stretch")
        st.caption(
            "The vertical axis is zoomed to make redistribution-driven price "
            "changes visible. Read the exact pX in the result block above."
        )

    current_pressure = sum(agent.alpha * agent.y for agent in period.population)
    if previous_period is None:
        st.write(
            "**Baseline:** this is a balanced mirrored-pair population. Nothing "
            "changes through time until you add a redistribution."
        )
        st.markdown(f"**X-demand pressure:** {current_pressure:.3f}")
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

    st.caption(f"Final market error: {final_step.market_error:.1e}")

elif view == "Market":
    st.subheader("Market")
    total_x = sum(spec.x for spec in period.population)
    total_y = sum(spec.y for spec in period.population)

    with st.container(border=True):
        st.markdown(
            f"**Price search:** pX {start_price_x:.3f} → "
            f"{period.prices['X']:.4f}"
        )
        st.caption(f"λ {config.adjustment_speed:.1f} · {adjustments} adjustments")

    comparison_ceiling = max(2.0, start_price_x, period.benchmark_price_x) * 1.05
    comparison_iterations = max(400, adjustments) * 1.05
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
        "The baseline population is built from mirrored agent pairs. There is still "
        "no carry-over inventory, consumption, saving, production, money, credit, "
        "banking, government, or randomness."
    )
    st.caption(
        "Each added period starts from the latest user-defined endowment schedule, "
        "not from the previous period's market closing stocks."
    )
