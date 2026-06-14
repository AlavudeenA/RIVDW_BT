"""Screen: Query — search metadata using plain-English questions."""

from __future__ import annotations

import streamlit as st

from config.strings import UILabels


def render() -> None:
    """Render the Query screen."""
    st.title(UILabels.PAGE_QUERY_TITLE)
    st.write(UILabels.PAGE_QUERY_DESCRIPTION)

    _initialise_session_state()

    query = st.text_area(
        "Your question",
        placeholder=UILabels.QUERY_INPUT_PLACEHOLDER,
        height=100,
        key="query_input",
        label_visibility="collapsed",
    )

    submitted = st.button(
        UILabels.BTN_QUERY_SUBMIT,
        type="primary",
        disabled=not query.strip(),
    )

    if submitted and query.strip():
        st.session_state["last_query"] = query.strip()

    if st.session_state.get("last_query"):
        st.divider()
        st.markdown(f"**Results for:** _{st.session_state['last_query']}_")
        st.info("Search logic coming soon.")


def _initialise_session_state() -> None:
    if "last_query" not in st.session_state:
        st.session_state["last_query"] = ""
