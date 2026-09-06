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


def chat_setting(name, default=""):
    value = os.environ.get(name)
    if value is not None:
        return value
    try:
        return st.secrets.get(name, default)
    except (FileNotFoundError, st.errors.StreamlitSecretNotFoundError):
        return default


def render_chat(result, selected_index, revision):
    st.subheader("Ask about this experiment")
    st.write("Make sense of the prices, the trades, and what changed.")
    period = result.periods[selected_index]
    identity = (revision, selected_index)
    if st.session_state.get("economy04_chat_trade_identity") != identity:
        st.session_state.economy04_chat_trade = None
        st.session_state.economy04_chat_trade_identity = identity
    options = [None, *range(len(period.trades))]
    trade_index = st.selectbox(
        "Focus",
        options,
        key="economy04_chat_trade",
        format_func=lambda i: (
            "Whole experiment"
            if i is None
            else (
                f"Trade {i + 1} of {len(period.trades)} · "
                f"{period.trades[i].seller} → {period.trades[i].buyer}"
            )
        ),
    )
    context = experiment_context(result, selected_index, trade_index)
    fingerprint = context_id(context)
    # Starting afresh prevents past assistant claims being applied to new results.
    if st.session_state.get("economy04_chat_context") != fingerprint:
        st.session_state.economy04_chat_context = fingerprint
        st.session_state.economy04_chat_messages = []
    history = st.session_state.economy04_chat_messages
    st.session_state.setdefault("economy04_chat_session", str(uuid4()))
    with st.container(border=True):
        st.markdown(
            f"**{context['experiment']}** · {len(period.population)} agents · "
            f"X price **{period.prices['X']:.4f}** · Y fixed at **1**"
        )
        st.caption("Changing the experiment or focus starts a fresh conversation.")
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
        "can be mistaken; check the results in Audit."
    )
    for message in history:
        with st.chat_message(message["role"]):
            # Plain text avoids model-generated HTML, links or tracking images.
            st.text(message["content"])
    suggestion = None
    if not history:
        questions = [
            "Explain this trade."
            if trade_index is not None
            else "What happened in this experiment?",
            "Why is Y's price fixed at 1?",
            "What could I try next?",
        ]
        for i, question in enumerate(questions):
            if st.button(
                question,
                key=f"economy04_suggestion_{i}",
                disabled=not ready,
                width="stretch",
            ):
                suggestion = question
    with st.container():
        typed = st.chat_input(
            "Ask a question…",
            key="economy04_chat_input",
            max_chars=MAX_QUESTION,
            disabled=not ready,
        )
    question = typed or suggestion
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
            st.session_state.economy04_chat_messages = history[-20:]
            st.rerun()
    if history and st.button("Clear conversation", width="stretch"):
        st.session_state.economy04_chat_messages = []
        st.rerun()
