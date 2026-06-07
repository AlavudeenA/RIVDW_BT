"""Embedding helpers — wraps FastEmbed with a local cache directory and corruption recovery."""

from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path
from typing import Any

import numpy as np

from config.settings import get_settings

logger = logging.getLogger(__name__)

_model: Any = None


def _local_cache_dir() -> str:
    """Return the project-local fastembed cache directory (committed to .gitignore)."""
    return str(Path(__file__).parent.parent / "fastembed_cache")


def _fastembed_cache_root() -> Path:
    """Return the system-level fastembed cache root (used for clearing on corruption)."""
    local_appdata = os.environ.get("LOCALAPPDATA")
    if local_appdata:
        return Path(local_appdata) / "Temp" / "fastembed_cache"
    return Path.cwd() / ".fastembed_cache"


def _clear_fastembed_cache() -> None:
    """Delete both the local and system fastembed caches so the model re-downloads cleanly."""
    for cache_path in (_local_cache_dir(), str(_fastembed_cache_root())):
        p = Path(cache_path)
        if p.exists():
            shutil.rmtree(p, ignore_errors=True)
            logger.warning("Cleared corrupted fastembed cache at %s", cache_path)


def _get_model() -> Any:
    """Return the singleton TextEmbedding model, loading from local cache on first call."""
    global _model
    if _model is None:
        from fastembed import TextEmbedding

        settings = get_settings()
        cache_dir = _local_cache_dir()
        logger.info("Loading fastembed model: %s (cache: %s)", settings.embedding_model, cache_dir)
        try:
            _model = TextEmbedding(model_name=settings.embedding_model, cache_dir=cache_dir)
        except ValueError as exc:
            if "tokenizer_config.json" not in str(exc):
                raise
            logger.warning("fastembed cache appears corrupted — clearing and retrying: %s", exc)
            _clear_fastembed_cache()
            _model = TextEmbedding(model_name=settings.embedding_model, cache_dir=cache_dir)
    return _model


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a list of texts. Returns one vector per text."""
    if not texts:
        return []
    model = _get_model()
    vectors = list(model.embed(texts))
    return [v.tolist() if isinstance(v, np.ndarray) else list(v) for v in vectors]


def embed_single(text: str) -> list[float]:
    """Embed one text string and return its vector."""
    results = embed_texts([text])
    return results[0] if results else []
