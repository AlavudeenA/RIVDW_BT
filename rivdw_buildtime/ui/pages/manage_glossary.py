"""Screen 3: manage the domain glossary — business-term-to-column mappings."""

from __future__ import annotations

import csv
import io
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import streamlit as st

from config.strings import UIConfirmations, UILabels, UIMessages

logger = logging.getLogger(__name__)


def render() -> None:
    """Render Screen 3: Domain Glossary."""
    st.title(UILabels.PAGE_GLOSSARY_TITLE)
    st.write(UILabels.PAGE_GLOSSARY_DESCRIPTION)

    _initialise_session_state()

    from glossary.domain_glossary import get_glossary
    glossary = get_glossary()
    entries = glossary.all_entries()

    # Top action bar
    col_add, col_export = st.columns(2)

    with col_add:
        if st.button(UILabels.BTN_ADD_TERM, type="primary"):
            st.session_state.show_add_form = True
            st.session_state.edit_index = None

    with col_export:
        csv_data = _build_export_csv(entries)
        st.download_button(
            label=UILabels.BTN_EXPORT_GLOSSARY,
            data=csv_data,
            file_name="glossary_export.csv",
            mime="text/csv",
        )

    # Add / Edit form
    if st.session_state.show_add_form:
        _render_add_edit_form(glossary, edit_index=None)

    if st.session_state.edit_index is not None:
        _render_add_edit_form(glossary, edit_index=st.session_state.edit_index)

    # Delete confirmation
    if st.session_state.delete_index is not None:
        _render_delete_confirmation(glossary, st.session_state.delete_index, entries)

    # Glossary table
    st.markdown("---")
    if not entries:
        st.info(UIMessages.NO_GLOSSARY_TERMS)
    else:
        _render_glossary_table(entries)


def _initialise_session_state() -> None:
    """Set up session state keys for form and confirmation tracking."""
    defaults = {
        "show_add_form": False,
        "edit_index": None,
        "delete_index": None,
    }
    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default


def _render_glossary_table(entries: List[Dict[str, Any]]) -> None:
    """Display all glossary entries in a table with Edit and Delete buttons per row."""
    st.markdown(f"**{len(entries)} glossary terms**")

    header_cols = st.columns([2, 2, 2, 1, 1, 1, 1])
    header_cols[0].markdown(f"**{UILabels.COL_BUSINESS_TERM}**")
    header_cols[1].markdown(f"**{UILabels.COL_MAPS_TO_TABLE}**")
    header_cols[2].markdown(f"**{UILabels.COL_MAPS_TO_COLUMN}**")
    header_cols[3].markdown(f"**{UILabels.COL_DOMAIN}**")
    header_cols[4].markdown(f"**{UILabels.COL_ADDED_BY}**")
    header_cols[5].markdown(f"**{UILabels.BTN_EDIT}**")
    header_cols[6].markdown(f"**{UILabels.BTN_DELETE}**")

    st.markdown("---")

    for index, entry in enumerate(entries):
        row_cols = st.columns([2, 2, 2, 1, 1, 1, 1])
        row_cols[0].write(entry.get("business_term", ""))
        row_cols[1].write(entry.get("maps_to_table", ""))
        row_cols[2].write(entry.get("maps_to_column", ""))
        row_cols[3].write(entry.get("domain", ""))
        row_cols[4].write(entry.get("added_by", ""))

        if row_cols[5].button(UILabels.BTN_EDIT, key=f"edit_{index}"):
            st.session_state.edit_index = index
            st.session_state.show_add_form = False
            st.rerun()

        if row_cols[6].button(UILabels.BTN_DELETE, key=f"delete_{index}"):
            st.session_state.delete_index = index
            st.rerun()


