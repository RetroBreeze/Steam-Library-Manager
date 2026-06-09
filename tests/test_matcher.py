from steamlib.matcher import is_clear_match, normalize, search_games
from steamlib.models import Game


def test_normalize_keeps_numbers_and_strips_punctuation() -> None:
    assert normalize("  Portal: 2!!! ") == "portal 2"
    assert normalize("007 First-Light") == "007 first light"


def test_search_prefers_exact_name() -> None:
    games = [
        Game(appid=1, name="Portal"),
        Game(appid=2, name="Portal 2"),
        Game(appid=3, name="Portal Stories: Mel"),
    ]
    matches = search_games("portal 2", games)
    assert matches[0].game.appid == 2
    assert is_clear_match(matches)


def test_ambiguous_short_query_is_not_clear() -> None:
    games = [
        Game(appid=1, name="Halo: The Master Chief Collection"),
        Game(appid=2, name="Halo: Spartan Assault"),
        Game(appid=3, name="Halo: Spartan Strike"),
    ]
    matches = search_games("halo", games)
    assert len(matches) == 3
    assert not is_clear_match(matches)


def test_installed_filter() -> None:
    games = [
        Game(appid=1, name="Installed Game", installed=True),
        Game(appid=2, name="Other Game", installed=False),
    ]
    assert [m.game.appid for m in search_games("game", games, installed=True)] == [1]

