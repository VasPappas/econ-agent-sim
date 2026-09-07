from dataclasses import replace
from uuid import uuid4

import streamlit as st

from econ_agent_sim.chat_view import render_chat
from econ_agent_sim.economy_0_2 import canonical_population
from econ_agent_sim.economy_0_4 import ASSETS, Economy04Config
from econ_agent_sim.evidence_view import render_evidence
from econ_agent_sim.experiment_chat import validate_chat_target
from econ_agent_sim.playground import apply_transfer, playground_data
from econ_agent_sim.playground_component import cached_economy, render_playground
from econ_agent_sim.workspace_style import apply_workspace_style


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


def reset_to_baseline():
    clear_redistributions()
    st.session_state.economy04_reset_revision = st.session_state.economy04_revision
    st.session_state.economy04_next_view = "Experiment"
    st.session_state.economy04_reset_notice = "Back at baseline. Transfers removed; your settings are unchanged."


def restore_defaults():
    for name, value in DEFAULTS.items():
        st.session_state[f"economy04_{name}"] = value
    for widget, setting in SETTINGS_INPUTS.items():
        st.session_state[widget] = st.session_state[setting]
    reset_to_baseline()
    st.session_state.economy04_reset_notice = "Original population, allocations, and model settings restored."


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
    st.session_state.economy04_next_view = "Results"
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
    "view_picker": "Experiment",
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
apply_workspace_style()
st.caption("TINY ECONOMY · MONEY")
st.page_link("streamlit_app.py", label="← Explore economies", width="content")
if st.session_state.pop("economy04_open_chat", False):
    st.session_state.economy04_view_picker = "Ask why"
pending_view = st.session_state.pop("economy04_next_view", None)
if pending_view:
    st.session_state.economy04_view_picker = pending_view
# Migrate sessions open during deployment.
st.session_state.economy04_view_picker = {
    "Overview": "Experiment", "Settlement": "Results", "Audit": "Results", "Ask": "Ask why",
}.get(st.session_state.economy04_view_picker, st.session_state.economy04_view_picker)
with st.container(key="economy04_mobile_nav"):
    view = st.pills(
        "View", options=("Experiment", "Results", "Ask why"), required=True,
        default="Experiment", key="economy04_view_picker",
        label_visibility="collapsed", width="stretch",
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
        "Your experiments", step_labels, key="economy04_period_picker",
        format_func=lambda label: label.replace("Redistribution", "Experiment")
    )
    selected_index = step_labels.index(selected_label)
else:
    selected_index = 0
period = result.periods[selected_index]
rows = accounting_rows(period)

latest_index = len(result.periods) - 1
st.button(
    "Reset to baseline", on_click=reset_to_baseline, width="stretch",
    disabled=latest_index == 0,
    help="Remove all transfers and return to the starting allocation. Keep your chosen settings.",
)
if latest_index:
    st.caption("Reset removes transfers and keeps your settings.")
else:
    st.caption("You are at baseline. No transfers to reset.")
if notice := st.session_state.pop("economy04_reset_notice", None):
    st.success(notice)

if view == "Experiment":
    baseline = result.periods[0]
    with st.container(border=True):
        st.markdown("**Your starting point · Baseline**")
        st.write(
            f"{len(baseline.population)} agents · "
            f"{sum(a.x for a in baseline.population):g} X and "
            f"{sum(a.y for a in baseline.population):g} Y in total · "
            f"{config.opening_money_per_agent:g} Money per agent"
        )
        st.caption("The baseline is the starting allocation before any of your transfers, using your chosen settings.")
        with st.expander("Meet the agents at baseline"):
            for agent in baseline.population:
                preference = "Prefers X" if agent.alpha > .5 else "Prefers Y" if agent.alpha < .5 else "Equal spending shares"
                st.markdown(f"**{agent.name} · {preference}**")
                st.write(f"{agent.x:g} X · {agent.y:g} Y · {config.opening_money_per_agent:g} Money")
                st.caption(f"Spends {agent.alpha:.0%} of goods wealth on X and {1-agent.alpha:.0%} on Y.")
    source = "Baseline" if latest_index == 0 else f"Experiment {latest_index}"
    st.markdown(f"**Next: Experiment {latest_index + 1} · starting from {source}’s endowments**")
    st.caption("Your transfer changes these opening goods. Every settlement starts with fresh money; closing balances never carry forward.")
elif selected_index:
    source = "Baseline" if selected_index == 1 else f"Experiment {selected_index - 1}"
    st.caption(f"Experiment {selected_index} · starting from {source}’s endowments, then applying its transfer.")
else:
    st.caption("Baseline · the market outcome before any transfers.")
if selected_index < latest_index:
    st.info(
        "Viewing a past experiment. This does not reset the economy. "
        f"Your next transfer still starts from Experiment {latest_index}’s opening endowments."
    )

if view in ("Experiment", "Results"):
    data = playground_data(
        result,
        selected_index,
        st.session_state.economy04_revision,
        st.session_state.economy04_last_transfer,
    )
    data["error"] = st.session_state.economy04_error
    data["view"] = view
    data["reset_revision"] = st.session_state.get("economy04_reset_revision")
    selection = st.session_state.get("economy04_selected_trade")
    if validate_chat_target(selection, st.session_state.economy04_revision,
                            selected_index, len(period.trades)):
        data["selected_trade"] = selection.get("trade_index")
    component = render_playground(data)
    selection = getattr(component, "selection", None)
    if (validate_chat_target(selection, st.session_state.economy04_revision,
                             selected_index, len(period.trades))
            and selection["id"] != st.session_state.get("economy04_last_selection")):
        st.session_state.economy04_last_selection = selection["id"]
        st.session_state.economy04_selected_trade = selection
    navigation = getattr(component, "navigation", None)
    if (validate_chat_target(navigation, st.session_state.economy04_revision,
                             selected_index, len(period.trades))
            and navigation.get("view") in ("Experiment", "Results")
            and navigation["id"] != st.session_state.get("economy04_last_navigation")):
        st.session_state.economy04_last_navigation = navigation["id"]
        st.session_state.economy04_next_view = navigation["view"]
        st.rerun()
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
        if chat_event.get("trade_index") is not None:
            st.session_state.economy04_selected_trade = chat_event
        st.session_state.economy04_open_chat = True
        st.rerun()
    if component.action and (
        not isinstance(component.action, dict)
        or component.action.get("id") != st.session_state.economy04_last_action_id
    ):
        add_transfer(component.action)
        st.rerun()

if view == "Experiment":
    # Native controls remain as an accessible fallback.
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
        st.caption("Restore defaults also resets the population, opening money, and price-search settings.")
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


if view == "Results":
    with st.expander("Inspect the evidence", expanded=False):
        render_evidence(result, selected_index, rows)
elif view == "Ask why":
    render_chat(result, selected_index, st.session_state.economy04_revision)
    if st.button("← Back to results", width="stretch"):
        st.session_state.economy04_next_view = "Results"
        st.rerun()
