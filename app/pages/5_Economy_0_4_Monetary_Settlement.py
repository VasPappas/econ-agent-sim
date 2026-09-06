from dataclasses import asdict, replace
from uuid import uuid4

import streamlit as st

from econ_agent_sim.chat_view import render_chat
from econ_agent_sim.economy_0_2 import canonical_population
from econ_agent_sim.economy_0_4 import ASSETS, MONEY, Economy04Config
from econ_agent_sim.experiment_chat import validate_chat_target
from econ_agent_sim.playground import apply_transfer, playground_data
from econ_agent_sim.playground_component import cached_economy, render_playground


def baseline_period_populations(agent_count: int = 10):
    """Keep the historical mirrored baseline exactly as before."""
    if agent_count < 2 or agent_count > 20 or agent_count % 2:
        raise ValueError("agent count must be an even number from 2 through 20")
    templates = canonical_population()
    return (
        tuple(
            replace(templates[index % len(templates)], name=f"Agent {index + 1}")
            for index in range(agent_count)
        ),
    )


def current_config():
    return Economy04Config(
        period_populations=st.session_state.economy04_period_populations,
        opening_money_per_agent=float(st.session_state.economy04_opening_money),
        initial_price_x=float(st.session_state.economy04_initial_price_x),
        adjustment_speed=float(st.session_state.economy04_adjustment_speed),
    )


def invalidate_playground():
    st.session_state.economy04_revision += 1
    st.session_state.economy04_last_transfer = None
    st.session_state.economy04_error = None


def apply_settings():
    new_agent_count = int(st.session_state.economy04_agent_count_input)
    population_changed = new_agent_count != st.session_state.economy04_agent_count
    candidate = replace(
        current_config(),
        period_populations=(
            baseline_period_populations(new_agent_count)
            if population_changed
            else st.session_state.economy04_period_populations
        ),
        opening_money_per_agent=float(st.session_state.economy04_opening_money_input),
        initial_price_x=float(st.session_state.economy04_initial_price_input),
        adjustment_speed=float(st.session_state.economy04_adjustment_speed_input),
    )
    try:
        cached_economy(candidate)
    except (ValueError, TypeError, RuntimeError, AssertionError) as error:
        st.session_state.economy04_error = f"Settings were not applied: {error}"
        return
    st.session_state.economy04_agent_count = new_agent_count
    st.session_state.economy04_period_populations = candidate.period_populations
    st.session_state.economy04_opening_money = candidate.opening_money_per_agent
    st.session_state.economy04_initial_price_x = candidate.initial_price_x
    st.session_state.economy04_adjustment_speed = candidate.adjustment_speed
    if population_changed:
        st.session_state.economy04_period_picker = "Baseline"
        for key in (
            "economy04_sender",
            "economy04_receiver",
            "economy04_redistribution_amount",
        ):
            st.session_state.pop(key, None)
    invalidate_playground()
    st.session_state.economy04_settings_open = False


def clear_redistributions():
    st.session_state.economy04_period_populations = baseline_period_populations(
        st.session_state.economy04_agent_count
    )
    st.session_state.economy04_period_picker = "Baseline"
    for key in (
        "economy04_sender",
        "economy04_receiver",
        "economy04_redistribution_amount",
    ):
        st.session_state.pop(key, None)
    invalidate_playground()


def restore_defaults():
    for name, value in DEFAULTS.items():
        st.session_state[f"economy04_{name}"] = value
    for widget, setting in SETTINGS_INPUTS.items():
        st.session_state[widget] = st.session_state[setting]
    clear_redistributions()


