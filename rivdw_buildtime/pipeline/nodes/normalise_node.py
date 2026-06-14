"""Pipeline node: convert raw crawl output into standardised MetadataEntry objects."""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from models.metadata_entry import MetadataEntry
from models.pipeline_state import PipelineState

logger = logging.getLogger(__name__)

NODE_NAME = "normalise"

# Maps database-specific type names to a common vocabulary.
_TYPE_NORMALISATION_MAP: Dict[str, str] = {
    # Oracle
    "number": "integer",
    "varchar2": "varchar",
    "nvarchar2": "nvarchar",
    "char": "char",
    "date": "date",
    "timestamp(6)": "timestamp",
    "timestamp": "timestamp",
    "float": "float",
    "clob": "text",
    "blob": "binary",
    "raw": "binary",
    "long": "text",
    # SQL Server
    "datetime": "timestamp",
    "datetime2": "timestamp",
    "smalldatetime": "timestamp",
    "ntext": "text",
    "image": "binary",
    "money": "decimal",
    "smallmoney": "decimal",
    "bit": "boolean",
    "tinyint": "integer",
    "smallint": "integer",
    "bigint": "bigint",
    "int": "integer",
    "uniqueidentifier": "uuid",
    "xml": "text",
}


def normalise_node(state: PipelineState) -> PipelineState:
    """
    Convert each dict in state.changed_entries into a typed MetadataEntry.
    Normalises database-specific type names and field casing.
    """
    normalised: List[MetadataEntry] = []
    failed: List[Dict[str, Any]] = list(state.failed_entries)

    for raw_entry in state.changed_entries:
        try:
            entry = _normalise_entry(raw_entry)
            normalised.append(entry)
        except Exception as error:
            logger.warning("Normalisation failed for entry %s: %s", raw_entry, error)
            failed_record = dict(raw_entry)
            failed_record["_error"] = str(error)
            failed_record["_stage"] = NODE_NAME
            failed.append(failed_record)

    state.normalised_entries = normalised
    state.failed_entries = failed
    state.mark_node_done(NODE_NAME)

    logger.info("Normalisation complete: %d entries standardised", len(normalised))
    return state


def _normalise_entry(raw: Dict[str, Any]) -> MetadataEntry:
    """Convert one raw crawl dict into a validated MetadataEntry."""
    source_db = str(raw.get("source_db", "")).strip()
    schema_name = str(raw.get("schema_name", "")).strip().lower()
    table_name = str(raw.get("table_name", "")).strip().lower()
    column_name = str(raw.get("column_name", "")).strip().lower()
    db_type = str(raw.get("db_type", "")).strip().lower()
    domain_tag = str(raw.get("domain_tag", "unknown")).strip().lower()
    data_type = _normalise_type(str(raw.get("data_type", "")).strip())
    nullable = raw.get("nullable", None)

    entry_id = MetadataEntry.make_id(source_db, table_name, column_name, schema_name)

    return MetadataEntry(
        id=entry_id,
        source_db=source_db,
        db_type=db_type,
        domain_tag=domain_tag,
        schema_name=schema_name,
        table_name=table_name,
        column_name=column_name,
        data_type=data_type,
        nullable=nullable,
        guardian_status="pending",
        human_verified=False,
    )


def _normalise_type(raw_type: str) -> str:
    """Map a database-specific type string to the common type vocabulary."""
    lower_type = raw_type.lower().strip()
    # Check exact match first
    if lower_type in _TYPE_NORMALISATION_MAP:
        return _TYPE_NORMALISATION_MAP[lower_type]
    # Check prefix match for parameterised types like varchar(255)
    for known_type, normalised_type in _TYPE_NORMALISATION_MAP.items():
        if lower_type.startswith(known_type):
            return normalised_type
    return lower_type or "unknown"
