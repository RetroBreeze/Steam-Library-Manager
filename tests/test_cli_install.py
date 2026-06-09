from pathlib import Path

from typer.testing import CliRunner

from steamlib import cli
from steamlib.actions import SteamCMDInstallResult
from steamlib.config import Config, SteamConfig, SteamCMDConfig
from steamlib.models import Game


runner = CliRunner()


def _config(tmp_path: Path) -> Config:
    return Config(
        steam=SteamConfig(username="testuser"),
        steamcmd=SteamCMDConfig(install_dir=str(tmp_path), validate=True),
    )


def test_single_install_uses_steamcmd_by_default(monkeypatch, tmp_path: Path) -> None:
    calls = []
    monkeypatch.setattr(cli, "load_config", lambda: _config(tmp_path))
    monkeypatch.setattr(cli, "_cache_games", lambda: [Game(appid=620, name="Portal 2")])
    monkeypatch.setattr(cli.actions, "steamcmd_available", lambda config: True)

    def fake_install(appid, install_dir, username, steamcmd, validate=None, dry_run=False):
        calls.append((appid, install_dir, username, validate))
        return SteamCMDInstallResult(0, install_dir, True, False)

    monkeypatch.setattr(cli.actions, "run_steamcmd_install", fake_install)

    result = runner.invoke(cli.app, ["install", "portal", "--yes"])

    assert result.exit_code == 0
    assert calls == [(620, tmp_path / "Portal 2", "testuser", True)]


def test_single_install_with_ui_uses_steam_protocol(monkeypatch, tmp_path: Path) -> None:
    calls = []
    monkeypatch.setattr(cli, "load_config", lambda: _config(tmp_path))
    monkeypatch.setattr(cli, "_cache_games", lambda: [Game(appid=620, name="Portal 2")])
    monkeypatch.setattr(
        cli.actions,
        "open_steam_install_prompt",
        lambda appid, config: calls.append(appid),
    )

    result = runner.invoke(cli.app, ["install", "portal", "--yes", "--ui"])

    assert result.exit_code == 0
    assert calls == [620]


def test_multi_install_runs_steamcmd_sequentially(monkeypatch, tmp_path: Path) -> None:
    games = [
        Game(appid=1, name="Alpha Game"),
        Game(appid=2, name="Beta Game"),
        Game(appid=3, name="Gamma Game"),
    ]
    calls = []
    monkeypatch.setattr(cli, "load_config", lambda: _config(tmp_path))
    monkeypatch.setattr(cli, "_cache_games", lambda: games)
    monkeypatch.setattr(cli.actions, "steamcmd_available", lambda config: True)

    def fake_install(appid, install_dir, username, steamcmd, validate=None, dry_run=False):
        calls.append(appid)
        return SteamCMDInstallResult(0, install_dir, True, False)

    monkeypatch.setattr(cli.actions, "run_steamcmd_install", fake_install)

    result = runner.invoke(cli.app, ["install", "-m", "alpha", "beta", "gamma", "--yes"])

    assert result.exit_code == 0
    assert calls == [1, 2, 3]


def test_failed_steamcmd_install_offers_steam_ui_fallback(monkeypatch, tmp_path: Path) -> None:
    ui_calls = []
    monkeypatch.setattr(cli, "load_config", lambda: _config(tmp_path))
    monkeypatch.setattr(cli, "_cache_games", lambda: [Game(appid=620, name="Portal 2")])
    monkeypatch.setattr(cli.actions, "steamcmd_available", lambda config: True)
    monkeypatch.setattr(
        cli.actions,
        "run_steamcmd_install",
        lambda appid, install_dir, username, steamcmd, validate=None, dry_run=False: (
            SteamCMDInstallResult(8, install_dir, False, False)
        ),
    )
    monkeypatch.setattr(
        cli.actions,
        "open_steam_install_prompt",
        lambda appid, config: ui_calls.append(appid),
    )

    result = runner.invoke(cli.app, ["install", "portal", "--yes"])

    assert result.exit_code == 0
    assert ui_calls == [620]


def test_missing_steamcmd_stops_before_install(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(cli, "load_config", lambda: _config(tmp_path))
    monkeypatch.setattr(cli, "_cache_games", lambda: [Game(appid=620, name="Portal 2")])
    monkeypatch.setattr(cli.actions, "steamcmd_available", lambda config: False)

    result = runner.invoke(cli.app, ["install", "portal", "--yes"])

    assert result.exit_code == 1
    assert "SteamCMD is not installed" in result.output
    assert "slm install <game> --ui" in result.output


def test_multi_dry_run_resolves_each_query_without_installing(monkeypatch, tmp_path: Path) -> None:
    games = [
        Game(appid=1, name="007 First Light"),
        Game(appid=2, name="Halo: The Master Chief Collection"),
        Game(appid=3, name="Halo: Spartan Assault"),
        Game(appid=4, name="Halo: Spartan Strike"),
    ]
    monkeypatch.setattr(cli, "load_config", lambda: _config(tmp_path))
    monkeypatch.setattr(cli, "_cache_games", lambda: games)

    result = runner.invoke(cli.app, ["install", "-m", "--dry-run", "007", "halo"])

    assert result.exit_code == 0
    assert "007" in result.output
    assert "007 First Light" in result.output
    assert "halo" in result.output
    assert "needs selection" in result.output
    assert "No SteamCMD commands were run." in result.output
