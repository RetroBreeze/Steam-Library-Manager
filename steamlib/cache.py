from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from .config import cache_path
from .models import Game, LibraryCache


def load_cache(path: Path | None = None) -> LibraryCache | None:
    path = path or cache_path()
    if not path.exists():
        return None
    return LibraryCache.model_validate_json(path.read_text(encoding="utf-8"))


def save_cache(games: list[Game], path: Path | None = None) -> Path:
    path = path or cache_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    cache = LibraryCache(last_refresh=datetime.now(timezone.utc), games=games)
    path.write_text(cache.model_dump_json(indent=2), encoding="utf-8")
    return path


def require_cache(path: Path | None = None) -> LibraryCache:
    cache = load_cache(path)
    if cache is None:
        raise FileNotFoundError("Owned library cache is unavailable.")
    return cache

