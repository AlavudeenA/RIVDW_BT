"""Pipeline node: run schema crawlers against all configured databases and return raw metadata."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from config.settings import get_settings
from database.schema_crawler import crawl_all_databases
from models.pipeline_state import PipelineState

logger = logging.getLogger(__name__)

NODE_NAME = "crawl"


def crawl_node(state: PipelineState) -> PipelineState:
    """
    Connect to each configured database, read table/column structure, and save a snapshot.
    Populates state.raw_entries with one dict per column across all databases.
    """
    settings = get_settings()

    database_names = state.databases_to_crawl
    if not database_names:
        from database.connection_registry import get_registry
        registry = get_registry()
        database_names = registry.all_names()

    logger.info("Crawl node: crawling %d databases", len(database_names))

    try:
        raw_entries = crawl_all_databases(database_names)
        _save_snapshot(raw_entries, settings.snapshot_dir)
        state.raw_entries = raw_entries
        state.mark_node_done(NODE_NAME)
        logger.info("Crawl node complete: %d raw entries collected", len(raw_entries))
    except Exception as error:
        logger.error("Crawl node failed: %s", error)
        state.mark_node_error(NODE_NAME, str(error))

    return state


def _save_snapshot(entries: list, snapshot_dir: str) -> None:
    """Write the full crawl result to a date-stamped JSON file in the snapshots directory."""
    path = Path(snapshot_dir)
    path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    snapshot_file = path / f"snapshot_{timestamp}.json"

    with open(snapshot_file, "w", encoding="utf-8") as file_handle:
        json.dump(entries, file_handle, indent=2, default=str)

    logger.info("Snapshot saved: %s", snapshot_file)
