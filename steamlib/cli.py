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
from .config import Config, SteamConfig, cache_path, config_path, expand_path, load_config, save_config
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


def _steam_config_from_profile_input(profile_input: str, api_key: str, steam_root: str) -> SteamConfig:
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
    )


@app.command("config")
def configure() -> None:
    """Create or update the Steam Library Manager config."""
    current = load_config()
    profile_default = current.steam.profile_input or current.steam.steamid
    profile_input = Prompt.ask(STEAM_PROFILE_PROMPT, default=profile_default)
    api_key = Prompt.ask("Enter Steam Web API key", default=current.steam.api_key, password=True)
    steam_root = Prompt.ask("Steam root", default=current.steam.steam_root)
    config = Config(
        steam=_steam_config_from_profile_input(profile_input, api_key, steam_root),
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
        config = Config(
            steam=_steam_config_from_profile_input(profile_input, api_key, config.steam.steam_root),
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
) -> None:
    """Install one or more games through Steam."""
    config = load_config()
    queries = queries or []
    if not queries:
        run_tui()
        return
    selected: list[tuple[str, Game]] = []
    for index, query in enumerate(queries, start=1):
        if multi:
            console.print(f"Query {index}/{len(queries)}: {query}")
        game = _choose_match(query, yes=yes, action_name="Install")
        if not game:
            continue
        if game.installed:
            console.print(f"{game.name} is already installed.")
            if skip_installed:
                continue
            if Confirm.ask("Launch it instead?", default=True):
                actions.launch_game(game.appid, config.commands, dry_run=dry_run)
            continue
        selected.append((query, game))
    if not selected:
        console.print("No games selected for install.")
        return
    if dry_run:
        console.print("Would install:")
        for query, game in selected:
            console.print(f"{query} -> {game.name}")
        console.print("No Steam actions were opened.")
        return
    if multi:
        console.print("Selected for install:")
        for index, (_, game) in enumerate(selected, start=1):
            console.print(f"{index}. {game.name}")
        if not yes and not Confirm.ask("Proceed with batch install?", default=True):
            return
    for _, game in selected:
        console.print(f"Opening Steam install prompt for {game.name}...")
        actions.install_game(game.appid, config.commands)
        if multi and not yes:
            answer = Prompt.ask(
                "Press Enter after accepting/queuing it in Steam, S to skip, or Q to stop",
                default="",
                show_default=False,
            )
            if answer.casefold() == "q":
                break


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
