"""Pipeline node: call the LLM to generate plain-English descriptions for each metadata entry."""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, List, Optional

import requests
from groq import Groq

from config.settings import get_settings
from config.strings import LLMPrompts, LogMessages
from models.metadata_entry import MetadataEntry
from models.pipeline_state import PipelineState

logger = logging.getLogger(__name__)

NODE_NAME = "enrich"


def enrich_node(state: PipelineState) -> PipelineState:
    """
    Call the LLM for each normalised entry to generate descriptions, business terms,
    and related table suggestions. Processes in batches to avoid rate limits.
    """
    settings = get_settings()
    entries = state.normalised_entries
    batch_size = settings.enrichment_batch_size

    enriched: List[MetadataEntry] = []
    failed = list(state.failed_entries)
    total_tokens = state.total_tokens_used

    batches = [entries[i : i + batch_size] for i in range(0, len(entries), batch_size)]
    total_batches = len(batches)

    for batch_index, batch in enumerate(batches, start=1):
        logger.info(
            LogMessages.ENRICH_BATCH.format(
                batch_num=batch_index, total_batches=total_batches, count=len(batch)
            )
        )

        for entry in batch:
            try:
                enriched_entry, tokens_used = _enrich_single_entry(entry, settings)
                enriched.append(enriched_entry)
                total_tokens += tokens_used
            except Exception as error:
                logger.error(
                    LogMessages.ENRICH_ENTRY_FAILED.format(entry_id=entry.id, error=error)
                )
                failed_record = entry.model_dump()
                failed_record["_error"] = str(error)
                failed_record["_stage"] = NODE_NAME
                failed.append(failed_record)
                enriched.append(entry)  # keep un-enriched entry so pipeline continues

        # Short pause between batches to stay within rate limits
        if batch_index < total_batches:
            time.sleep(1)

    state.enriched_entries = enriched
    state.failed_entries = failed
    state.total_tokens_used = total_tokens
    state.mark_node_done(NODE_NAME)

    logger.info("Enrich node complete: %d entries enriched", len(enriched))
    return state


def _enrich_single_entry(
    entry: MetadataEntry, settings: Any
) -> tuple[MetadataEntry, int]:
    """Call the LLM for one entry and return the enriched entry plus token count."""
    prompt = LLMPrompts.ENRICHMENT_TEMPLATE.format(
        source_db=entry.source_db,
        domain_tag=entry.domain_tag,
        table_name=entry.table_name,
        column_name=entry.column_name if entry.column_name else "(table-level)",
        data_type=entry.data_type,
        business_terms="none known",
    )

    llm_response, tokens_used = _call_llm(prompt, settings)

    parsed = _parse_llm_response(llm_response)

    entry.description = parsed.get("description", "")
    entry.business_terms = parsed.get("business_terms", [])
    entry.related_tables = parsed.get("related_tables", [])
    entry.business_process = parsed.get("business_process", "")

    return entry, tokens_used


def _call_llm(prompt: str, settings: Any) -> tuple[str, int]:
    """Route LLM call to Groq (primary) or VS Code LM API (fallback)."""
    if settings.groq_enabled and settings.groq_api_key:
        return _call_groq(prompt, settings)
    else:
        logger.info(LogMessages.LLM_FALLBACK)
        return _call_vscode_lm(prompt, settings)


def _call_groq(prompt: str, settings: Any) -> tuple[str, int]:
    """Send a prompt to the Groq API and return (response_text, token_count)."""
    client = Groq(api_key=settings.groq_api_key)

    completion = client.chat.completions.create(
        model=settings.groq_model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a data dictionary expert for a banking compliance system. "
                    "Always respond with valid JSON only. No markdown, no explanation outside the JSON."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        max_tokens=4096,
    )

    response_text = completion.choices[0].message.content or ""
    tokens_used = completion.usage.total_tokens if completion.usage else 0
    return response_text, tokens_used


def _call_vscode_lm(prompt: str, settings: Any) -> tuple[str, int]:
    """
    Send a prompt to the local VS Code LM API server (running on localhost).
    The VS Code extension exposes POST /prompt on the configured port.
    """
    url = f"http://127.0.0.1:{settings.vscode_lm_port}/prompt"
    payload = {
        "secret": settings.vscode_lm_secret,
        "system": (
            "You are a data dictionary expert for a banking compliance system. "
            "Always respond with valid JSON only. No markdown, no explanation outside the JSON."
        ),
        "prompt": prompt,
    }

    try:
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        return data.get("text", ""), 0  # VS Code LM API does not report token counts
    except requests.RequestException as error:
        raise RuntimeError(f"VS Code LM API call failed: {error}") from error


def _parse_llm_response(raw_response: str) -> Dict[str, Any]:
    """
    Parse the JSON response from the LLM.
    Returns a dict with description, business_terms, related_tables, business_process.
    Falls back to empty values if parsing fails.
    """
    if not raw_response:
        return _empty_response()

    # Strip markdown code fences if the LLM added them
    cleaned = raw_response.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        cleaned = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

    try:
        data = json.loads(cleaned)
        return {
            "description": str(data.get("description", "")),
            "business_terms": list(data.get("business_terms", [])),
            "related_tables": list(data.get("related_tables", [])),
            "business_process": str(data.get("business_process", "")),
        }
    except json.JSONDecodeError:
        # If LLM returned plain text instead of JSON, use it as the description
        logger.warning("LLM returned non-JSON response; using raw text as description")
        return {
            "description": raw_response.strip(),
            "business_terms": [],
            "related_tables": [],
            "business_process": "",
        }


def _empty_response() -> Dict[str, Any]:
    """Return a blank enrichment result when the LLM response was empty."""
    return {
        "description": "",
        "business_terms": [],
        "related_tables": [],
        "business_process": "",
    }
