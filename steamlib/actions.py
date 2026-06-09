from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .config import CommandsConfig, SteamCMDConfig


class ActionError(RuntimeError):
    pass


@dataclass(frozen=True)
class SteamCMDInstallResult:
    returncode: int
    install_dir: Path
    files_found: bool
    manifest_found: bool
    output: str = ""

    @property
    def successful(self) -> bool:
        return self.returncode == 0 and self.files_found

    @property
    def uncertain(self) -> bool:
        return self.returncode == 0 and not self.files_found

    @property
    def no_subscription(self) -> bool:
        return "no subscription" in self.output.casefold()


def ensure_command(command: str) -> None:
    if shutil.which(command) is None:
        raise ActionError(f"{command} does not appear to be installed or could not be found.")


def command_exists(command: str) -> bool:
    return shutil.which(command) is not None


def run_command(args: list[str], *, dry_run: bool = False) -> None:
    if dry_run:
        return
    ensure_command(args[0])
    subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def open_url(url: str, config: CommandsConfig, *, dry_run: bool = False) -> None:
    run_command([config.open_command, url], dry_run=dry_run)


def build_steam_install_url(appid: int) -> str:
    return f"steam://install/{appid}"


def open_steam_install_prompt(appid: int, config: CommandsConfig, *, dry_run: bool = False) -> None:
    open_url(build_steam_install_url(appid), config, dry_run=dry_run)


def install_game(appid: int, config: CommandsConfig, *, dry_run: bool = False) -> None:
    open_steam_install_prompt(appid, config, dry_run=dry_run)


def sanitise_install_dir_name(name: str) -> str:
    cleaned = "".join(" " if char in '/\\:*?"<>|' else char for char in name)
    return " ".join(cleaned.split()).strip() or "Steam Game"


def game_install_dir(base_install_dir: Path, game_name: str) -> Path:
    return base_install_dir / sanitise_install_dir_name(game_name)


def build_steamcmd_install_command(
    appid: int,
    install_dir: Path,
    username: str,
    validate: bool = True,
    force_platform: str | None = None,
    command: str = "steamcmd",
) -> list[str]:
    cmd = [command, "+force_install_dir", str(install_dir)]
    if force_platform:
        cmd.extend(["+@sSteamCmdForcePlatformType", force_platform])
    cmd.extend(["+login", username, "+app_update", str(appid)])
    if validate:
        cmd.append("validate")
    cmd.append("+quit")
    return cmd


def steamcmd_available(config: SteamCMDConfig) -> bool:
    return command_exists(config.command)


def _installed_files_found(install_dir: Path) -> bool:
    if not install_dir.exists():
        return False
    return any(path.is_file() for path in install_dir.rglob("*"))


def _appmanifest_found(appid: int, install_dir: Path) -> bool:
    return any(install_dir.rglob(f"appmanifest_{appid}.acf"))


def run_steamcmd_install(
    appid: int,
    install_dir: Path,
    username: str,
    steamcmd: SteamCMDConfig,
    *,
    validate: bool | None = None,
    dry_run: bool = False,
) -> SteamCMDInstallResult:
    if dry_run:
        return SteamCMDInstallResult(0, install_dir, False, False)
    ensure_command(steamcmd.command)
    install_dir.mkdir(parents=True, exist_ok=True)
    cmd = build_steamcmd_install_command(
        appid=appid,
        install_dir=install_dir,
        username=username,
        validate=steamcmd.validate if validate is None else validate,
        force_platform=steamcmd.force_platform or None,
        command=steamcmd.command,
    )
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    output: list[str] = []
    assert process.stdout is not None
    while True:
        chunk = process.stdout.read(1)
        if not chunk:
            break
        print(chunk, end="", flush=True)
        output.append(chunk)
    returncode = process.wait()
    text = "".join(output)
    return SteamCMDInstallResult(
        returncode=returncode,
        install_dir=install_dir,
        files_found=_installed_files_found(install_dir),
        manifest_found=_appmanifest_found(appid, install_dir),
        output=text,
    )


def uninstall_game(appid: int, config: CommandsConfig, *, dry_run: bool = False) -> None:
    open_url(f"steam://uninstall/{appid}", config, dry_run=dry_run)


def open_game_details(appid: int, config: CommandsConfig, *, dry_run: bool = False) -> None:
    open_url(f"steam://nav/games/details/{appid}", config, dry_run=dry_run)


def launch_game(appid: int, config: CommandsConfig, *, dry_run: bool = False) -> None:
    run_command([config.steam_command, "-applaunch", str(appid)], dry_run=dry_run)
