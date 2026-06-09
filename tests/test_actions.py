from steamlib import actions
from steamlib.config import CommandsConfig


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

