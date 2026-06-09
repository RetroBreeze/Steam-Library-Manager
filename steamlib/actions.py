from __future__ import annotations

import shutil
import subprocess

from .config import CommandsConfig


class ActionError(RuntimeError):
    pass


def ensure_command(command: str) -> None:
    if shutil.which(command) is None:
        raise ActionError(f"{command} does not appear to be installed or could not be found.")


def run_command(args: list[str], *, dry_run: bool = False) -> None:
    if dry_run:
        return
    ensure_command(args[0])
    subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def open_url(url: str, config: CommandsConfig, *, dry_run: bool = False) -> None:
    run_command([config.open_command, url], dry_run=dry_run)


def install_game(appid: int, config: CommandsConfig, *, dry_run: bool = False) -> None:
    open_url(f"steam://install/{appid}", config, dry_run=dry_run)


def uninstall_game(appid: int, config: CommandsConfig, *, dry_run: bool = False) -> None:
    open_url(f"steam://uninstall/{appid}", config, dry_run=dry_run)


def open_game_details(appid: int, config: CommandsConfig, *, dry_run: bool = False) -> None:
    open_url(f"steam://nav/games/details/{appid}", config, dry_run=dry_run)


def launch_game(appid: int, config: CommandsConfig, *, dry_run: bool = False) -> None:
    run_command([config.steam_command, "-applaunch", str(appid)], dry_run=dry_run)

