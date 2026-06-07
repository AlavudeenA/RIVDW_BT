"""Screen 2: review and edit AI-generated metadata before it is finalised."""

from __future__ import annotations

import csv
import io
import logging
from typing import Any, Dict, List, Optional

import streamlit as st

from config.strings import UIConfirmations, UILabels, UIMessages

logger = logging.getLogger(__name__)


def render() -> None:
    """Render Screen 2: Review AI-Generated Metadata."""
    st.title(UILabels.PAGE_REVIEW_TITLE)
    st.write(UILabels.PAGE_REVIEW_DESCRIPTION)

    _initialise_session_state()

    entries = _load_all_entries()

    if not entries:
        st.info(UIMessages.NO_ENTRIES_FOUND)
        return

    # Sidebar filters
    with st.sidebar:
        _render_filters(entries)

    # Top action bar
    col_approve_all, col_export = st.columns(2)
    with col_approve_all:
        if st.button(UILabels.BTN_APPROVE_ALL, type="secondary"):
            _handle_approve_all_visible(entries)

    with col_export:
        csv_data = _build_export_csv(entries)
        st.download_button(
            label=UILabels.BTN_EXPORT_REVIEW,
            data=csv_data,
            file_name="metadata_review.csv",
            mime="text/csv",
        )

    # Apply filters
    filtered_entries = _apply_filters(entries)

    if not filtered_entries:
        st.info("No entries match the current filters.")
    else:
        st.markdown(f"**Showing {len(filtered_entries)} entries**")
        _render_entry_cards(filtered_entries)

    # Bottom: reset vector store
    st.markdown("---")
    _render_reset_section()


def _initialise_session_state() -> None:
    """Set up session state for filter and confirmation tracking."""
    defaults = {
        "filter_db": "All",
        "filter_domain": "All",
        "filter_status": "All",
        "search_query": "",
        "show_reset_confirm": False,
        "approve_all_confirm": False,
    }
    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default


def _load_all_entries() -> List[Dict[str, Any]]:
    """Fetch all metadata entries from the vector store."""
    try:
        from vector_store.qdrant_store import get_store
        store = get_store()
        return store.get_all_entries(limit=2000)
    except Exception as error:
        logger.error("Failed to load entries from vector store: %s", error)
        st.error(f"Could not load metadata: {error}")
        return []


def _render_filters(entries: List[Dict[str, Any]]) -> None:
    """Render the sidebar filter controls."""
    st.markdown("### Filters")

    all_dbs = sorted({e.get("source_db", "") for e in entries if e.get("source_db")})
    all_domains = sorted({e.get("domain_tag", "") for e in entries if e.get("domain_tag")})
    all_statuses = [
        UILabels.STATUS_PENDING,
        UILabels.STATUS_APPROVED,
        UILabels.STATUS_REJECTED,
        "needs_review",
    ]

    st.session_state.filter_db = st.selectbox(
        UILabels.FILTER_DATABASE,
        options=[UILabels.LABEL_ALL] + all_dbs,
        index=([UILabels.LABEL_ALL] + all_dbs).index(st.session_state.filter_db)
        if st.session_state.filter_db in [UILabels.LABEL_ALL] + all_dbs
        else 0,
    )
    st.session_state.filter_domain = st.selectbox(
        UILabels.FILTER_DOMAIN,
        options=[UILabels.LABEL_ALL] + all_domains,
        index=([UILabels.LABEL_ALL] + all_domains).index(st.session_state.filter_domain)
        if st.session_state.filter_domain in [UILabels.LABEL_ALL] + all_domains
        else 0,
    )
    st.session_state.filter_status = st.selectbox(
        UILabels.FILTER_STATUS,
        options=[UILabels.LABEL_ALL] + all_statuses,
        index=([UILabels.LABEL_ALL] + all_statuses).index(st.session_state.filter_status)
        if st.session_state.filter_status in [UILabels.LABEL_ALL] + all_statuses
        else 0,
    )
    st.session_state.search_query = st.text_input(
        UILabels.SEARCH_PLACEHOLDER,
        value=st.session_state.search_query,
    )


