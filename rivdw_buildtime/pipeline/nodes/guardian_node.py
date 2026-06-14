"""Pipeline node: validate enriched metadata quality and classify each entry's readiness."""

from __future__ import annotations

import logging
from typing import List, Tuple

from config.settings import get_settings
from config.strings import LogMessages
from models.metadata_entry import MetadataEntry
from models.pipeline_state import PipelineState

logger = logging.getLogger(__name__)

NODE_NAME = "guardian"


def guardian_node(state: PipelineState) -> PipelineState:
    """
    Run quality checks on each enriched entry.
    Sets guardian_status to approved, needs_review, or rejected on each entry.
    """
    settings = get_settings()
    min_words = settings.min_description_word_count
    filler_phrases = settings.get_filler_phrases()
    known_domains = settings.get_known_domains()

    validated: List[MetadataEntry] = []

    for entry in state.enriched_entries:
        status, reason = _validate_entry(
            entry,
            min_words=min_words,
            filler_phrases=filler_phrases,
            known_domains=known_domains,
        )
        entry.guardian_status = status

        if status == "approved":
            logger.info(LogMessages.GUARDIAN_APPROVED.format(entry_id=entry.id))
        elif status == "needs_review":
            entry.human_notes = f"[Guardian flag] {reason}"
            logger.warning(LogMessages.GUARDIAN_REVIEW.format(entry_id=entry.id, reason=reason))
        else:
            entry.human_notes = f"[Guardian rejected] {reason}"
            logger.warning(LogMessages.GUARDIAN_REJECTED.format(entry_id=entry.id, reason=reason))

        validated.append(entry)

    state.validated_entries = validated
    state.mark_node_done(NODE_NAME)

    approved = sum(1 for e in validated if e.guardian_status == "approved")
    review = sum(1 for e in validated if e.guardian_status == "needs_review")
    rejected = sum(1 for e in validated if e.guardian_status == "rejected")

    logger.info(
        "Guardian complete: %d approved, %d needs_review, %d rejected",
        approved, review, rejected,
    )
    return state


def _validate_entry(
    entry: MetadataEntry,
    min_words: int,
    filler_phrases: List[str],
    known_domains: List[str],
) -> Tuple[str, str]:
    """
    Run all quality checks on one entry.
    Returns (guardian_status, failure_reason).
    """
    # Hard failure: empty description — reject immediately
    if not entry.description:
        return "rejected", "Description is empty"

    # Hard failure: missing domain — reject immediately
    if not entry.domain_tag or entry.domain_tag == "unknown":
        return "rejected", "Domain tag is missing"

    # Hard failure: missing source database
    if not entry.source_db:
        return "rejected", "Source database is not tagged"

    # Soft failure: description too short
    if entry.word_count() < min_words:
        return (
            "needs_review",
            f"Description is only {entry.word_count()} words (minimum {min_words})",
        )

    # Soft failure: domain not in the known list
    if entry.domain_tag not in known_domains:
        return "needs_review", f"Domain '{entry.domain_tag}' is not in the known domains list"

    # Soft failure: filler phrases detected
    description_lower = entry.description.lower()
    for phrase in filler_phrases:
        if phrase.lower() in description_lower:
            return "needs_review", f"Description contains generic filler phrase: '{phrase}'"

    return "approved", ""
