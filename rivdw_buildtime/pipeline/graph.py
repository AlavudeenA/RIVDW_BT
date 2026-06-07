"""LangGraph pipeline definition — all nodes wired together here."""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict

from langgraph.graph import END, START, StateGraph

from models.pipeline_state import PipelineState
from pipeline.nodes.connect_node import connect_node
from pipeline.nodes.crawl_node import crawl_node
from pipeline.nodes.diff_node import diff_node
from pipeline.nodes.enrich_node import enrich_node
from pipeline.nodes.guardian_node import guardian_node
from pipeline.nodes.normalise_node import normalise_node

logger = logging.getLogger(__name__)


def _store_node(state: PipelineState) -> PipelineState:
    """
    Persist validated entries to the Qdrant vector store.
    Approved and needs_review entries are saved; rejected entries are skipped.
    """
    from config.strings import LogMessages
    from vector_store.qdrant_store import get_store

    store = get_store()
    entries_to_save = [
        entry for entry in state.validated_entries
        if entry.guardian_status in ("approved", "needs_review")
    ]
    rejected_count = len(state.validated_entries) - len(entries_to_save)

    saved = store.save_entries(entries_to_save)
    logger.info(LogMessages.STORE_SAVED.format(count=saved))
    logger.info(LogMessages.STORE_SKIPPED.format(count=rejected_count))

    state.mark_node_done("store")
    return state


def build_pipeline() -> StateGraph:
    """
    Construct and compile the LangGraph pipeline.
    Returns a compiled graph ready for invocation.
    """
    # LangGraph requires the state to be a dict-compatible type.
    # We use PipelineState.model_dump() / model_validate() at the boundaries.
    graph = StateGraph(dict)

    # Register each pipeline node as a graph node
    graph.add_node("connect", _wrap_node(connect_node))
    graph.add_node("crawl", _wrap_node(crawl_node))
    graph.add_node("diff", _wrap_node(diff_node))
    graph.add_node("normalise", _wrap_node(normalise_node))
    graph.add_node("enrich", _wrap_node(enrich_node))
    graph.add_node("guardian", _wrap_node(guardian_node))
    graph.add_node("store", _wrap_node(_store_node))

    # Wire nodes in sequence
    graph.add_edge(START, "connect")
    graph.add_edge("connect", "crawl")
    graph.add_edge("crawl", "diff")
    graph.add_edge("diff", "normalise")
    graph.add_edge("normalise", "enrich")
    graph.add_edge("enrich", "guardian")
    graph.add_edge("guardian", "store")
    graph.add_edge("store", END)

    return graph.compile()


def _wrap_node(node_fn: Callable[[PipelineState], PipelineState]) -> Callable[[Dict], Dict]:
    """
    Wrap a PipelineState-based node function into the dict-based signature LangGraph expects.
    Converts dict → PipelineState → node_fn → dict.
    """
    def wrapped(state_dict: Dict[str, Any]) -> Dict[str, Any]:
        pipeline_state = PipelineState.model_validate(state_dict)
        updated_state = node_fn(pipeline_state)
        return updated_state.model_dump()

    wrapped.__name__ = node_fn.__name__
    return wrapped


def run_pipeline(databases_to_crawl: list[str] | None = None) -> PipelineState:
    """
    Execute the full pipeline, log run history to SQLite, and return the final PipelineState.
    If databases_to_crawl is None, all registered databases are crawled.
    """
    from database.sqlite_store import get_sqlite_store

    initial_state = PipelineState(
        databases_to_crawl=databases_to_crawl or []
    )

    sqlite_store = get_sqlite_store()
    sqlite_store.start_run(
        run_id=initial_state.pipeline_run_id,
        started_at=initial_state.started_at,
        databases=initial_state.databases_to_crawl,
    )

    pipeline = build_pipeline()

    logger.info(
        "Pipeline run starting: id=%s, databases=%s",
        initial_state.pipeline_run_id,
        databases_to_crawl,
    )

    error: str | None = None
    try:
        result_dict = pipeline.invoke(initial_state.model_dump())
        final_state = PipelineState.model_validate(result_dict)
    except Exception as exc:
        error = str(exc)
        logger.error("Pipeline failed: %s", error)
        final_state = initial_state
        final_state.mark_node_error("pipeline", error)

    sqlite_store.finish_run(
        run_id=final_state.pipeline_run_id,
        summary=final_state.summary(),
        error=error,
    )
    sqlite_store.set_metadata("last_run_id", final_state.pipeline_run_id)
    sqlite_store.set_metadata("last_run_status", "failed" if error else "completed")

    logger.info(
        "Pipeline run complete: id=%s, summary=%s",
        final_state.pipeline_run_id,
        final_state.summary(),
    )

    return final_state
