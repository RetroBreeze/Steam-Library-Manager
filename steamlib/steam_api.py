from __future__ import annotations

import requests

from .models import Game

OWNED_GAMES_URL = "https://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/"


class SteamAPIError(RuntimeError):
    pass


def fetch_owned_games(steamid: str, api_key: str, timeout: int = 30) -> list[Game]:
    if not steamid or not api_key:
        raise SteamAPIError("Steam profile configuration and Steam Web API key are required.")
    response = requests.get(
        OWNED_GAMES_URL,
        params={
            "key": api_key,
            "steamid": steamid,
            "format": "json",
            "include_appinfo": "true",
            "include_played_free_games": "true",
        },
        timeout=timeout,
    )
    if response.status_code != 200:
        raise SteamAPIError(f"Steam API returned HTTP {response.status_code}.")
    payload = response.json()
    games = payload.get("response", {}).get("games", [])
    result: list[Game] = []
    for item in games:
        appid = int(item["appid"])
        icon_hash = item.get("img_icon_url") or None
        icon_url = (
            f"https://cdn.cloudflare.steamstatic.com/steamcommunity/public/images/apps/{appid}/{icon_hash}.jpg"
            if icon_hash
            else None
        )
        result.append(
            Game(
                appid=appid,
                name=str(item.get("name") or f"App {appid}"),
                owned=True,
                playtime_forever_minutes=int(item.get("playtime_forever", 0)),
                last_played=int(item["rtime_last_played"])
                if item.get("rtime_last_played")
                else None,
                icon_url=icon_url,
            )
        )
    return result
