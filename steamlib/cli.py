from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.table import Table

from . import actions
from .cache import load_cache, require_cache, save_cache
from .config import (
    Config,
    SteamConfig,
    SteamCMDConfig,
    cache_path,
    config_path,
    expand_path,
    load_config,
    save_config,
)
from .local_steam import merge_games, scan_installed_games
from .matcher import Match, is_clear_match, search_games
from .models import Game
from .steam_api import SteamAPIError, fetch_owned_games
from .steam_identity import parse_steam_profile_input, resolve_vanity_url
from .tui import run_tui

app = typer.Typer(help="Steam Library Manager")
console = Console()
STEAM_PROFILE_PROMPT = "Enter your Steam profile URL, custom ID, or SteamID64"


def _cache_games() -> list[Game]:
    try:
        return require_cache().games
    except FileNotFoundError:
        console.print("[red]Owned library cache is unavailable.[/red]")
        console.print("Run: slm config")
        console.print("Then: slm refresh")
        raise typer.Exit(1)


def _format_size(size: int | None) -> str:
    if size is None:
        return "-"
    value = float(size)
    units = ["B", "KB", "MB", "GB", "TB"]
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{value:.1f} TB"


def _format_playtime(minutes: int | None) -> str:
    if not minutes:
        return "-"
    hours, mins = divmod(minutes, 60)
    return f"{hours}h {mins}m"


def _format_date(timestamp: int | None) -> str:
    if not timestamp:
        return "-"
    return datetime.fromtimestamp(timestamp).date().isoformat()


def _game_table(title: str, games: list[Game]) -> Table:
    table = Table(title=title)
    table.add_column("Name")
    table.add_column("AppID", justify="right")
    table.add_column("Installed")
    table.add_column("Playtime", justify="right")
    table.add_column("Size", justify="right")
    for game in games:
        table.add_row(
            game.name,
            str(game.appid),
            "Yes" if game.installed else "No",
            _format_playtime(game.playtime_forever_minutes),
            _format_size(game.size_on_disk),
        )
    return table


def _print_matches(query: str, matches: list[Match], title: str) -> None:
    if not matches:
        console.print(f'[red]No games matched "{query}".[/red]')
        return
    table = Table(title=title)
    table.add_column("#", justify="right")
    table.add_column("Name")
    table.add_column("Installed")
    table.add_column("Score", justify="right")
    for index, match in enumerate(matches, start=1):
        table.add_row(
            str(index),
            match.game.name,
            "Yes" if match.game.installed else "No",
            f"{match.score:.0f}",
        )
    console.print(table)


def _choose_match(
    query: str,
    *,
    installed: bool | None = None,
    yes: bool = False,
    action_name: str = "Use",
) -> Game | None:
    matches = search_games(query, _cache_games(), installed=installed, limit=5)
    if not matches:
        console.print(f'[red]No games matched "{query}".[/red]')
        closest = search_games(query, _cache_games(), installed=installed, limit=3, min_score=0)
        if closest:
            _print_matches(query, closest, "Closest matches")
        return None
    if is_clear_match(matches):
        game = matches[0].game
        if yes:
            return game
        console.print(f"Found: [bold]{game.name}[/bold]")
        console.print(f"AppID: {game.appid}")
        console.print(f"Installed: {'Yes' if game.installed else 'No'}")
        return game if Confirm.ask(f"{action_name} {game.name}?", default=True) else None
    _print_matches(query, matches, "Multiple matches")
    while True:
        answer = Prompt.ask(f"{action_name} which one? [1-{len(matches)}/q]", default="q")
        if answer.casefold() == "q":
            return None
        if answer.isdigit() and 1 <= int(answer) <= len(matches):
            return matches[int(answer) - 1].game


