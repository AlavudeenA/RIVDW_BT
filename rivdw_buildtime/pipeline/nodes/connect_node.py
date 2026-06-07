"""Pipeline node: test connections to all configured databases before crawling begins."""

from __future__ import annotations

import logging

from config.strings import ErrorMessages, LogMessages
from database.connection_registry import get_registry
from models.pipeline_state import PipelineState

logger = logging.getLogger(__name__)

NODE_NAME = "connect"


def connect_node(state: PipelineState) -> PipelineState:
    """
    Test each configured database connection and populate databases_to_crawl
    with only the databases that are reachable. Unreachable databases are
    logged as warnings but do not stop the pipeline.
    """
    registry = get_registry()
    candidate_names = state.databases_to_crawl or registry.all_names()

    if not candidate_names:
        logger.warning("No databases configured — pipeline will produce no output")
        state.mark_node_done(NODE_NAME)
        return state

    reachable: list[str] = []

    for db_name in candidate_names:
        success, message = registry.test_connection(db_name)
        if success:
            logger.info("Connected to database: %s", db_name)
            reachable.append(db_name)
        else:
            logger.warning(
                LogMessages.CRAWL_SKIPPED.format(db_name=db_name, error=message)
            )

    state.databases_to_crawl = reachable
    state.mark_node_done(NODE_NAME)

    logger.info(
        "Connect node complete: %d/%d databases reachable",
        len(reachable),
        len(candidate_names),
    )
    return state
