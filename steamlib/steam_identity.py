from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse

import requests

from .steam_api import SteamAPIError

RESOLVE_VANITY_URL = "https://api.steampowered.com/ISteamUser/ResolveVanityURL/v1/"
STEAMID64_RE = re.compile(r"^7656\d{13}$")
VANITY_RESOLUTION_ERROR = (
    "Could not resolve that Steam custom profile name. Check the spelling or paste your full Steam profile URL."
)


@dataclass(frozen=True)
class SteamProfileInput:
    kind: str
    value: str
    source_kind: str
    original: str


def parse_steam_profile_input(value: str) -> SteamProfileInput:
    original = value
    value = value.strip()
    if not value:
        raise ValueError("Enter your Steam profile URL, custom ID, or SteamID64.")

    if STEAMID64_RE.fullmatch(value):
        return SteamProfileInput(
            kind="steamid64",
            value=value,
            source_kind="steamid64",
            original=original,
        )

    parsed = urlparse(value)
    if parsed.scheme or parsed.netloc:
        return _parse_steam_profile_url(value, original)

    if any(char.isspace() for char in value):
        raise ValueError("Steam custom profile names cannot contain whitespace.")

    return SteamProfileInput(
        kind="custom_id",
        value=value,
        source_kind="custom_id",
        original=original,
    )


def _parse_steam_profile_url(value: str, original: str) -> SteamProfileInput:
    parsed = urlparse(value)
    host = parsed.netloc.casefold()
    if parsed.scheme != "https" or host not in {"steamcommunity.com", "www.steamcommunity.com"}:
        raise ValueError(
            "Unsupported Steam profile URL. Paste a steamcommunity.com profile URL, custom ID, or SteamID64."
        )

    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) == 2 and parts[0] == "profiles" and STEAMID64_RE.fullmatch(parts[1]):
        return SteamProfileInput(
            kind="steamid64",
            value=parts[1],
            source_kind="profile_url_numeric",
            original=original,
        )
    if len(parts) == 2 and parts[0] == "id" and parts[1]:
        return SteamProfileInput(
            kind="custom_id",
            value=parts[1],
            source_kind="profile_url_custom",
            original=original,
        )

    raise ValueError(
        "Unsupported Steam profile URL. Use /profiles/<SteamID64> or /id/<custom-name>."
    )


def resolve_vanity_url(custom_id: str, api_key: str, timeout: int = 30) -> str:
    if not custom_id or not api_key:
        raise SteamAPIError(VANITY_RESOLUTION_ERROR)

    try:
        response = requests.get(
            RESOLVE_VANITY_URL,
            params={"key": api_key, "vanityurl": custom_id},
            timeout=timeout,
        )
    except requests.RequestException as exc:
        raise SteamAPIError(VANITY_RESOLUTION_ERROR) from exc
    if response.status_code != 200:
        raise SteamAPIError(VANITY_RESOLUTION_ERROR)

    try:
        payload = response.json()
    except ValueError as exc:
        raise SteamAPIError(VANITY_RESOLUTION_ERROR) from exc
    data = payload.get("response", {})
    steamid = data.get("steamid")
    if data.get("success") != 1 or not steamid:
        raise SteamAPIError(VANITY_RESOLUTION_ERROR)
    return str(steamid)
