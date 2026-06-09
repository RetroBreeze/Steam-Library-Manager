from steamlib.cache import load_cache, save_cache
from steamlib.models import Game


def test_cache_round_trip(tmp_path) -> None:
    path = tmp_path / "library.json"
    save_cache([Game(appid=620, name="Portal 2", owned=True)], path)
    cache = load_cache(path)
    assert cache is not None
    assert cache.games[0].appid == 620
    assert cache.games[0].name == "Portal 2"

