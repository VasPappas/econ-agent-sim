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
    experiment_context,
)
from econ_agent_sim.explanations import built_in_explanations
from econ_agent_sim.run_workspace import run_context, run_explanations


def chat_setting(name, default=""):
    value = os.environ.get(name)
    if value is not None:
        return value
    try:
        return st.secrets.get(name, default)
    except (FileNotFoundError, st.errors.StreamlitSecretNotFoundError):
        return default


def render_chat(result, selected_index, revision, *, previous_result=None, run_number=None):
    st.subheader("Let’s make sense of it.")
    st.write("Make sense of the prices, the trades, and what changed.")
    period = result.periods[selected_index]
    identity = (revision, selected_index)
    def make_context(trade=None):
        if run_number is not None:
            return run_context(result, previous_result, run_number, trade)
        return experiment_context(result, selected_index, trade)

    base_fingerprint = context_id(make_context())
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
            "Whole experiment"
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
    context = make_context(trade_index)
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
    if trade_index is not None:
        st.session_state.economy04_selected_trade = {
            "id": "chat-focus", "revision": revision,
            "selected_index": selected_index, "trade_index": trade_index,
        }
    st.session_state.setdefault("economy04_chat_session", str(uuid4()))
    with st.container(border=True):
        st.markdown(
            f"**{context['experiment']}** · {len(period.population)} agents · "
            f"X price **{period.prices['X']:.4f}** · Y fixed at **1**"
        )
        st.caption("Your conversation stays with this experiment and trade focus.")
    st.markdown("**Explore the explanation**")
    st.caption("From the model · instant · no AI usage")
    explanations = (run_explanations(result, previous_result, trade_index)
                    if run_number is not None else built_in_explanations(result, selected_index, trade_index))
    for title, explanation in explanations.items():
        with st.expander(title):
            st.write(explanation)
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
        "experiment's data go to OpenAI. Avoid personal information. AI explanations "
        "can be mistaken; inspect the evidence in Results. Sending uses the app’s AI allowance."
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
            with st.spinner("Looking at your experiment…"):
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
