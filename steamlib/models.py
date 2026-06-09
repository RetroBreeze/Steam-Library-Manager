from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class Game(BaseModel):
    appid: int
    name: str
    owned: bool = False
    installed: bool = False
    library_path: str | None = None
    install_dir: str | None = None
    size_on_disk: int | None = None
    playtime_forever_minutes: int | None = None
    last_played: int | None = None
    icon_url: str | None = None


class LibraryCache(BaseModel):
    last_refresh: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    games: list[Game] = Field(default_factory=list)

