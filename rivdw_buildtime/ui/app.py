"""Streamlit entry point — handles page routing and navigation."""

from __future__ import annotations

import sys
from pathlib import Path

# Add the project root to sys.path so all modules resolve correctly
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

from config.strings import UILabels

st.set_page_config(
    page_title=UILabels.APP_TITLE,
    page_icon="🗄️",
    layout="wide",
    initial_sidebar_state="expanded",
)


def main() -> None:
    """Set up navigation and route to the selected page."""
    with st.sidebar:
        st.markdown(f"## {UILabels.APP_TITLE}")
        st.markdown("---")

        page = st.radio(
            "Navigation",
            options=[
                UILabels.NAV_BUILD_METADATA,
                UILabels.NAV_RUN_PIPELINE,
                UILabels.NAV_REVIEW_METADATA,
                UILabels.NAV_MANAGE_GLOSSARY,
            ],
            label_visibility="collapsed",
        )

    if page == UILabels.NAV_BUILD_METADATA:
        from ui.pages.build_metadata import render
        render()

    elif page == UILabels.NAV_RUN_PIPELINE:
        from ui.pages.run_pipeline import render
        render()

    elif page == UILabels.NAV_REVIEW_METADATA:
        from ui.pages.review_metadata import render
        render()

    elif page == UILabels.NAV_MANAGE_GLOSSARY:
        from ui.pages.manage_glossary import render
        render()


if __name__ == "__main__":
    main()
