"""Scope-aware, session-local explanations for the current economy."""

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
from econ_agent_sim.explanations import build_context, built_in_explanations


def chat_setting(name, default=""):
    value = os.environ.get(name)
    if value is not None:
        return value
    try:
        return st.secrets.get(name, default)
    except (FileNotFoundError, st.errors.StreamlitSecretNotFoundError):
        return default


def render_chat(period, report, run_id, view_key, *, comparison=None):
    st.subheader("Make sense of your economy")
    st.caption(f"{report['label']} · Answers use the results you are viewing.")
    answers = built_in_explanations(period, report)
    if comparison is not None:
        answers["How should I read the baseline comparison?"] = (
            f"{comparison['label']}. {comparison['note']} "
            "Each firm's comparison follows its identity across experiments. "
            "Sales-share changes are percentage points. Changed settings compare "
            "submitted runs, not unsubmitted edits. A higher number is not "
            "automatically better for households with different priorities."
        )
    topic = st.selectbox(
        "Explore a question", list(answers), key=f"{view_key}_question_topic",
    )
    st.text(answers[topic])
    st.caption("From the model · instant · no AI usage")
    st.divider()
    context = build_context(period, report, run_id, comparison=comparison)
    fingerprint = context_id(context)
    conversations = st.session_state.setdefault("te_conversations", {})
    history = conversations.pop(fingerprint, [])
    conversations[fingerprint] = history
    while len(conversations) > 12:
        conversations.pop(next(iter(conversations)))
    # Workspace resets clear conversations, not the request-budget identity.
    st.session_state.setdefault("chat_session_id", str(uuid4()))
    render_conversation(context, history)


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
            key="te_chat_input",
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
                    session_id=st.session_state.chat_session_id,
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
            st.rerun()
    if history and st.button("Clear conversation", width="stretch"):
        history.clear()
        st.rerun()
