from pathlib import Path

from steamlib.local_steam import find_library_paths, merge_games, parse_appmanifest
from steamlib.models import Game


def test_parse_appmanifest(tmp_path: Path) -> None:
    library = tmp_path / "SteamLibrary"
    steamapps = library / "steamapps"
    steamapps.mkdir(parents=True)
    manifest = steamapps / "appmanifest_620.acf"
    manifest.write_text(
        '"AppState"\n'
        "{\n"
        '  "appid" "620"\n'
        '  "name" "Portal 2"\n'
        '  "installdir" "Portal 2"\n'
        '  "SizeOnDisk" "1234"\n'
        '  "LastUpdated" "1700000000"\n'
        "}\n",
        encoding="utf-8",
    )
    game = parse_appmanifest(manifest, library)
    assert game is not None
    assert game.appid == 620
    assert game.installed is True
    assert game.install_dir == str(library / "steamapps" / "common" / "Portal 2")


def test_find_library_paths_includes_configured_libraries(tmp_path: Path) -> None:
    steam_root = tmp_path / "Steam"
    extra = tmp_path / "ExtraLibrary"
    (steam_root / "config").mkdir(parents=True)
    (steam_root / "config" / "libraryfolders.vdf").write_text(
        '"libraryfolders"\n'
        "{\n"
        '  "0"\n'
        "  {\n"
        f'    "path" "{steam_root}"\n'
        "  }\n"
        '  "1"\n'
        "  {\n"
        f'    "path" "{extra}"\n'
        "  }\n"
        "}\n",
        encoding="utf-8",
    )
    assert find_library_paths(steam_root) == [steam_root, extra]


def test_merge_games_marks_owned_game_installed() -> None:
    merged = merge_games(
        [Game(appid=620, name="Portal 2", owned=True)],
        [Game(appid=620, name="Portal 2", installed=True, size_on_disk=10)],
    )
    assert merged[0].owned is True
    assert merged[0].installed is True
    assert merged[0].size_on_disk == 10

