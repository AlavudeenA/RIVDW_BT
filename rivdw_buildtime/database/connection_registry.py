"""Reads database list from config/databases.json and creates SQLAlchemy engines."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, Optional

from sqlalchemy import Engine, create_engine, text

from config.settings import DatabaseConfig, get_settings

logger = logging.getLogger(__name__)


class ConnectionRegistry:
    """Holds one SQLAlchemy Engine per configured source database."""

    def __init__(self) -> None:
        self._engines: Dict[str, Engine] = {}
        self._configs: Dict[str, DatabaseConfig] = {}

    def load(self) -> None:
        """
        Read database metadata from config/databases.json and match each entry to the
        connection string stored in .env under the same key as the 'name' field.
        """
        settings = get_settings()
        json_path = Path(settings.databases_config_path)

        if not json_path.exists():
            logger.warning(
                "databases.json not found at %s — no databases loaded. "
                "Create the file and add at least one entry.",
                json_path,
            )
            return

        with open(json_path, encoding="utf-8") as fh:
            db_list = json.load(fh)

        for db_meta in db_list:
            name = db_meta.get("name", "").strip()
            if not name:
                logger.warning("Skipping databases.json entry with no 'name' field: %s", db_meta)
                continue

            conn_str = settings.get_connection_string(name)
            if not conn_str:
                logger.warning(
                    "No connection string in .env for database '%s'. "
                    "Add a line: %s=<sqlalchemy_url>",
                    name,
                    name,
                )
                continue

            db_config = DatabaseConfig(
                name=name,
                display_name=db_meta.get("display_name", name),
                db_type=db_meta.get("db_type", "sqlserver"),
                schema=db_meta.get("schema", "dbo"),
                domain_tag=db_meta.get("domain_tag", ""),
                owner=db_meta.get("owner", ""),
                description=db_meta.get("description", ""),
                connection_string=conn_str,
            )

            try:
                engine = create_engine(
                    conn_str,
                    pool_pre_ping=True,
                    pool_size=2,
                    max_overflow=0,
                )
                self._engines[name] = engine
                self._configs[name] = db_config
                logger.info("Registered database: %s (%s)", name, db_config.db_type)
            except Exception as error:
                logger.error("Failed to create engine for %s: %s", name, error)

    def get_engine(self, database_name: str) -> Optional[Engine]:
        """Return the SQLAlchemy engine for the named database, or None if not found."""
        return self._engines.get(database_name)

    def get_config(self, database_name: str) -> Optional[DatabaseConfig]:
        """Return the DatabaseConfig for the named database."""
        return self._configs.get(database_name)

    def all_names(self) -> list[str]:
        """Return all registered database names."""
        return list(self._engines.keys())

    def test_connection(self, database_name: str) -> tuple[bool, str]:
        """Try a simple query against the named database. Returns (success, message)."""
        engine = self.get_engine(database_name)
        if engine is None:
            return False, f"No engine registered for '{database_name}'"
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return True, "Connection successful"
        except Exception as error:
            return False, str(error)


_registry: Optional[ConnectionRegistry] = None


def get_registry() -> ConnectionRegistry:
    """Return the singleton ConnectionRegistry, loading it on first call."""
    global _registry
    if _registry is None:
        _registry = ConnectionRegistry()
        _registry.load()
    return _registry
