from pathlib import Path

from steamlib import actions
from steamlib.config import CommandsConfig, SteamCMDConfig


def test_install_uses_steam_protocol(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(actions, "run_command", lambda args, dry_run=False: calls.append(args))
    actions.install_game(620, CommandsConfig(open_command="xdg-open"))
    assert calls == [["xdg-open", "steam://install/620"]]


def test_launch_uses_steam_command(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(actions, "run_command", lambda args, dry_run=False: calls.append(args))
    actions.launch_game(620, CommandsConfig(steam_command="steam"))
    assert calls == [["steam", "-applaunch", "620"]]


def test_build_steamcmd_command_basic() -> None:
    cmd = actions.build_steamcmd_install_command(
        appid=620,
        install_dir=Path("/home/user/SteamCMDLibrary/Portal 2"),
        username="testuser",
        validate=True,
    )
    assert cmd == [
        "steamcmd",
        "+force_install_dir",
        "/home/user/SteamCMDLibrary/Portal 2",
        "+login",
        "testuser",
        "+app_update",
        "620",
        "validate",
        "+quit",
    ]


def test_build_steamcmd_command_no_validate() -> None:
    cmd = actions.build_steamcmd_install_command(
        appid=620,
        install_dir=Path("/tmp/Portal 2"),
        username="testuser",
        validate=False,
    )
    assert "validate" not in cmd


def test_build_steamcmd_command_with_force_platform() -> None:
    cmd = actions.build_steamcmd_install_command(
        appid=620,
        install_dir=Path("/tmp/Portal 2"),
        username="testuser",
        force_platform="windows",
    )
    assert cmd[3:5] == ["+@sSteamCmdForcePlatformType", "windows"]
    assert cmd.index("+@sSteamCmdForcePlatformType") < cmd.index("+login")


def test_sanitise_game_install_name() -> None:
    assert (
        actions.sanitise_install_dir_name('Halo: The/Master*Chief? Collection')
        == "Halo The Master Chief Collection"
    )


def test_ui_backend_uses_steam_protocol() -> None:
    assert actions.build_steam_install_url(620) == "steam://install/620"


def test_detect_missing_steamcmd(monkeypatch) -> None:
    monkeypatch.setattr(actions.shutil, "which", lambda command: None)
    assert actions.steamcmd_available(SteamCMDConfig(command="steamcmd")) is False
