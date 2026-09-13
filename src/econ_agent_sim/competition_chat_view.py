"""Scope-aware questions using the existing shared, bounded AI request path."""

from uuid import uuid4

import streamlit as st

from econ_agent_sim.chat_view import render_conversation
from econ_agent_sim.competition_explanations import (
    competition_context,
    competition_explanations,
)
from econ_agent_sim.experiment_chat import context_id


def render_competition_chat(period, report, run_id, view_key, *, comparison=None):
    st.subheader("Make sense of your economy")
    st.caption(f"{report['label']} · Answers use the results you are viewing.")
    answers = competition_explanations(period, report)
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
    st.write(answers[topic])
    st.caption("From the model · instant · no AI usage")
    st.divider()
    context = competition_context(period, report, run_id, comparison=comparison)
    fingerprint = context_id(context)
    conversations = st.session_state.setdefault("competition_conversations", {})
    history = conversations.pop(fingerprint, [])
    conversations[fingerprint] = history
    while len(conversations) > 12:
        conversations.pop(next(iter(conversations)))
    st.session_state.setdefault("economy04_chat_session", str(uuid4()))
    render_conversation(context, history)
