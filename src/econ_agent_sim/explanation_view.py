"""Built-in explanations for the selected economy report."""

import streamlit as st

from econ_agent_sim.explanations import built_in_explanations


def render_explanations(period, report, *, comparison=None):
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
        "Explore a question", list(answers), key="te_explanation_question_topic",
    )
    st.text(answers[topic])
    st.caption("Built-in explanations · based on this simulation")