def _steam_config_from_profile_input(
    profile_input: str,
    api_key: str,
    steam_root: str,
    username: str = "",
) -> SteamConfig:
    try:
        parsed = parse_steam_profile_input(profile_input)
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc

    steamid = parsed.value
    if parsed.kind == "custom_id":
        try:
            console.print("Resolving Steam custom profile name...")
            steamid = resolve_vanity_url(parsed.value, api_key)
        except SteamAPIError as exc:
            console.print(f"[red]{exc}[/red]")
            raise typer.Exit(1) from exc

    return SteamConfig(
        steamid=steamid,
        profile_input=profile_input.strip(),
        api_key=api_key,
        steam_root=steam_root,
        username=username,
    )


def _prompt_steamcmd_config(current: Config) -> tuple[str, SteamCMDConfig]:
    username = Prompt.ask("Enter your Steam username for SteamCMD login", default=current.steam.username)
    console.print("Where should SteamCMD install games?")
    console.print("1. ~/SteamCMDLibrary")
    console.print("2. Existing Steam library: ~/.local/share/Steam")
    console.print("3. Custom path")
    choice = Prompt.ask("Choose install location [1-3]", default="1")
    if choice == "2":
        if not Confirm.ask(
            "Using an existing Steam library may work, but SteamCMD installs can behave differently "
            "from Steam client installs. Continue?",
            default=False,
        ):
            install_dir = "~/SteamCMDLibrary"
        else:
            install_dir = current.steam.steam_root or "~/.local/share/Steam"
    elif choice == "3":
        install_dir = Prompt.ask("SteamCMD install directory", default=current.steamcmd.install_dir)
    else:
        install_dir = "~/SteamCMDLibrary"
    return username, SteamCMDConfig(
        command=current.steamcmd.command,
        install_dir=install_dir,
        validate=current.steamcmd.validate,
        force_platform=current.steamcmd.force_platform,
    )


def _steamcmd_missing_message(command: str) -> None:
    console.print("[red]SteamCMD is not installed.[/red]\n")
    console.print("Install it with:")
    console.print("sudo pacman -S steamcmd\n")
    console.print("Or use:")
    console.print("slm install <game> --ui")


def _install_dir_for_game(config: Config, game: Game) -> Path:
    return actions.game_install_dir(expand_path(config.steamcmd.install_dir), game.name)


def _prompt_installed_game_action(game: Game) -> str:
    console.print(f"{game.name} is already installed.\n")
    console.print("Options:")
    console.print("1. Skip")
    console.print("2. Validate with SteamCMD")
    console.print("3. Launch")
    console.print("4. Reinstall")
    answer = Prompt.ask("Choose [1-4]", default="1")
    return {"1": "skip", "2": "validate", "3": "launch", "4": "reinstall"}.get(answer, "skip")


def _resolve_backend(backend: str, ui: bool) -> str:
    if ui:
        return "steam-ui"
    if backend not in {"steamcmd", "steam-ui"}:
        console.print("[red]Backend must be one of: steamcmd, steam-ui[/red]")
        raise typer.Exit(2)
    return backend


def _print_dry_run(queries: list[str]) -> None:
    console.print("Would install with SteamCMD:\n")
    games = _cache_games()
    for query in queries:
        matches = search_games(query, games, limit=3)
        if not matches:
            console.print(f"{query:<10} -> no match")
        elif is_clear_match(matches):
            console.print(f"{query:<10} -> {matches[0].game.name}")
        else:
            names = " / ".join(match.game.name for match in matches)
            console.print(f"{query:<10} -> needs selection: {names}")
    console.print("\nNo SteamCMD commands were run.")


def _run_steamcmd_install(config: Config, game: Game, *, validate: bool | None = None) -> bool:
    install_dir = _install_dir_for_game(config, game)
    console.print(f"Installing {game.name} with SteamCMD...")
    console.print(f"Install directory: {install_dir}")
    console.print("SteamCMD may ask for your Steam password or Steam Guard code.")
    console.print("Credentials are handled by SteamCMD, not stored by slm.")
    result = actions.run_steamcmd_install(
        appid=game.appid,
        install_dir=install_dir,
        username=config.steam.username,
        steamcmd=config.steamcmd,
        validate=validate,
    )
    if result.successful:
        console.print(f"[green]✓ {game.name} installed successfully.[/green]")
        return True
    if result.uncertain:
        console.print(
            "[yellow]? SteamCMD exited successfully, but no installed files were detected. "
            "Check the install directory.[/yellow]"
        )
        return False
    console.print(f"[red]✗ SteamCMD failed with exit code {result.returncode}.[/red]")
    if result.no_subscription:
        console.print(
            "SteamCMD says this account does not own the game, or the depot is not available "
            "through SteamCMD. Install it manually in Steam if you own it."
        )
    return False