def add_transfer(action):
    """Process each component event once and commit only a valid experiment."""
    if not isinstance(action, dict):
        st.session_state.economy04_error = "Invalid transfer request."
        return
    action_id = action.get("id")
    if action_id and action_id == st.session_state.economy04_last_action_id:
        return
    st.session_state.economy04_last_action_id = action_id
    try:
        populations = st.session_state.economy04_period_populations
        new_population = apply_transfer(
            populations[-1], action, st.session_state.economy04_revision
        )
        candidate = replace(
            current_config(), period_populations=(*populations, new_population)
        )
        cached_economy(candidate)
    except (ValueError, TypeError, RuntimeError, AssertionError) as error:
        st.session_state.economy04_error = str(error)
        return
    st.session_state.economy04_period_populations = candidate.period_populations
    st.session_state.economy04_period_picker = f"Redistribution {len(populations)}"
    invalidate_playground()
    st.session_state.economy04_last_transfer = {
        key: action[key] for key in ("sender", "receiver", "amount")
    }


def accounting_rows(period):
    return [
        {
            "agent": name,
            "asset": asset,
            "opening": opening[asset],
            "net flow": period.flows[name][asset],
            "closing": period.closing_stocks[name][asset],
            "check": (
                opening[asset]
                + period.flows[name][asset]
                - period.closing_stocks[name][asset]
            ),
        }
        for name, opening in period.opening_stocks.items()
        for asset in ASSETS
    ]


DEFAULTS = {
    "agent_count": 10,
    "opening_money": 10.0,
    "initial_price_x": 0.5,
    "adjustment_speed": 1.0,
}
SETTINGS_INPUTS = {
    "economy04_agent_count_input": "economy04_agent_count",
    "economy04_opening_money_input": "economy04_opening_money",
    "economy04_initial_price_input": "economy04_initial_price_x",
    "economy04_adjustment_speed_input": "economy04_adjustment_speed",
}
for name, value in DEFAULTS.items():
    st.session_state.setdefault(f"economy04_{name}", value)
for name, value in {
    "period_populations": baseline_period_populations(
        st.session_state.economy04_agent_count
    ),
    "period_picker": "Baseline",
    "view_picker": "Overview",
    "settings_open": False,
    "revision": 0,
    "last_transfer": None,
    "last_action_id": None,
    "error": None,
}.items():
    st.session_state.setdefault(f"economy04_{name}", value)

st.set_page_config(
    page_title="Economy 0.4 — Monetary Settlement",
    layout="centered",
    initial_sidebar_state="collapsed",
)
st.markdown(
    """
<style>
.block-container { padding-top: 1.5rem; }
h1 { font-size: 1.5rem !important; letter-spacing: -0.03em; }
.st-key-economy04_mobile_nav { margin-bottom: 0.25rem; }
@media (max-width: 768px) {
    .block-container { padding-left: 0.75rem; padding-right: 0.75rem; padding-bottom: 2rem; }
    h1 { font-size: 1.25rem !important; }
}
</style>
""",
    unsafe_allow_html=True,
)
st.caption("ECONOMY 0.4")
st.title("Money settles the trade")
with st.container(horizontal=True, wrap=False, gap="small"):
    st.page_link("streamlit_app.py", label="← Home", width="content")
    st.page_link(
        "pages/4_Economy_0_3_Repeated_Exchange.py",
        label="← Economy 0.3",
        width="content",
    )
if st.session_state.pop("economy04_open_chat", False):
    st.session_state.economy04_view_picker = "Ask"
with st.container(key="economy04_mobile_nav"):
    view = st.pills(
        "View",
        options=("Overview", "Settlement", "Audit", "Ask"),
        required=True,
        default="Overview",
        key="economy04_view_picker",
        label_visibility="collapsed",
        width="stretch",
    )

config = current_config()
result = cached_economy(config)
step_labels = ["Baseline"] + [
    f"Redistribution {index}" for index in range(1, len(result.periods))
]
if st.session_state.get("economy04_period_picker") not in step_labels:
    st.session_state.economy04_period_picker = step_labels[-1]
if len(step_labels) > 1:
    selected_label = st.selectbox(
        "Experiment step", step_labels, key="economy04_period_picker"
    )
    selected_index = step_labels.index(selected_label)
else:
    selected_index = 0
period = result.periods[selected_index]
final_step = period.steps[-1]
rows = accounting_rows(period)

