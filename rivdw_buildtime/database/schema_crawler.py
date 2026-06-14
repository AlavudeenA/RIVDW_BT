"""Connects to each configured database and reads table/column structure from system catalogs."""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from sqlalchemy import text

from config.settings import DatabaseConfig
from database.connection_registry import get_registry

logger = logging.getLogger(__name__)

# Read-only queries against system catalogs — never touches actual data rows.
_SQL_SERVER_CATALOG_QUERY = """
SELECT
    s.name  AS schema_name,
    t.name  AS table_name,
    c.name  AS column_name,
    ty.name AS data_type,
    c.is_nullable AS nullable
FROM sys.tables  t
JOIN sys.schemas s  ON t.schema_id = s.schema_id
JOIN sys.columns c  ON t.object_id = c.object_id
JOIN sys.types   ty ON c.user_type_id = ty.user_type_id
WHERE t.is_ms_shipped = 0
  AND s.name = :schema_name
ORDER BY t.name, c.column_id
"""

_ORACLE_CATALOG_QUERY = """
SELECT
    owner       AS schema_name,
    table_name,
    column_name,
    data_type,
    nullable
FROM ALL_TAB_COLUMNS
WHERE owner = :schema_name
ORDER BY table_name, column_id
"""


def crawl_database(database_name: str) -> List[Dict[str, Any]]:
    """
    Connect to the named database and return raw column entries from the system catalog.
    Each entry is a dict with: source_db, db_type, domain_tag, table_name, column_name,
    data_type, nullable.
    """
    registry = get_registry()
    engine = registry.get_engine(database_name)
    db_config = registry.get_config(database_name)

    if engine is None or db_config is None:
        logger.warning("Skipping unknown database: %s", database_name)
        return []

    logger.info("Starting schema crawl for database: %s (%s)", database_name, db_config.db_type)

    try:
        raw_rows = _execute_catalog_query(engine, db_config)
        entries = _rows_to_entries(raw_rows, db_config)
        logger.info("Crawl complete for %s: %d columns found", database_name, len(entries))
        return entries
    except Exception as error:
        logger.error("Crawl failed for %s: %s", database_name, error)
        return []


def _execute_catalog_query(engine: Any, db_config: DatabaseConfig) -> List[Dict[str, Any]]:
    """Run the appropriate catalog query and return rows as dicts."""
    with engine.connect() as connection:
        if db_config.db_type == "sqlserver":
            result = connection.execute(
                text(_SQL_SERVER_CATALOG_QUERY),
                {"schema_name": db_config.schema},
            )
        elif db_config.db_type == "oracle":
            result = connection.execute(
                text(_ORACLE_CATALOG_QUERY),
                {"schema_name": db_config.schema.upper()},
            )
        else:
            raise ValueError(f"Unsupported db_type: {db_config.db_type}")

        columns = list(result.keys())
        return [dict(zip(columns, row)) for row in result.fetchall()]


def _rows_to_entries(
    rows: List[Dict[str, Any]],
    db_config: DatabaseConfig,
) -> List[Dict[str, Any]]:
    """Convert raw catalog rows into tagged entry dicts."""
    entries: List[Dict[str, Any]] = []

    for row in rows:
        table_name = str(row.get("table_name", "")).strip()
        column_name = str(row.get("column_name", "")).strip()
        data_type = str(row.get("data_type", "")).strip()
        raw_nullable = row.get("nullable", None)

        nullable: Any = None
        if raw_nullable is not None:
            if isinstance(raw_nullable, bool):
                nullable = raw_nullable
            elif str(raw_nullable).upper() in ("Y", "1", "TRUE"):
                nullable = True
            elif str(raw_nullable).upper() in ("N", "0", "FALSE"):
                nullable = False

        schema_name = str(row.get("schema_name", db_config.schema or "")).strip()

        entries.append({
            "source_db": db_config.name,
            "db_type": db_config.db_type,
            "domain_tag": db_config.domain_tag,
            "schema_name": schema_name,
            "table_name": table_name,
            "column_name": column_name,
            "data_type": data_type,
            "nullable": nullable,
        })

    return entries


def crawl_all_databases(database_names: List[str]) -> List[Dict[str, Any]]:
    """
    Crawl all databases in the list, skipping any that fail.
    Returns a flat list of all column entries across all databases.
    """
    all_entries: List[Dict[str, Any]] = []

    for database_name in database_names:
        entries = crawl_database(database_name)
        all_entries.extend(entries)

    logger.info("Total entries from all databases: %d", len(all_entries))
    return all_entries
