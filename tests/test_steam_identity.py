import pytest

from steamlib.steam_identity import parse_steam_profile_input


def test_parse_steamid64() -> None:
    result = parse_steam_profile_input("76561198012345678")
    assert result.kind == "steamid64"
    assert result.source_kind == "steamid64"
    assert result.value == "76561198012345678"


def test_parse_numeric_profile_url() -> None:
    result = parse_steam_profile_input("https://steamcommunity.com/profiles/76561198012345678")
    assert result.kind == "steamid64"
    assert result.source_kind == "profile_url_numeric"
    assert result.value == "76561198012345678"


def test_parse_custom_profile_url() -> None:
    result = parse_steam_profile_input("https://steamcommunity.com/id/retrobreeze")
    assert result.kind == "custom_id"
    assert result.source_kind == "profile_url_custom"
    assert result.value == "retrobreeze"


def test_parse_plain_custom_id() -> None:
    result = parse_steam_profile_input("retrobreeze")
    assert result.kind == "custom_id"
    assert result.source_kind == "custom_id"
    assert result.value == "retrobreeze"


def test_empty_rejected() -> None:
    with pytest.raises(ValueError):
        parse_steam_profile_input("")


def test_unsupported_steam_url_rejected() -> None:
    with pytest.raises(ValueError):
        parse_steam_profile_input("https://steamcommunity.com/app/620")
