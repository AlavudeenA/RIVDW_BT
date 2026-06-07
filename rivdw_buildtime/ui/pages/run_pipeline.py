"""Screen 1: trigger the build-time pipeline and watch it run step by step."""

from __future__ import annotations

import csv
import io
import logging
import threading
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import streamlit as st

from config.strings import UILabels, UIMessages
from models.pipeline_state import PipelineState

logger = logging.getLogger(__name__)

_PIPELINE_STEPS = [
    ("connect", UILabels.STEP_CONNECT),
    ("crawl", UILabels.STEP_CRAWL),
    ("diff", UILabels.STEP_DIFF),
    ("normalise", UILabels.STEP_NORMALISE),
    ("enrich", UILabels.STEP_ENRICH),
    ("guardian", UILabels.STEP_VALIDATE),
    ("store", UILabels.STEP_STORE),
]


def render() -> None:
    """Render Screen 1: Run Metadata Ingestion Pipeline."""
    st.title(UILabels.PAGE_RUN_TITLE)
    st.write(UILabels.PAGE_RUN_DESCRIPTION)

    _initialise_session_state()

    if st.session_state.pipeline_running:
        _render_running_state()
    elif st.session_state.pipeline_result is not None:
        _render_completed_state()
    else:
        _render_idle_state()


def _initialise_session_state() -> None:
    """Set up session state keys on first load."""
    defaults = {
        "pipeline_running": False,
        "pipeline_result": None,
        "pipeline_error": None,
        "pipeline_logs": [],
    }
    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default


def _render_idle_state() -> None:
    """Show the Run Pipeline button when nothing is running."""
    st.markdown("---")
    if st.button(UILabels.BTN_RUN_PIPELINE, type="primary", use_container_width=True):
        _start_pipeline()


def _render_running_state() -> None:
    """Show a step-by-step progress display while the pipeline runs."""
    st.info(UIMessages.PIPELINE_RUNNING)

    result: Optional[PipelineState] = st.session_state.pipeline_result

    for node_key, step_label in _PIPELINE_STEPS:
        status = (result.node_status.get(node_key) if result else None) or "running"
        _render_step_row(step_label, status)

    st.rerun()


def _render_completed_state() -> None:
    """Show the results and action buttons after the pipeline finishes."""
    result: PipelineState = st.session_state.pipeline_result

    if st.session_state.pipeline_error:
        st.error(f"{UIMessages.PIPELINE_FAILED}\n\n{st.session_state.pipeline_error}")
    else:
        st.success(UIMessages.PIPELINE_COMPLETE)

    st.markdown("### Steps completed")
    for node_key, step_label in _PIPELINE_STEPS:
        status = result.node_status.get(node_key, "skipped")
        _render_step_row(step_label, status)

    summary = result.summary()
    st.markdown("---")
    st.markdown(
        UIMessages.PIPELINE_SUMMARY.format(
            tables=summary["tables"],
            columns=summary["columns"],
            skipped=summary["skipped"],
        )
    )

    col_download, col_review, col_rerun = st.columns(3)

    with col_download:
        csv_data = _build_summary_csv(result)
        st.download_button(
            label=UILabels.BTN_DOWNLOAD_REPORT,
            data=csv_data,
            file_name=f"pipeline_summary_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
        )

    with col_review:
        if st.button(UILabels.BTN_GO_TO_REVIEW, type="primary"):
            st.switch_page("pages/review_metadata.py")

    with col_rerun:
        if st.button("Run Again"):
            st.session_state.pipeline_result = None
            st.session_state.pipeline_error = None
            st.session_state.pipeline_logs = []
            st.rerun()

    with st.expander("View Details"):
        st.text("\n".join(st.session_state.pipeline_logs))
        if result.failed_entries:
            st.warning(f"{len(result.failed_entries)} entries failed enrichment:")
            for failed_entry in result.failed_entries[:20]:
                st.write(f"- `{failed_entry.get('id', 'unknown')}`: {failed_entry.get('_error', '')}")


def _render_step_row(label: str, status: str) -> None:
    """Display one step row with the appropriate icon."""
    if status == "done":
        icon = "✅"
    elif status == "error":
        icon = "❌"
    elif status == "running":
        icon = "⏳"
    else:
        icon = "⬜"
    st.write(f"{icon} {label}")


def _start_pipeline() -> None:
    """Launch the pipeline in a background thread and update session state."""
    st.session_state.pipeline_running = True
    st.session_state.pipeline_result = None
    st.session_state.pipeline_error = None
    st.session_state.pipeline_logs = []

    thread = threading.Thread(target=_run_pipeline_thread, daemon=True)
    thread.start()
    st.rerun()


def _run_pipeline_thread() -> None:
    """Execute the pipeline on a background thread and store the result in session state."""
    try:
        # Import here to avoid circular imports at module load time
        from pipeline.graph import run_pipeline

        result = run_pipeline()
        st.session_state.pipeline_result = result
        st.session_state.pipeline_running = False
    except Exception as error:
        logger.error("Pipeline thread error: %s", error)
        st.session_state.pipeline_error = str(error)
        st.session_state.pipeline_running = False

        # Build a minimal failed state so the UI can still render
        failed_state = PipelineState()
        for node_key, _ in _PIPELINE_STEPS:
            failed_state.node_status[node_key] = "error"
            failed_state.node_errors[node_key] = str(error)
        st.session_state.pipeline_result = failed_state


def _build_summary_csv(result: PipelineState) -> bytes:
    """Build a CSV summary of all validated entries for download."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id", "source_db", "table_name", "column_name", "data_type",
        "domain_tag", "guardian_status", "description",
    ])

    for entry in result.validated_entries:
        writer.writerow([
            entry.id,
            entry.source_db,
            entry.table_name,
            entry.column_name,
            entry.data_type,
            entry.domain_tag,
            entry.guardian_status,
            entry.description,
        ])

    return output.getvalue().encode("utf-8")
