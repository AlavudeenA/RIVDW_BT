"""Pipeline node: compare current crawl against previous snapshot, pass only changed entries."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from config.settings import get_settings
from models.pipeline_state import PipelineState

logger = logging.getLogger(__name__)

NODE_NAME = "diff"


def diff_node(state: PipelineState) -> PipelineState:
    """
    Load the most recent previous snapshot and compare it against state.raw_entries.
    Sets state.changed_entries to only new/changed items; increments state.skipped_count.
    """
    settings = get_settings()
    previous_snapshot = _load_previous_snapshot(settings.snapshot_dir)

    if previous_snapshot is None:
        logger.info("Diff node: no previous snapshot found — treating all entries as new")
        state.changed_entries = state.raw_entries
        state.skipped_count = 0
        state.mark_node_done(NODE_NAME)
        return state

    previous_index = _build_index(previous_snapshot)
    new_entries: List[Dict[str, Any]] = []
    unchanged_count = 0

    for entry in state.raw_entries:
        entry_key = _make_key(entry)
        previous_entry = previous_index.get(entry_key)

        if previous_entry is None:
            entry["_change_reason"] = "new"
            new_entries.append(entry)
        elif _data_type_changed(previous_entry, entry):
            entry["_change_reason"] = "type_changed"
            new_entries.append(entry)
        else:
            unchanged_count += 1

    state.changed_entries = new_entries
    state.skipped_count = unchanged_count

    logger.info(
        "Diff complete: %d new/changed, %d unchanged (skipped)",
        len(new_entries),
        unchanged_count,
    )
    state.mark_node_done(NODE_NAME)
    return state


def _load_previous_snapshot(snapshot_dir: str) -> Optional[List[Dict[str, Any]]]:
    """Load the most recently saved snapshot file. Returns None if none exists."""
    path = Path(snapshot_dir)
    if not path.exists():
        return None

    snapshot_files = sorted(path.glob("snapshot_*.json"), reverse=True)
    # Skip the most recent one (that's the one we just wrote in crawl_node)
    if len(snapshot_files) < 2:
        return None

    previous_file = snapshot_files[1]
    try:
        with open(previous_file, "r", encoding="utf-8") as file_handle:
            data = json.load(file_handle)
        logger.info("Loaded previous snapshot: %s (%d entries)", previous_file, len(data))
        return data
    except Exception as error:
        logger.warning("Could not read previous snapshot %s: %s", previous_file, error)
        return None


def _build_index(entries: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Build a lookup dict keyed by (source_db, table_name, column_name)."""
    return {_make_key(entry): entry for entry in entries}


def _make_key(entry: Dict[str, Any]) -> str:
    """Create a stable unique key for an entry."""
    source_db = str(entry.get("source_db", "")).lower()
    table_name = str(entry.get("table_name", "")).lower()
    column_name = str(entry.get("column_name", "")).lower()
    return f"{source_db}__{table_name}__{column_name}"


def _data_type_changed(previous: Dict[str, Any], current: Dict[str, Any]) -> bool:
    """Return True if the column data type changed between snapshots."""
    return str(previous.get("data_type", "")).lower() != str(current.get("data_type", "")).lower()
