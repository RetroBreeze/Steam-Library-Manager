from __future__ import annotations

import json
import os
import stat
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from platformdirs import user_cache_dir, user_config_dir

APP_NAME = "steam-library-manager"


@dataclass(frozen=True)
class SteamConfig:
    steamid: str = ""
    profile_input: str = ""
    api_key: str = ""
    steam_root: str = "~/.local/share/Steam"
    username: str = ""


@dataclass(frozen=True)
class SteamCMDConfig:
    command: str = "steamcmd"
    install_dir: str = "~/SteamCMDLibrary"
    validate: bool = True
    force_platform: str = ""


@dataclass(frozen=True)
class CommandsConfig:
    steam_command: str = "steam"
    open_command: str = "xdg-open"


@dataclass(frozen=True)
class UIConfig:
    default_sort: str = "name"
    confirm_installs: bool = True
    confirm_uninstalls: bool = True


@dataclass(frozen=True)
class Config:
    steam: SteamConfig = SteamConfig()
    steamcmd: SteamCMDConfig = SteamCMDConfig()
    commands: CommandsConfig = CommandsConfig()
    ui: UIConfig = UIConfig()


def config_path() -> Path:
    return Path(user_config_dir(APP_NAME)) / "config.toml"


def cache_path() -> Path:
    return Path(user_cache_dir(APP_NAME)) / "library.json"


def _section(data: dict[str, Any], name: str) -> dict[str, Any]:
    value = data.get(name)
    return value if isinstance(value, dict) else {}


def load_config(path: Path | None = None) -> Config:
    path = path or config_path()
    if not path.exists():
        return Config()
    with path.open("rb") as fh:
        data = tomllib.load(fh)
    steam = _section(data, "steam")
    steamcmd = _section(data, "steamcmd")
    commands = _section(data, "commands")
    ui = _section(data, "ui")
    return Config(
        steam=SteamConfig(
            steamid=str(steam.get("steamid", "")),
            profile_input=str(steam.get("profile_input", "")),
            api_key=str(steam.get("api_key", "")),
            steam_root=str(steam.get("steam_root", "~/.local/share/Steam")),
            username=str(steam.get("username", "")),
        ),
        steamcmd=SteamCMDConfig(
            command=str(steamcmd.get("command", "steamcmd")),
            install_dir=str(steamcmd.get("install_dir", "~/SteamCMDLibrary")),
            validate=bool(steamcmd.get("validate", True)),
            force_platform=str(steamcmd.get("force_platform", "")),
        ),
        commands=CommandsConfig(
            steam_command=str(commands.get("steam_command", "steam")),
            open_command=str(commands.get("open_command", "xdg-open")),
        ),
        ui=UIConfig(
            default_sort=str(ui.get("default_sort", "name")),
            confirm_installs=bool(ui.get("confirm_installs", True)),
            confirm_uninstalls=bool(ui.get("confirm_uninstalls", True)),
        ),
    )


def save_config(config: Config, path: Path | None = None) -> Path:
    path = path or config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    content = (
        "[steam]\n"
        f"steamid = {_toml_string(config.steam.steamid)}\n"
        f"profile_input = {_toml_string(config.steam.profile_input)}\n"
        f"api_key = {_toml_string(config.steam.api_key)}\n"
        f"steam_root = {_toml_string(config.steam.steam_root)}\n"
        f"username = {_toml_string(config.steam.username)}\n\n"
        "[steamcmd]\n"
        f"command = {_toml_string(config.steamcmd.command)}\n"
        f"install_dir = {_toml_string(config.steamcmd.install_dir)}\n"
        f"validate = {str(config.steamcmd.validate).lower()}\n"
        f"force_platform = {_toml_string(config.steamcmd.force_platform)}\n\n"
        "[commands]\n"
        f"steam_command = {_toml_string(config.commands.steam_command)}\n"
        f"open_command = {_toml_string(config.commands.open_command)}\n\n"
        "[ui]\n"
        f"default_sort = {_toml_string(config.ui.default_sort)}\n"
        f"confirm_installs = {str(config.ui.confirm_installs).lower()}\n"
        f"confirm_uninstalls = {str(config.ui.confirm_uninstalls).lower()}\n"
    )
    path.write_text(content, encoding="utf-8")
    os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    return path


def _toml_string(value: str) -> str:
    return json.dumps(value)


def expand_path(path: str) -> Path:
    return Path(path).expanduser()
