"""SQLite relational store for run history, metadata history, and application metadata via SQLAlchemy ORM."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import Column, DateTime, Integer, String, Text, create_engine, func
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from config.settings import get_settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


class RunHistory(Base):
    """One row per pipeline execution."""

    __tablename__ = "run_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(64), unique=True, nullable=False)
    started_at = Column(DateTime, nullable=False)
    finished_at = Column(DateTime, nullable=True)
    status = Column(String(16), nullable=False, default="running")
    databases_crawled = Column(Text, nullable=True)
    tables_processed = Column(Integer, default=0)
    columns_enriched = Column(Integer, default=0)
    skipped_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)


class MetadataHistory(Base):
    """Every version of every metadata entry — append-only archive."""

    __tablename__ = "metadata_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    entry_id = Column(String(512), nullable=False, index=True)
    source_db = Column(String(128), nullable=False, index=True)
    table_name = Column(String(256), nullable=False)
    column_name = Column(String(256), nullable=False, default="")
    version = Column(Integer, nullable=False)
    description = Column(Text, nullable=True)
    guardian_status = Column(String(32), nullable=True)
    human_notes = Column(Text, nullable=True)
    changed_at = Column(DateTime, nullable=False)
    changed_by = Column(String(64), nullable=False)   # 'llm' or 'user'
    change_type = Column(String(32), nullable=False)  # 'generated' or 'user_edit'


class AppMetadata(Base):
    """Key-value store for application-level metadata."""

    __tablename__ = "app_metadata"

    key = Column(String(128), primary_key=True)
    value = Column(Text, nullable=True)
    updated_at = Column(DateTime, nullable=False)


class SQLiteStore:
    """CRUD operations against the local SQLite database."""

    def __init__(self) -> None:
        settings = get_settings()
        db_path = settings.sqlite_db_path
        engine = create_engine(f"sqlite:///{db_path}", echo=False)
        Base.metadata.create_all(engine)
        self._Session = sessionmaker(bind=engine)
        logger.info("SQLite store initialised at: %s", db_path)

    # ── Run history ──────────────────────────────────────────────────────────

    def start_run(self, run_id: str, started_at: datetime, databases: List[str]) -> None:
        """Insert a new run record with status=running."""
        with self._Session() as session:
            session.add(RunHistory(
                run_id=run_id,
                started_at=started_at,
                status="running",
                databases_crawled=",".join(databases),
            ))
            session.commit()

    def finish_run(self, run_id: str, summary: Dict[str, Any], error: Optional[str] = None) -> None:
        """Update the run record when the pipeline finishes or fails."""
        with self._Session() as session:
            record = session.query(RunHistory).filter_by(run_id=run_id).first()
            if record is None:
                return
            record.finished_at = datetime.now(timezone.utc)
            record.status = "failed" if error else "completed"
            record.tables_processed = summary.get("tables", 0)
            record.columns_enriched = summary.get("columns", 0)
            record.skipped_count = summary.get("skipped", 0)
            record.failed_count = summary.get("failed", 0)
            record.total_tokens = summary.get("tokens", 0)
            record.error_message = error
            session.commit()

    def get_run_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Return the most recent pipeline runs, newest first."""
        with self._Session() as session:
            rows = (
                session.query(RunHistory)
                .order_by(RunHistory.started_at.desc())
                .limit(limit)
                .all()
            )
            return [
                {
                    "run_id": row.run_id,
                    "started_at": row.started_at,
                    "finished_at": row.finished_at,
                    "status": row.status,
                    "databases_crawled": row.databases_crawled,
                    "tables_processed": row.tables_processed,
                    "columns_enriched": row.columns_enriched,
                    "skipped_count": row.skipped_count,
                    "failed_count": row.failed_count,
                    "total_tokens": row.total_tokens,
                    "error_message": row.error_message,
                }
                for row in rows
            ]

    # ── Metadata history (append-only version archive) ───────────────────────

    def archive_entry(
        self,
        entry_id: str,
        source_db: str,
        table_name: str,
        column_name: str,
        description: str,
        guardian_status: str,
        human_notes: str,
        changed_by: str,
        change_type: str,
    ) -> int:
        """
        Write a new version record to metadata_history.
        Returns the version number assigned (auto-incremented per entry_id).
        """
        with self._Session() as session:
            max_version = (
                session.query(func.max(MetadataHistory.version))
                .filter(MetadataHistory.entry_id == entry_id)
                .scalar()
            ) or 0
            new_version = max_version + 1

            session.add(MetadataHistory(
                entry_id=entry_id,
                source_db=source_db,
                table_name=table_name,
                column_name=column_name,
                version=new_version,
                description=description,
                guardian_status=guardian_status,
                human_notes=human_notes,
                changed_at=datetime.now(timezone.utc),
                changed_by=changed_by,
                change_type=change_type,
            ))
            session.commit()
            return new_version

    def get_entry_history(
        self,
        source_db: Optional[str] = None,
        entry_id: Optional[str] = None,
        limit: int = 300,
    ) -> List[Dict[str, Any]]:
        """Return metadata history rows filtered by entry_id or source_db, newest first."""
        with self._Session() as session:
            query = session.query(MetadataHistory)
            if entry_id:
                query = query.filter(MetadataHistory.entry_id == entry_id)
            elif source_db:
                query = query.filter(MetadataHistory.source_db == source_db)
            rows = query.order_by(MetadataHistory.changed_at.desc()).limit(limit).all()
            return [
                {
                    "entry_id": row.entry_id,
                    "source_db": row.source_db,
                    "table_name": row.table_name,
                    "column_name": row.column_name,
                    "version": row.version,
                    "description": row.description,
                    "guardian_status": row.guardian_status,
                    "human_notes": row.human_notes,
                    "changed_at": row.changed_at,
                    "changed_by": row.changed_by,
                    "change_type": row.change_type,
                }
                for row in rows
            ]

    # ── Application metadata ─────────────────────────────────────────────────

    def set_metadata(self, key: str, value: str) -> None:
        """Upsert an application metadata key-value pair."""
        with self._Session() as session:
            record = session.query(AppMetadata).filter_by(key=key).first()
            if record:
                record.value = value
                record.updated_at = datetime.now(timezone.utc)
            else:
                session.add(AppMetadata(key=key, value=value, updated_at=datetime.now(timezone.utc)))
            session.commit()

    def get_metadata(self, key: str) -> Optional[str]:
        """Retrieve an application metadata value by key, or None if not set."""
        with self._Session() as session:
            record = session.query(AppMetadata).filter_by(key=key).first()
            return record.value if record else None


_sqlite_store_instance: Optional[SQLiteStore] = None


def get_sqlite_store() -> SQLiteStore:
    """Return the singleton SQLiteStore, initialising it on first call."""
    global _sqlite_store_instance
    if _sqlite_store_instance is None:
        _sqlite_store_instance = SQLiteStore()
    return _sqlite_store_instance