def _render_add_edit_form(glossary: Any, edit_index: Optional[int]) -> None:
    """Render the add-new or edit-existing form."""
    from database.connection_registry import get_registry
    from database.schema_crawler import crawl_database

    is_editing = edit_index is not None
    existing: Dict[str, Any] = glossary.all_entries()[edit_index] if is_editing else {}

    form_title = "Edit Term" if is_editing else "Add New Term"
    st.markdown(f"#### {form_title}")

    registry = get_registry()
    all_db_names = registry.all_names()

    business_term = st.text_input(
        UILabels.INPUT_BUSINESS_TERM,
        value=existing.get("business_term", ""),
        key="form_business_term",
    )

    selected_db = st.selectbox(
        UILabels.INPUT_DATABASE,
        options=all_db_names or ["(no databases configured)"],
        index=all_db_names.index(existing["source_db"])
        if is_editing and existing.get("source_db") in all_db_names
        else 0,
        key="form_database",
    )

    # Load tables dynamically for the selected database
    tables: List[str] = []
    if selected_db and selected_db != "(no databases configured)":
        raw_entries = crawl_database(selected_db)
        tables = sorted({e["table_name"] for e in raw_entries if e.get("table_name")})

    selected_table = st.selectbox(
        UILabels.INPUT_TABLE,
        options=tables or ["(select database first)"],
        index=tables.index(existing["maps_to_table"])
        if is_editing and existing.get("maps_to_table") in tables
        else 0,
        key="form_table",
    )

    # Load columns dynamically for the selected table
    columns: List[str] = []
    if tables and selected_table and selected_table != "(select database first)":
        raw_entries = crawl_database(selected_db)
        columns = sorted({
            e["column_name"]
            for e in raw_entries
            if e.get("table_name") == selected_table and e.get("column_name")
        })

    selected_column = st.selectbox(
        UILabels.INPUT_COLUMN,
        options=columns or ["(select table first)"],
        index=columns.index(existing["maps_to_column"])
        if is_editing and existing.get("maps_to_column") in columns
        else 0,
        key="form_column",
    )

    domain_options = ["compliance", "surveillance", "employee", "brokerage", "finance", "risk"]
    selected_domain = st.selectbox(
        UILabels.INPUT_DOMAIN,
        options=domain_options,
        index=domain_options.index(existing["domain"])
        if is_editing and existing.get("domain") in domain_options
        else 0,
        key="form_domain",
    )

    col_save, col_cancel = st.columns(2)

    with col_save:
        if st.button(UILabels.BTN_SAVE, type="primary", key="form_save"):
            new_entry = {
                "business_term": business_term.strip(),
                "maps_to_table": selected_table if selected_table != "(select database first)" else "",
                "maps_to_column": selected_column if selected_column != "(select table first)" else "",
                "source_db": selected_db,
                "domain": selected_domain,
                "added_by": "ui-user",
                "date_added": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            }
            if not new_entry["business_term"]:
                st.error("Business term cannot be empty.")
            else:
                if is_editing:
                    glossary.update_entry(edit_index, new_entry)
                else:
                    glossary.add_entry(new_entry)
                st.success(UIMessages.SAVED)
                st.session_state.show_add_form = False
                st.session_state.edit_index = None
                st.rerun()

    with col_cancel:
        if st.button(UILabels.BTN_CANCEL, key="form_cancel"):
            st.session_state.show_add_form = False
            st.session_state.edit_index = None
            st.rerun()

    st.markdown("---")


def _render_delete_confirmation(
    glossary: Any, delete_index: int, entries: List[Dict[str, Any]]
) -> None:
    """Ask for confirmation before deleting a glossary term."""
    term_name = entries[delete_index].get("business_term", "this term") if delete_index < len(entries) else "this term"
    st.warning(f"{UIConfirmations.DELETE_GLOSSARY_TERM} Term: **{term_name}**")

    col_yes, col_no = st.columns(2)
    with col_yes:
        if st.button("Yes, delete", type="primary", key="confirm_delete"):
            glossary.delete_entry(delete_index)
            st.success(UIMessages.DELETED)
            st.session_state.delete_index = None
            st.rerun()
    with col_no:
        if st.button("Cancel", key="cancel_delete"):
            st.session_state.delete_index = None
            st.rerun()


def _build_export_csv(entries: List[Dict[str, Any]]) -> bytes:
    """Build a CSV export of all glossary entries."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        UILabels.COL_BUSINESS_TERM,
        UILabels.COL_MAPS_TO_TABLE,
        UILabels.COL_MAPS_TO_COLUMN,
        UILabels.COL_DOMAIN,
        UILabels.COL_ADDED_BY,
        UILabels.COL_DATE,
    ])
    for entry in entries:
        writer.writerow([
            entry.get("business_term", ""),
            entry.get("maps_to_table", ""),
            entry.get("maps_to_column", ""),
            entry.get("domain", ""),
            entry.get("added_by", ""),
            entry.get("date_added", ""),
        ])
    return output.getvalue().encode("utf-8")