def _offer_ui_fallback(game: Game, config: Config, *, yes: bool = False) -> None:
    if yes or Confirm.ask("Open Steam install prompt for this game?", default=True):
        actions.open_steam_install_prompt(game.appid, config.commands)


@app.command("config")
def configure() -> None:
    """Create or update the Steam Library Manager config."""
    current = load_config()
    profile_default = current.steam.profile_input or current.steam.steamid
    profile_input = Prompt.ask(STEAM_PROFILE_PROMPT, default=profile_default)
    api_key = Prompt.ask("Enter Steam Web API key", default=current.steam.api_key, password=True)
    steam_root = Prompt.ask("Steam root", default=current.steam.steam_root)
    username, steamcmd = _prompt_steamcmd_config(current)
    config = Config(
        steam=_steam_config_from_profile_input(profile_input, api_key, steam_root, username),
        steamcmd=steamcmd,
        commands=current.commands,
        ui=current.ui,
    )
    if Confirm.ask(f"Save config to {config_path()}?", default=True):
        path = save_config(config)
        console.print(f"Config saved to {path}")


@app.command()
def refresh() -> None:
    """Fetch owned games, scan local installs, and update the cache."""
    config = load_config()
    if not config.steam.steamid or not config.steam.api_key:
        console.print("Steam Library Manager is not configured.")
        profile_input = Prompt.ask(STEAM_PROFILE_PROMPT)
        api_key = Prompt.ask("Enter Steam Web API key", password=True)
        username, steamcmd = _prompt_steamcmd_config(config)
        config = Config(
            steam=_steam_config_from_profile_input(
                profile_input,
                api_key,
                config.steam.steam_root,
                username,
            ),
            steamcmd=steamcmd,
            commands=config.commands,
            ui=config.ui,
        )
        if Confirm.ask(f"Save config to {config_path()}?", default=True):
            save_config(config)
    try:
        console.print("Fetching owned library...")
        owned = fetch_owned_games(config.steam.steamid, config.steam.api_key)
    except SteamAPIError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1)
    console.print(f"Found {len(owned)} owned games.")
    console.print("Scanning local Steam libraries...")
    installed = scan_installed_games(expand_path(config.steam.steam_root))
    console.print(f"Found {len(installed)} installed games.")
    path = save_cache(merge_games(owned, installed))
    console.print(f"Cache saved to {path}.")


@app.command("search")
def search_command(query: str) -> None:
    """Search owned library cache."""
    matches = search_games(query, _cache_games(), limit=20)
    _print_matches(query, matches, f'Owned games matching "{query}"')


@app.command("list")
def list_games(
    installed: Annotated[bool, typer.Option("--installed")] = False,
    not_installed: Annotated[bool, typer.Option("--not-installed")] = False,
    never_played: Annotated[bool, typer.Option("--never-played")] = False,
    played: Annotated[bool, typer.Option("--played")] = False,
    recent: Annotated[bool, typer.Option("--recent")] = False,
    sort: Annotated[str, typer.Option("--sort")] = "name",
    name: Annotated[str | None, typer.Option("--name")] = None,
) -> None:
    """List cached games."""
    games = _cache_games()
    if installed and not_installed:
        console.print("[red]Use only one of --installed or --not-installed.[/red]")
        raise typer.Exit(2)
    if installed:
        games = [game for game in games if game.installed]
    if not_installed:
        games = [game for game in games if not game.installed]
    if never_played:
        games = [game for game in games if not game.playtime_forever_minutes]
    if played:
        games = [game for game in games if (game.playtime_forever_minutes or 0) > 0]
    if name:
        games = [match.game for match in search_games(name, games, limit=100)]
    if recent:
        sort = "last-played"
    sorters = {
        "name": lambda game: game.name.casefold(),
        "playtime": lambda game: -(game.playtime_forever_minutes or 0),
        "last-played": lambda game: -(game.last_played or 0),
        "size": lambda game: -(game.size_on_disk or 0),
    }
    if sort not in sorters:
        console.print("[red]Sort must be one of: name, playtime, last-played, size[/red]")
        raise typer.Exit(2)
    games = sorted(games, key=sorters[sort])
    console.print(_game_table("Steam Library", games))


