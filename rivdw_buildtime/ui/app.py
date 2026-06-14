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
                UILabels.NAV_QUERY,
            ],
            label_visibility="collapsed",
        )

        st.markdown("---")
        with st.expander("Reset Vector Store"):
            st.caption("Deletes all stored metadata. You will need to re-generate.")
            if st.button("Reset", type="secondary", use_container_width=True):
                if st.session_state.get("_reset_confirmed"):
                    import shutil
                    from config.settings import get_settings
                    qdrant_path = Path(get_settings().qdrant_path)
                    if qdrant_path.exists():
                        shutil.rmtree(qdrant_path)
                    st.session_state["_reset_confirmed"] = False
                    st.success("Vector store deleted. Re-generate metadata to rebuild.")
                    st.rerun()
                else:
                    st.session_state["_reset_confirmed"] = True
                    st.warning("Click again to confirm.")

    if page == UILabels.NAV_BUILD_METADATA:
        from ui.pages.build_metadata import render
        render()

    elif page == UILabels.NAV_QUERY:
        from ui.pages.query import render
        render()


if __name__ == "__main__":
    main()
