"""Compact explanations and bounded optional AI chat for Economy 0.9."""

from uuid import uuid4

import streamlit as st

from econ_agent_sim.chat_view import render_conversation
from econ_agent_sim.experiment_chat import context_id
from econ_agent_sim.investment_explanations import (
    investment_context,
    investment_explanations,
)


def render_investment_chat(period, report, run_id, view_key):
    st.subheader("Make sense of your economy")
    st.caption(f"{report['label']} · Answers use the results you are viewing.")
    answers = investment_explanations(period, report)
    topic = st.selectbox(
        "Explore a question", list(answers), key=f"{view_key}_question_topic",
    )
    st.write(answers[topic])
    st.caption("From the model · instant · no AI usage")
    st.divider()

    context = investment_context(period, report, run_id)
    fingerprint = context_id(context)
    conversations = st.session_state.setdefault("investment_conversations", {})
    history = conversations.pop(fingerprint, [])
    conversations[fingerprint] = history
    while len(conversations) > 12:
        conversations.pop(next(iter(conversations)))
    # Reuse the existing shared session budget and protected API request path.
    st.session_state.setdefault("economy04_chat_session", str(uuid4()))
    render_conversation(context, history)
