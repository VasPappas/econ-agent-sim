"""Keep user-supplied names literal at Streamlit Markdown boundaries."""

from string import punctuation


def literal(value: str) -> str:
    return "".join("\\" + char if char in punctuation else char for char in value)
