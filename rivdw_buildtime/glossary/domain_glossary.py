"""Business term → table/column mapping, loaded from glossary_data/glossary.json."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_GLOSSARY_FILE = Path(__file__).parent.parent / "glossary_data" / "glossary.json"


class DomainGlossary:
    """Holds business-term-to-column mappings and provides lookup methods."""

    def __init__(self) -> None:
        self._entries: List[Dict[str, Any]] = []

    def load(self) -> None:
        """Read glossary entries from the JSON file on disk."""
        if not _GLOSSARY_FILE.exists():
            logger.info("Glossary file not found — starting with empty glossary")
            self._entries = []
            return

        try:
            with open(_GLOSSARY_FILE, "r", encoding="utf-8") as file_handle:
                self._entries = json.load(file_handle)
            logger.info("Loaded %d glossary entries", len(self._entries))
        except Exception as error:
            logger.warning("Could not load glossary: %s", error)
            self._entries = []

    def save(self) -> None:
        """Write current glossary entries back to the JSON file."""
        _GLOSSARY_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(_GLOSSARY_FILE, "w", encoding="utf-8") as file_handle:
            json.dump(self._entries, file_handle, indent=2)
        logger.info("Glossary saved: %d entries", len(self._entries))

    def all_entries(self) -> List[Dict[str, Any]]:
        """Return a copy of all glossary entries."""
        return list(self._entries)

    def add_entry(self, entry: Dict[str, Any]) -> None:
        """Add a new glossary entry and save immediately."""
        self._entries.append(entry)
        self.save()

    def update_entry(self, index: int, entry: Dict[str, Any]) -> None:
        """Replace the entry at the given index and save."""
        self._entries[index] = entry
        self.save()

    def delete_entry(self, index: int) -> None:
        """Remove the entry at the given index and save."""
        self._entries.pop(index)
        self.save()

    def find_terms_for_column(self, table_name: str, column_name: str) -> List[str]:
        """
        Return all business terms that map to the given table/column combination.
        Comparison is case-insensitive.
        """
        table_lower = table_name.lower()
        column_lower = column_name.lower()

        matching_terms: List[str] = []
        for entry in self._entries:
            maps_table = str(entry.get("maps_to_table", "")).lower()
            maps_column = str(entry.get("maps_to_column", "")).lower()
            if maps_table == table_lower and maps_column == column_lower:
                term = entry.get("business_term", "")
                if term:
                    matching_terms.append(term)

        return matching_terms

    def get_all_domains(self) -> List[str]:
        """Return a sorted list of unique domain values currently in the glossary."""
        domains = {str(e.get("domain", "")).strip() for e in self._entries if e.get("domain")}
        return sorted(domains)


_glossary_instance: Optional[DomainGlossary] = None


def get_glossary() -> DomainGlossary:
    """Return the singleton DomainGlossary, loading it on first call."""
    global _glossary_instance
    if _glossary_instance is None:
        _glossary_instance = DomainGlossary()
        _glossary_instance.load()
    return _glossary_instance
