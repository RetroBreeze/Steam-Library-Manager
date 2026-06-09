from __future__ import annotations

from pathlib import Path
from typing import Any

import vdf

from .models import Game


def _read_vdf(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8", errors="replace") as fh:
        return vdf.load(fh)


def find_library_paths(steam_root: Path) -> list[Path]:
    steam_root = steam_root.expanduser()
    paths = [steam_root]
    config = steam_root / "config" / "libraryfolders.vdf"
    if not config.exists():
        return paths
    try:
        data = _read_vdf(config)
    except Exception:
        return paths
    folders = data.get("libraryfolders", {})
    if not isinstance(folders, dict):
        return paths
    for key, value in folders.items():
        if not str(key).isdigit() or not isinstance(value, dict):
            continue
        raw_path = value.get("path")
        if raw_path:
            path = Path(str(raw_path)).expanduser()
            if path not in paths:
                paths.append(path)
    return paths


def parse_appmanifest(path: Path, library_path: Path | None = None) -> Game | None:
    try:
        data = _read_vdf(path)
    except Exception:
        return None
    app_state = data.get("AppState", {})
    if not isinstance(app_state, dict) or not app_state.get("appid"):
        return None
    appid = int(app_state["appid"])
    name = str(app_state.get("name") or f"App {appid}")
    install_dir_name = str(app_state.get("installdir") or "")
    library = library_path or path.parent.parent
    install_dir = (
        str(library / "steamapps" / "common" / install_dir_name)
        if install_dir_name
        else None
    )
    return Game(
        appid=appid,
        name=name,
        installed=True,
        library_path=str(library),
        install_dir=install_dir,
        size_on_disk=int(app_state["SizeOnDisk"])
        if app_state.get("SizeOnDisk")
        else None,
        last_played=int(app_state["LastUpdated"])
        if app_state.get("LastUpdated")
        else None,
    )


def scan_installed_games(steam_root: Path) -> list[Game]:
    games: list[Game] = []
    for library in find_library_paths(steam_root):
        steamapps = library / "steamapps"
        for manifest in sorted(steamapps.glob("appmanifest_*.acf")):
            game = parse_appmanifest(manifest, library)
            if game:
                games.append(game)
    return games


def merge_games(owned: list[Game], installed: list[Game]) -> list[Game]:
    by_appid = {game.appid: game for game in owned}
    for local in installed:
        existing = by_appid.get(local.appid)
        if existing:
            by_appid[local.appid] = existing.model_copy(
                update={
                    "installed": True,
                    "library_path": local.library_path,
                    "install_dir": local.install_dir,
                    "size_on_disk": local.size_on_disk,
                    "last_played": existing.last_played or local.last_played,
                }
            )
        else:
            by_appid[local.appid] = local
    return sorted(by_appid.values(), key=lambda game: game.name.casefold())

