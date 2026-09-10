"""A phone-friendly, session-local chat view for the selected experiment."""

import os
import tempfile
from pathlib import Path
from uuid import uuid4

import streamlit as st

from econ_agent_sim.experiment_chat import (
    DEFAULT_MODEL,
    MAX_QUESTION,
    ChatUnavailable,
    answer_question,
    context_id,
)
from econ_agent_sim.explanations import built_in_explanations


def chat_setting(name, default=""):
    value = os.environ.get(name)
    if value is not None:
        return value
    try:
        return st.secrets.get(name, default)
    except (FileNotFoundError, st.errors.StreamlitSecretNotFoundError):
        return default


def render_chat(run):
    st.subheader("Let’s make sense of it.")
    st.write("Make sense of the prices, the trades, and what changed.")
    period = run.period
    base_fingerprint = context_id(run.context())
    identity = base_fingerprint
    working = run.data.get("model") == "work_leisure"
    evolving = run.data.get("model") == "production_consumption" or working
    valued_money = run.data.get("model") == "money_in_utility" or evolving
    saved_focus = st.session_state.setdefault("economy04_saved_focus", {})
    if (st.session_state.get("economy04_chat_trade_identity") != identity
            or "economy04_chat_trade" not in st.session_state):
        st.session_state.economy04_chat_trade = saved_focus.get(base_fingerprint, -1)
        st.session_state.economy04_chat_trade_identity = identity
    if st.session_state.get("economy04_chat_trade") is None:
        st.session_state.economy04_chat_trade = -1
    options = [-1, *range(len(period.trades))]
    trade_index = st.selectbox(
        "Focus",
        options,
        key="economy04_chat_trade",
        format_func=lambda i: (
            ("Whole period" if evolving else "Whole run")
        if i == -1
            else (
                f"Trade {i + 1} of {len(period.trades)} · "
                f"{period.trades[i].seller} → {period.trades[i].buyer}"
            )
        ),
    )
    saved_focus[base_fingerprint] = trade_index
    while len(saved_focus) > 12:
        saved_focus.pop(next(iter(saved_focus)))
    trade_index = None if trade_index == -1 else trade_index
    context = run.context(trade_index)
    fingerprint = context_id(context)
    # Restore the matching conversation; never apply another result's history.
    conversations = st.session_state.setdefault("economy04_conversations", {})
    history = conversations.setdefault(fingerprint, [])
    # Bound session memory, preserving the most recently visited contexts.
    conversations.pop(fingerprint)
    conversations[fingerprint] = history
    while len(conversations) > 12:
        conversations.pop(next(iter(conversations)))
    st.session_state.economy04_chat_context = fingerprint
    st.session_state.economy04_chat_messages = history
    st.session_state.setdefault("economy04_chat_session", str(uuid4()))
    with st.container(border=True):
        st.markdown(
            f"**{context['label']}** · {len(period.population)} agents · "
            f"X price **{period.prices['X']:.4f}** · "
            + ("Money is valued" if valued_money else "Y fixed at **1**")
        )
        st.caption("Your conversation stays with this run and trade focus.")
    st.markdown("**Explore the explanation**")
    st.caption("From the model · instant · no AI usage")
    for title, explanation in built_in_explanations(context).items():
        with st.expander(title):
            st.write(explanation)
    if working:
        with st.expander("How were work and price found?"):
            st.write("The model solves work choices and market clearing together. It checks which agents choose zero work, then solves the corresponding linear equation in 1/p. This is not a simulated price-adjustment path.")
            st.latex(r"\ell_i=\max\left(0,\;1-\gamma_i-\frac{\gamma_i}{A_i}\left(x_i^0+\frac{m_i^0}{p}\right)\right)")
            st.caption("ℓ is work time; γ is leisure preference; A is productivity. Opening X and Money are x⁰ and m⁰. Production is A × ℓ. The price makes total desired consumption equal opening X plus production.")
    elif valued_money:
        with st.expander("How was the price found?"):
            st.write("This version solves the clearing price directly; it does not simulate a price-adjustment path.")
            st.latex(r"p_X = \frac{\sum_i \alpha_i m_i^0}{\sum_i (1-\alpha_i)x_i^0}")
            st.caption("α is preference for consumption. Here x⁰ includes this period's production; m⁰ is carried money. The price clears the market before consumption." if evolving else "α is preference for the good. Starting money and goods are m⁰ and x⁰. The price makes total desired X equal total available X.")
    else:
        render_price_history(period)
    render_conversation(context, history)


def render_price_history(period):
    with st.expander("How was the price found?"):
        st.caption(
            "The model adjusts the price of X until demand and supply clear. "
            "Y stays fixed at 1 as the reference price."
        )
        st.dataframe(
            [
                {
                    "step": step.iteration,
                    "X price": step.price_x,
                    "X excess demand": step.excess_demand_x,
                    "Y excess demand": step.excess_demand_y,
                    "market error": step.market_error,
                }
                for step in period.steps
            ],
            width="stretch",
            hide_index=True,
        )


def render_conversation(context, history):
    st.markdown("**Ask a deeper question**")
    key = str(chat_setting("OPENAI_API_KEY"))
    enabled = str(chat_setting("ECON_CHAT_ENABLED", "false")).lower() == "true"
    ready = enabled and bool(key.strip())
    if not ready:
        st.info(
            "The experiment assistant is not connected yet. You can keep exploring the economy."
        )
    st.caption(
        "Powered by OpenAI · When you send a question, your recent chat and this "
        "run's data go to OpenAI. Avoid personal information. AI explanations "
        "can be mistaken; check the accounts in Results. Sending uses the app’s AI allowance."
    )
    for message in history:
        with st.chat_message(message["role"]):
            # Plain text avoids model-generated HTML, links or tracking images.
            st.text(message["content"])
    with st.container():
        typed = st.chat_input(
            "Ask a question…",
            key="economy04_chat_input",
            max_chars=MAX_QUESTION,
            disabled=not ready,
        )
    question = typed
    if question and ready:
        try:
            limit = int(chat_setting("ECON_CHAT_DAILY_LIMIT", "100"))
            with st.spinner("Looking at your run…"):
                answer = answer_question(
                    question,
                    context,
                    history,
                    api_key=key,
                    model=str(chat_setting("OPENAI_MODEL", DEFAULT_MODEL)),
                    budget_path=Path(tempfile.gettempdir())
                    / "econ-chat-budget.sqlite3",
                    session_id=st.session_state.economy04_chat_session,
                    daily_limit=limit,
                )
        except (ChatUnavailable, ValueError) as error:
            st.warning(
                str(error)
                if isinstance(error, ChatUnavailable)
                else "Questions are temporarily unavailable."
            )
            st.caption(
                "Your question wasn't added to the conversation. You can try again."
            )
        else:
            history.extend(
                [
                    {"role": "user", "content": question},
                    {"role": "assistant", "content": answer},
                ]
            )
            history[:] = history[-20:]
            st.session_state.economy04_chat_messages = history
            st.rerun()
    if history and st.button("Clear conversation", width="stretch"):
        history.clear()
        st.session_state.economy04_chat_messages = history
        st.rerun()