def _apply_filters(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return only entries matching the active sidebar filters."""
    filtered = entries

    if st.session_state.filter_db != UILabels.LABEL_ALL:
        filtered = [e for e in filtered if e.get("source_db") == st.session_state.filter_db]

    if st.session_state.filter_domain != UILabels.LABEL_ALL:
        filtered = [e for e in filtered if e.get("domain_tag") == st.session_state.filter_domain]

    if st.session_state.filter_status != UILabels.LABEL_ALL:
        status_map = {
            UILabels.STATUS_PENDING: "pending",
            UILabels.STATUS_APPROVED: "approved",
            UILabels.STATUS_REJECTED: "rejected",
            "needs_review": "needs_review",
        }
        target_status = status_map.get(st.session_state.filter_status, st.session_state.filter_status)
        filtered = [e for e in filtered if e.get("guardian_status") == target_status]

    if st.session_state.search_query:
        query = st.session_state.search_query.lower()
        filtered = [
            e for e in filtered
            if query in str(e.get("table_name", "")).lower()
            or query in str(e.get("column_name", "")).lower()
        ]

    return filtered


def _render_entry_cards(entries: List[Dict[str, Any]]) -> None:
    """Render one card per entry with editable fields and action buttons."""
    # Group entries by table for a cleaner layout
    tables: Dict[str, List[Dict[str, Any]]] = {}
    for entry in entries:
        table_key = f"{entry.get('source_db', '')}::{entry.get('table_name', '')}"
        tables.setdefault(table_key, []).append(entry)

    for table_key, table_entries in tables.items():
        # Find table-level entry if it exists
        table_entry = next((e for e in table_entries if not e.get("column_name")), None)
        column_entries = [e for e in table_entries if e.get("column_name")]

        source_db = table_entries[0].get("source_db", "")
        table_name = table_entries[0].get("table_name", "")
        domain_tag = table_entries[0].get("domain_tag", "")
        status = (table_entry or table_entries[0]).get("guardian_status", "pending")

        status_colour = {"approved": "🟢", "needs_review": "🟡", "rejected": "🔴"}.get(status, "⚪")

        with st.container(border=True):
            st.markdown(f"### {status_colour} **{table_name}**")
            st.caption(f"Database: `{source_db}` · Domain: `{domain_tag}`")

            if table_entry:
                _render_single_entry_editor(table_entry, label="Table description")

            if column_entries:
                with st.expander(f"Columns ({len(column_entries)})"):
                    for col_entry in column_entries:
                        col_name = col_entry.get("column_name", "")
                        col_type = col_entry.get("data_type", "")
                        st.markdown(f"**`{col_name}`** `{col_type}`")
                        _render_single_entry_editor(col_entry, label=UILabels.LABEL_AI_DESCRIPTION)
                        st.markdown("---")

            # Action buttons
            entry_for_actions = table_entry or table_entries[0]
            col_approve, col_reject, col_save = st.columns(3)
            with col_approve:
                if st.button(
                    UILabels.BTN_APPROVE,
                    key=f"approve_{entry_for_actions.get('id')}",
                    type="primary",
                ):
                    _approve_entry(entry_for_actions)

            with col_reject:
                if st.button(
                    UILabels.BTN_REJECT,
                    key=f"reject_{entry_for_actions.get('id')}",
                    type="secondary",
                ):
                    _reject_entry(entry_for_actions)

            with col_save:
                if st.button(
                    UILabels.BTN_SAVE_EDITS,
                    key=f"save_{entry_for_actions.get('id')}",
                ):
                    _save_edits(entry_for_actions)


def _render_single_entry_editor(entry: Dict[str, Any], label: str = "") -> None:
    """Render an editable text area for one entry's description and a notes field."""
    entry_id = entry.get("id", "")
    description_key = f"desc_{entry_id}"
    notes_key = f"notes_{entry_id}"

    if description_key not in st.session_state:
        st.session_state[description_key] = entry.get("description", "")
    if notes_key not in st.session_state:
        st.session_state[notes_key] = entry.get("human_notes", "")

    st.text_area(
        label or UILabels.LABEL_AI_DESCRIPTION,
        key=description_key,
        height=120,
    )
    st.text_input(UILabels.LABEL_BUSINESS_NOTES, key=notes_key)


def _approve_entry(entry: Dict[str, Any]) -> None:
    """Mark one entry as approved and human-verified in the vector store."""
    entry_id = entry.get("id", "")
    description = st.session_state.get(f"desc_{entry_id}", entry.get("description", ""))
    notes = st.session_state.get(f"notes_{entry_id}", "")

    try:
        from vector_store.qdrant_store import get_store
        store = get_store()
        store.update_entry_fields(entry_id, {
            "guardian_status": "approved",
            "human_verified": True,
            "description": description,
            "human_notes": notes,
        })
        st.success(f"Approved: {entry.get('table_name')} / {entry.get('column_name', '(table)')}")
    except Exception as error:
        st.error(f"Could not approve entry: {error}")


def _reject_entry(entry: Dict[str, Any]) -> None:
    """Mark one entry as rejected in the vector store."""
    entry_id = entry.get("id", "")
    try:
        from vector_store.qdrant_store import get_store
        store = get_store()
        store.update_entry_fields(entry_id, {
            "guardian_status": "rejected",
            "human_verified": False,
        })
        st.warning(UIMessages.REJECTED_QUEUED)
    except Exception as error:
        st.error(f"Could not reject entry: {error}")


def _save_edits(entry: Dict[str, Any]) -> None:
    """Save description and notes edits without changing the approval status."""
    entry_id = entry.get("id", "")
    description = st.session_state.get(f"desc_{entry_id}", entry.get("description", ""))
    notes = st.session_state.get(f"notes_{entry_id}", "")

    try:
        from vector_store.qdrant_store import get_store
        store = get_store()
        store.update_entry_fields(entry_id, {
            "description": description,
            "human_notes": notes,
        })
        st.success(UIMessages.SAVED)
    except Exception as error:
        st.error(f"Could not save edits: {error}")


def _handle_approve_all_visible(entries: List[Dict[str, Any]]) -> None:
    """Ask for confirmation then approve all currently visible entries."""
    if not st.session_state.approve_all_confirm:
        st.session_state.approve_all_confirm = True
        st.rerun()

    st.warning(UIConfirmations.APPROVE_ALL_VISIBLE)
    col_yes, col_no = st.columns(2)
    with col_yes:
        if st.button("Yes, approve all"):
            filtered = _apply_filters(entries)
            _bulk_approve(filtered)
            st.session_state.approve_all_confirm = False
    with col_no:
        if st.button("Cancel"):
            st.session_state.approve_all_confirm = False
            st.rerun()


def _bulk_approve(entries: List[Dict[str, Any]]) -> None:
    """Approve every entry in the provided list."""
    try:
        from vector_store.qdrant_store import get_store
        store = get_store()
        for entry in entries:
            store.update_entry_fields(entry.get("id", ""), {
                "guardian_status": "approved",
                "human_verified": True,
            })
        st.success(f"Approved {len(entries)} entries.")
    except Exception as error:
        st.error(f"Bulk approve failed: {error}")


def _render_reset_section() -> None:
    """Render the Reset Vector Store button with a two-step confirmation."""
    st.markdown("### Danger Zone")

    if not st.session_state.show_reset_confirm:
        if st.button(UILabels.BTN_RESET_VECTOR_STORE, type="secondary"):
            st.session_state.show_reset_confirm = True
            st.rerun()
    else:
        st.error(UIConfirmations.RESET_VECTOR_STORE_MESSAGE)
        col_confirm, col_cancel = st.columns(2)
        with col_confirm:
            if st.button(UIConfirmations.RESET_CONFIRM_BTN, type="primary"):
                _do_reset_vector_store()
                st.session_state.show_reset_confirm = False
        with col_cancel:
            if st.button(UIConfirmations.RESET_CANCEL_BTN):
                st.session_state.show_reset_confirm = False
                st.rerun()


def _do_reset_vector_store() -> None:
    """Execute the vector store reset."""
    try:
        from vector_store.qdrant_store import get_store
        store = get_store()
        store.reset()
        st.success("Vector store has been reset. Run the pipeline again to rebuild.")
    except Exception as error:
        st.error(f"Reset failed: {error}")


def _build_export_csv(entries: List[Dict[str, Any]]) -> bytes:
    """Build a CSV export of all entries for offline review."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id", "source_db", "table_name", "column_name", "data_type",
        "domain_tag", "guardian_status", "human_verified", "description", "human_notes",
    ])
    for entry in entries:
        writer.writerow([
            entry.get("id", ""),
            entry.get("source_db", ""),
            entry.get("table_name", ""),
            entry.get("column_name", ""),
            entry.get("data_type", ""),
            entry.get("domain_tag", ""),
            entry.get("guardian_status", ""),
            entry.get("human_verified", False),
            entry.get("description", ""),
            entry.get("human_notes", ""),
        ])
    return output.getvalue().encode("utf-8")
