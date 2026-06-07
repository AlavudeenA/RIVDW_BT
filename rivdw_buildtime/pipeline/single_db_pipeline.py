"""
Process one database at a time with per-table progress reporting.
Used by the Build Metadata UI screen — makes one LLM call per table
(returns descriptions for all columns at once) for efficiency.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Callable, Dict, List, Optional

from config.settings import get_settings
from config.strings import LLMPrompts
from database.schema_crawler import crawl_database
from database.sqlite_store import get_sqlite_store
from glossary.domain_glossary import get_glossary
from models.metadata_entry import MetadataEntry
from pipeline.nodes.enrich_node import _call_llm
from pipeline.nodes.guardian_node import _validate_entry
from pipeline.nodes.normalise_node import _normalise_entry
from vector_store.qdrant_store import get_store

logger = logging.getLogger(__name__)

# Type alias for the progress callback: (event, table_name, optional_detail)
ProgressFn = Optional[Callable[[str, str, str], None]]


def process_database(
    database_name: str,
    progress_fn: ProgressFn = None,
) -> List[MetadataEntry]:
    """
    Full pipeline for a single database: crawl → normalise → enrich → validate → store.

    Calls progress_fn(event, table_name, detail) at key moments:
      event="start"   — table processing is beginning
      event="done"    — table fully stored
      event="error"   — something failed for this table

    Returns all MetadataEntry objects that were successfully stored.
    """
    settings = get_settings()
    qdrant = get_store()
    sqlite = get_sqlite_store()
    glossary = get_glossary()

    raw_entries = crawl_database(database_name)
    if not raw_entries:
        logger.warning("No entries found for database: %s", database_name)
        return []

    # Group raw entries by table name
    tables: Dict[str, List[Dict[str, Any]]] = {}
    for raw in raw_entries:
        tables.setdefault(raw["table_name"], []).append(raw)

    all_stored: List[MetadataEntry] = []

    for table_name, columns in tables.items():
        if progress_fn:
            progress_fn("start", table_name, f"{len(columns)} columns")

        try:
            entries = _process_one_table(table_name, columns, settings, glossary)

            for entry in entries:
                # Archive to history first (LLM-generated version)
                sqlite.archive_entry(
                    entry_id=entry.id,
                    source_db=entry.source_db,
                    table_name=entry.table_name,
                    column_name=entry.column_name,
                    description=entry.description,
                    guardian_status=entry.guardian_status,
                    human_notes=entry.human_notes,
                    changed_by="llm",
                    change_type="generated",
                )
                # Then upsert into vector store (always latest version)
                qdrant.save_entry(entry)

            all_stored.extend(entries)

            if progress_fn:
                progress_fn("done", table_name, f"{len(entries)} entries stored")

        except Exception as error:
            logger.error("Error processing table %s: %s", table_name, error)
            if progress_fn:
                progress_fn("error", table_name, str(error))

    return all_stored


def process_single_table_by_name(
    database_name: str,
    table_name: str,
) -> List[MetadataEntry]:
    """
    Re-generate metadata for one specific table (used by the Re-generate button in the UI).
    Archives the previous version before overwriting.
    """
    settings = get_settings()
    qdrant = get_store()
    sqlite = get_sqlite_store()
    glossary = get_glossary()

    raw_entries = crawl_database(database_name)
    table_columns = [r for r in raw_entries if r["table_name"] == table_name]

    if not table_columns:
        logger.warning("Table %s not found in database %s", table_name, database_name)
        return []

    entries = _process_one_table(table_name, table_columns, settings, glossary)

    for entry in entries:
        # Archive old version first if it exists
        existing = qdrant.get_entry_by_id(entry.id)
        if existing and existing.get("description"):
            sqlite.archive_entry(
                entry_id=entry.id,
                source_db=entry.source_db,
                table_name=entry.table_name,
                column_name=entry.column_name,
                description=existing.get("description", ""),
                guardian_status=existing.get("guardian_status", ""),
                human_notes=existing.get("human_notes", ""),
                changed_by="system",
                change_type="replaced_by_regenerate",
            )
        # Archive the new LLM version
        sqlite.archive_entry(
            entry_id=entry.id,
            source_db=entry.source_db,
            table_name=entry.table_name,
            column_name=entry.column_name,
            description=entry.description,
            guardian_status=entry.guardian_status,
            human_notes=entry.human_notes,
            changed_by="llm",
            change_type="regenerated",
        )
        qdrant.save_entry(entry)

    return entries


def save_user_edit(
    entry_id: str,
    new_description: str,
    human_notes: str,
) -> bool:
    """
    Save a user's manual edit to an entry.
    Archives the previous version to history, then updates the vector store.
    Returns True on success.
    """
    qdrant = get_store()
    sqlite = get_sqlite_store()

    existing = qdrant.get_entry_by_id(entry_id)
    if not existing:
        logger.warning("Cannot save edit — entry not found: %s", entry_id)
        return False

    # Archive the version being replaced
    sqlite.archive_entry(
        entry_id=entry_id,
        source_db=existing.get("source_db", ""),
        table_name=existing.get("table_name", ""),
        column_name=existing.get("column_name", ""),
        description=new_description,
        guardian_status=existing.get("guardian_status", ""),
        human_notes=human_notes,
        changed_by="user",
        change_type="user_edit",
    )

    # Update the vector store with the new description + notes
    return qdrant.update_entry_fields(
        entry_id,
        {
            "description": new_description,
            "human_notes": human_notes,
            "human_verified": True,
            "guardian_status": "approved",
        },
    )


# ── Internal helpers ─────────────────────────────────────────────────────────


def _process_one_table(
    table_name: str,
    raw_columns: List[Dict[str, Any]],
    settings: Any,
    glossary: Any,
) -> List[MetadataEntry]:
    """
    Normalise, batch-enrich, and validate all entries for one table.
    Makes a single LLM call that returns descriptions for every column at once.
    """
    normalised = [_normalise_entry(col) for col in raw_columns]

    # One LLM call for the whole table
    llm_data = _batch_enrich_table(table_name, normalised, settings, glossary)

    filler_phrases = settings.get_filler_phrases()
    known_domains = settings.get_known_domains()

    for entry in normalised:
        col_data = llm_data.get("columns", {}).get(entry.column_name, {})
        entry.description = col_data.get("description", "")
        entry.business_terms = col_data.get("business_terms", [])
        entry.related_tables = col_data.get("related_tables", [])
        entry.business_process = col_data.get("business_process", "")

        status, reason = _validate_entry(
            entry,
            min_words=settings.min_description_word_count,
            filler_phrases=filler_phrases,
            known_domains=known_domains,
            glossary=glossary,
        )
        entry.guardian_status = status
        if reason:
            entry.human_notes = f"[Guardian: {reason}]"

    # Also create a table-level entry using the table description
    table_entry = _make_table_entry(normalised[0], llm_data)
    if table_entry:
        status, reason = _validate_entry(
            table_entry,
            min_words=settings.min_description_word_count,
            filler_phrases=filler_phrases,
            known_domains=known_domains,
            glossary=glossary,
        )
        table_entry.guardian_status = status
        if reason:
            table_entry.human_notes = f"[Guardian: {reason}]"
        return [table_entry] + normalised

    return normalised


def _batch_enrich_table(
    table_name: str,
    normalised_entries: List[MetadataEntry],
    settings: Any,
    glossary: Any,
) -> Dict[str, Any]:
    """
    Make one LLM call covering the entire table and return the parsed response dict.
    Falls back to an empty dict if the LLM call fails.
    """
    column_lines = "\n".join(
        f"  {e.column_name} | {e.data_type}" for e in normalised_entries if e.column_name
    )

    first = normalised_entries[0]
    prompt = LLMPrompts.BATCH_TABLE_TEMPLATE.format(
        source_db=first.source_db,
        domain_tag=first.domain_tag,
        table_name=table_name,
        column_list=column_lines,
    )

    try:
        raw_response, _ = _call_llm(prompt, settings)
        return _parse_batch_response(raw_response)
    except Exception as error:
        logger.warning("Batch LLM call failed for table %s: %s", table_name, error)
        return {}


def _parse_batch_response(raw: str) -> Dict[str, Any]:
    """Parse the JSON returned by the batch table LLM call."""
    if not raw:
        return {}
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        cleaned = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning("Could not parse batch LLM response as JSON")
        return {}


def _make_table_entry(
    column_entry: MetadataEntry,
    llm_data: Dict[str, Any],
) -> Optional[MetadataEntry]:
    """Build a table-level MetadataEntry using the table_description from the LLM response."""
    table_desc = llm_data.get("table_description", "")
    if not table_desc:
        return None

    return MetadataEntry(
        id=MetadataEntry.make_id(column_entry.source_db, column_entry.table_name, ""),
        source_db=column_entry.source_db,
        db_type=column_entry.db_type,
        domain_tag=column_entry.domain_tag,
        table_name=column_entry.table_name,
        column_name="",
        data_type="",
        description=table_desc,
        business_terms=[],
        related_tables=llm_data.get("table_related_tables", []),
        business_process=llm_data.get("table_business_process", ""),
        guardian_status="pending",
        human_verified=False,
    )
