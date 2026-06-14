"""Pydantic model representing one table or column entry in the metadata pipeline."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class MetadataEntry(BaseModel):
    """One enriched metadata record — either a table-level or column-level entry."""

    # --- identity ---
    id: str  # unique key: source_db__schema__table__column (column empty for table entries)
    source_db: str
    db_type: str  # sqlserver / oracle / postgresql
    domain_tag: str  # compliance / surveillance / employee / brokerage / finance / risk

    # --- structure ---
    schema_name: str = ""  # database schema (e.g. dbo, hr) — stored per-entry to handle multi-schema DBs
    table_name: str
    column_name: str = ""  # empty string when this is a table-level entry
    data_type: str = ""
    nullable: Optional[bool] = None

    # --- enrichment ---
    description: str = ""
    business_terms: List[str] = Field(default_factory=list)
    related_tables: List[str] = Field(default_factory=list)
    business_process: str = ""

    # --- status ---
    guardian_status: str = "pending"  # pending / approved / needs_review / rejected
    human_verified: bool = False
    human_notes: str = ""
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("guardian_status")
    @classmethod
    def validate_guardian_status(cls, value: str) -> str:
        """Ensure guardian_status is one of the allowed values."""
        allowed = {"pending", "approved", "needs_review", "rejected"}
        if value not in allowed:
            raise ValueError(f"guardian_status must be one of {allowed}, got '{value}'")
        return value

    @field_validator("db_type")
    @classmethod
    def validate_db_type(cls, value: str) -> str:
        """Ensure db_type is a recognised database kind."""
        allowed = {"sqlserver", "oracle", "postgresql"}
        if value and value not in allowed:
            raise ValueError(f"db_type must be one of {allowed}, got '{value}'")
        return value

    def is_table_entry(self) -> bool:
        """Return True if this entry describes a whole table (not a specific column)."""
        return self.column_name == ""

    def word_count(self) -> int:
        """Return the number of words in the generated description."""
        return len(self.description.split()) if self.description else 0

    @classmethod
    def make_id(cls, source_db: str, table_name: str, column_name: str = "", schema_name: str = "") -> str:
        """Build the canonical unique ID for a metadata entry."""
        parts = [source_db.lower(), schema_name.lower(), table_name.lower(), column_name.lower()]
        return "__".join(parts)
