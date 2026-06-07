"""Pydantic model for the state object that travels between LangGraph pipeline nodes."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from pydantic import BaseModel, Field

from models.metadata_entry import MetadataEntry


class PipelineState(BaseModel):
    """Carries all data and tracking information as it flows through the pipeline nodes."""

    # --- input ---
    databases_to_crawl: List[str] = Field(default_factory=list)

    # --- data flowing between nodes ---
    raw_entries: List[Dict[str, Any]] = Field(default_factory=list)
    changed_entries: List[Dict[str, Any]] = Field(default_factory=list)
    normalised_entries: List[MetadataEntry] = Field(default_factory=list)
    enriched_entries: List[MetadataEntry] = Field(default_factory=list)
    validated_entries: List[MetadataEntry] = Field(default_factory=list)

    # --- tracking ---
    skipped_count: int = 0
    failed_entries: List[Dict[str, Any]] = Field(default_factory=list)
    total_tokens_used: int = 0
    pipeline_run_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # --- per-node status for UI reporting ---
    node_status: Dict[str, str] = Field(default_factory=dict)  # node_name -> done/error
    node_errors: Dict[str, str] = Field(default_factory=dict)  # node_name -> error message

    def mark_node_done(self, node_name: str) -> "PipelineState":
        """Record that a node completed successfully."""
        self.node_status[node_name] = "done"
        return self

    def mark_node_error(self, node_name: str, error_message: str) -> "PipelineState":
        """Record that a node encountered an error."""
        self.node_status[node_name] = "error"
        self.node_errors[node_name] = error_message
        return self

    def summary(self) -> Dict[str, int]:
        """Return a summary dict for display on the pipeline results screen."""
        table_entries = [e for e in self.validated_entries if e.is_table_entry()]
        column_entries = [e for e in self.validated_entries if not e.is_table_entry()]
        return {
            "tables": len(set(e.table_name for e in self.validated_entries)),
            "columns": len(column_entries),
            "skipped": self.skipped_count,
            "failed": len(self.failed_entries),
            "tokens": self.total_tokens_used,
        }