@app.command()
def installed() -> None:
    """List installed games."""
    games = [game for game in _cache_games() if game.installed]
    console.print(_game_table("Installed Steam Games", games))


@app.command()
def install(
    queries: Annotated[list[str] | None, typer.Argument()] = None,
    multi: Annotated[bool, typer.Option("--multi", "-m")] = False,
    yes: Annotated[bool, typer.Option("--yes", "-y")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
    skip_installed: Annotated[bool, typer.Option("--skip-installed")] = False,
    ui: Annotated[bool, typer.Option("--ui", help="Use the Steam UI install prompt instead of SteamCMD.")] = False,
    backend: Annotated[str, typer.Option("--backend")] = "steamcmd",
    validate: Annotated[bool, typer.Option("--validate")] = False,
    reinstall: Annotated[bool, typer.Option("--reinstall")] = False,
) -> None:
    """Install one or more games with SteamCMD by default."""
    config = load_config()
    queries = queries or []
    if not queries:
        run_tui()
        return
    selected_backend = _resolve_backend(backend, ui)
    if dry_run and multi and selected_backend == "steamcmd":
        _print_dry_run(queries)
        return
    if selected_backend == "steamcmd":
        if not config.steam.username:
            console.print("[red]SteamCMD username is not configured.[/red]")
            console.print("Run: slm config")
            raise typer.Exit(1)
        if not dry_run and not actions.steamcmd_available(config.steamcmd):
            _steamcmd_missing_message(config.steamcmd.command)
            raise typer.Exit(1)
    selected: list[tuple[str, Game, bool | None]] = []
    for index, query in enumerate(queries, start=1):
        if multi:
            console.print(f"Query {index}/{len(queries)}: {query}")
        game = _choose_match(query, yes=yes, action_name="Install")
        if not game:
            continue
        if game.installed:
            if skip_installed:
                console.print(f"{game.name} is already installed. Skipping.")
                continue
            if validate:
                selected.append((query, game, True))
                continue
            if reinstall:
                selected.append((query, game, True if validate else config.steamcmd.validate))
                continue
            action = _prompt_installed_game_action(game)
            if action == "launch":
                actions.launch_game(game.appid, config.commands, dry_run=dry_run)
            elif action == "validate":
                selected.append((query, game, True))
            elif action == "reinstall":
                selected.append((query, game, True if validate else config.steamcmd.validate))
            continue
        selected.append((query, game, True if validate else config.steamcmd.validate))
    if not selected:
        console.print("No games selected for install.")
        return
    if dry_run:
        verb = "open Steam install prompt for" if selected_backend == "steam-ui" else "install with SteamCMD"
        console.print(f"Would {verb}:")
        for query, game, _ in selected:
            console.print(f"{query} -> {game.name}")
        console.print(
            "No Steam UI prompts were opened."
            if selected_backend == "steam-ui"
            else "No SteamCMD commands were run."
        )
        return
    if selected_backend == "steam-ui":
        for _, game, _ in selected:
            console.print(f"Opening Steam install prompt for {game.name}...")
            actions.open_steam_install_prompt(game.appid, config.commands)
        return
    if multi:
        console.print("Selected for automatic SteamCMD install:")
        for index, (_, game, _) in enumerate(selected, start=1):
            console.print(f"{index}. {game.name}")
        if not yes and not Confirm.ask(f"Install these {len(selected)} games with SteamCMD?", default=True):
            return
    elif not yes and not Confirm.ask(
        f"Install automatically with SteamCMD?", default=True
    ):
        return
    failed: list[Game] = []
    for index, (_, game, validate_choice) in enumerate(selected, start=1):
        if multi:
            console.print(f"Installing {index}/{len(selected)}: {game.name}")
        if not _run_steamcmd_install(config, game, validate=validate_choice):
            failed.append(game)
            if not multi:
                console.print(f"[red]✗ SteamCMD install failed for {game.name}.[/red]")
                _offer_ui_fallback(game, config, yes=yes)
    if multi:
        console.print("\nInstall summary:\n")
        for _, game, _ in selected:
            marker = "✗" if game in failed else "✓"
            console.print(f"{marker} {game.name}")
        if failed:
            noun = "game" if len(failed) == 1 else "games"
            console.print(f"\n{len(failed)} {noun} failed. Failed games can be installed manually in Steam.")
            if yes or Confirm.ask("Open Steam install prompts for failed games?", default=True):
                for game in failed:
                    actions.open_steam_install_prompt(game.appid, config.commands)


@app.command()
def uninstall(
    queries: Annotated[list[str] | None, typer.Argument()] = None,
    multi: Annotated[bool, typer.Option("--multi", "-m")] = False,
    yes: Annotated[bool, typer.Option("--yes", "-y")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
) -> None:
    """Uninstall installed games through Steam. Never deletes files directly."""
    config = load_config()
    queries = queries or []
    if not queries:
        run_tui()
        return
    selected: list[Game] = []
    for query in queries:
        game = _choose_match(query, installed=True, yes=False, action_name="Uninstall")
        if game:
            console.print(f"Size: {_format_size(game.size_on_disk)}")
            if yes or Confirm.ask(f"Uninstall {game.name} using Steam?", default=False):
                selected.append(game)
    if not selected:
        console.print("No games selected for uninstall.")
        return
    total = sum(game.size_on_disk or 0 for game in selected)
    console.print(
        f"Uninstall {len(selected)} games and free approximately {_format_size(total)}?"
    )
    for index, game in enumerate(selected, start=1):
        console.print(f"{index}. {game.name}    {_format_size(game.size_on_disk)}")
    if dry_run:
        console.print("No Steam actions were opened.")
        return
    if not Confirm.ask("Proceed?", default=False):
        return
    for game in selected:
        actions.uninstall_game(game.appid, config.commands)
        if multi and not yes:
            answer = Prompt.ask(
                "Press Enter after accepting it in Steam, S to skip, or Q to stop",
                default="",
                show_default=False,
            )
            if answer.casefold() == "q":
                break


@app.command()
def launch(query: str, dry_run: Annotated[bool, typer.Option("--dry-run")] = False) -> None:
    """Launch a game by fuzzy name."""
    game = _choose_match(query, yes=True, action_name="Launch")
    if not game:
        raise typer.Exit(1)
    actions.launch_game(game.appid, load_config().commands, dry_run=dry_run)
    console.print(f"Launching {game.name}...")


@app.command()
def details(query: str) -> None:
    """Show details for a game."""
    game = _choose_match(query, yes=True, action_name="Show details for")
    if not game:
        raise typer.Exit(1)
    console.print(f"[bold]{game.name}[/bold]")
    console.print(f"AppID: {game.appid}")
    console.print(f"Installed: {'Yes' if game.installed else 'No'}")
    console.print(f"Library: {game.library_path or '-'}")
    console.print(f"Install path: {game.install_dir or '-'}")
    console.print(f"Size: {_format_size(game.size_on_disk)}")
    console.print(f"Playtime: {_format_playtime(game.playtime_forever_minutes)}")
    console.print(f"Last played: {_format_date(game.last_played)}")


@app.command()
def tui() -> None:
    """Open the interactive library browser."""
    run_tui()


def main() -> None:
    app()


if __name__ == "__main__":
    main()