if view == "Overview":
    data = playground_data(
        result,
        selected_index,
        st.session_state.economy04_revision,
        st.session_state.economy04_last_transfer,
    )
    data["error"] = st.session_state.economy04_error
    component = render_playground(data)
    chat_event = getattr(component, "question", None)
    if validate_chat_target(
        chat_event,
        st.session_state.economy04_revision,
        selected_index,
        len(period.trades),
    ) and chat_event["id"] != st.session_state.get("economy04_last_chat_event"):
        st.session_state.economy04_last_chat_event = chat_event["id"]
        st.session_state.economy04_chat_trade = chat_event.get("trade_index")
        st.session_state.economy04_chat_trade_identity = (
            st.session_state.economy04_revision,
            selected_index,
        )
        st.session_state.economy04_open_chat = True
        st.rerun()
    if component.action and (
        not isinstance(component.action, dict)
        or component.action.get("id") != st.session_state.economy04_last_action_id
    ):
        add_transfer(component.action)
        st.rerun()

    # Native controls remain as an accessible fallback, not the first screen.
    with st.expander("Add a redistribution", expanded=False):
        st.caption("Alternative controls. Transfers use the latest opening endowments.")
        latest_population = st.session_state.economy04_period_populations[-1]
        names = [agent.name for agent in latest_population]
        sender = st.selectbox("Move Y from", names, key="economy04_sender")
        receiver = st.selectbox("Move Y to", names, index=1, key="economy04_receiver")
        available = next(agent.y for agent in latest_population if agent.name == sender)
        amount = st.number_input(
            "Amount of Y",
            min_value=0.01,
            value=0.1,
            step=0.1,
            key="economy04_redistribution_amount",
        )
        st.caption(f"{sender} has {available:.2f} Y in the latest starting endowment.")
        if st.button(
            "Add as next period",
            width="stretch",
            disabled=sender == receiver or amount > available,
        ):
            add_transfer(
                {
                    "kind": "redistribute",
                    "id": str(uuid4()),
                    "revision": st.session_state.economy04_revision,
                    "sender": sender,
                    "receiver": receiver,
                    "amount": amount,
                }
            )
            st.rerun()

    # Rehydrate missing widget keys from committed settings after view/page changes.
    for widget, setting in SETTINGS_INPUTS.items():
        st.session_state.setdefault(widget, st.session_state[setting])
    settings_panel = st.expander(
        "Settings", key="economy04_settings_open", on_change="rerun"
    )
    with settings_panel:
        st.caption(
            "Agent count changes the economy and clears redistributions. "
            "Opening money affects settlement balances only."
        )
        with st.form("economy04_settings"):
            st.number_input(
                "Number of agents",
                min_value=2,
                max_value=20,
                step=2,
                key="economy04_agent_count_input",
            )
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
                key="economy04_adjustment_speed_input",
            )
            st.form_submit_button(
                "Apply and close", on_click=apply_settings, width="stretch"
            )
        st.button(
            "Clear redistributions", on_click=clear_redistributions, width="stretch"
        )
        st.button(
            "Restore default settings", on_click=restore_defaults, width="stretch"
        )

    if len(result.periods) > 1 and st.button(
        "Remove last redistribution", width="stretch"
    ):
        st.session_state.economy04_period_populations = config.period_populations[:-1]
        st.session_state.economy04_period_picker = step_labels[-2]
        invalidate_playground()
        st.rerun()
    with st.expander("Model boundary"):
        st.subheader("What changed in 0.4?")
        st.write(
            "Money does not enter utility or restrict purchases yet. Every market "
            "goods transfer has a reverse money payment at the clearing price."
        )
        st.caption(
            "Each experiment starts from exogenous X/Y endowments and fresh opening "
            "money. No inventory or financial wealth carries over. Price discovery "
            "finishes before trade. Payments clear as one batch: the animation is "
            "a visual explanation, not a funding sequence."
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

elif view == "Ask":
    render_chat(result, selected_index, st.session_state.economy04_revision)

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
