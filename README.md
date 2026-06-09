# Steam Library Manager

Search, install, launch, and uninstall Steam games from your terminal.

```bash
slm install 007
slm install halo
slm install -m 007 halo sonic
slm search "final fantasy"
slm list --installed
slm uninstall
slm launch portal
```

## What is it?

**Steam Library Manager** is a Linux command-line tool for managing your Steam library by game name.

Steam can already install games by AppID, but AppIDs are annoying to look up. This tool lets you use the names you actually remember:

```bash
slm install "portal 2"
```

Instead of:

```bash
xdg-open "steam://install/620"
```

The main command is:

```bash
steamlib
```

The short command is:

```bash
slm
```

## What can it do?

* Search your Steam library by name
* Install games by name
* Install multiple games from one command
* List installed and not-installed games
* Launch games by name
* Uninstall installed games safely through Steam
* Open an interactive picker when you want to browse/select games

## Install a game

```bash
slm install "portal 2"
```

Example:

```text
Found: Portal 2
AppID: 620
Installed: No

Install Portal 2? [Y/n]
```

## Install with a rough name

```bash
slm install 007
```

Example:

```text
Best match:
1. 007 First Light

Install 007 First Light? [Y/n]
```

## Handle multiple matches

```bash
slm install halo
```

Example:

```text
Multiple matches:

1. Halo: The Master Chief Collection
2. Halo: Spartan Assault
3. Halo: Spartan Strike

Install which one? [1-3/q]
```

## Install multiple games

```bash
slm install -m 007 halo sonic
```

Each item is treated as a separate game search.

Example:

```text
Query 1/3: 007
Best match: 007 First Light
Install this game? [Y/n/skip/details]

Query 2/3: halo
Multiple matches:

1. Halo: The Master Chief Collection
2. Halo: Spartan Assault
3. Halo: Spartan Strike

Choose game to install [1-3/s/q]:

Query 3/3: sonic
Multiple matches:

1. Sonic Frontiers
2. Sonic Mania
3. Sonic Adventure 2

Choose game to install [1-3/s/q]:
```

Then:

```text
Selected for install:

1. 007 First Light
2. Halo: The Master Chief Collection
3. Sonic Mania

Proceed with batch install? [Y/n]
```

The tool opens Steam install prompts one at a time.

## Search your library

```bash
slm search "final fantasy"
```

Example:

```text
Owned games matching "final fantasy":

1. Final Fantasy VII Remake Intergrade     Installed: No
2. Final Fantasy VIII Remastered           Installed: Yes
3. Final Fantasy IX                        Installed: No
```

## List games

```bash
slm list
```

Useful filters:

```bash
slm list --installed
slm list --not-installed
slm list --never-played
slm list --sort name
slm list --sort playtime
```

Shortcut:

```bash
slm installed
```

## Launch a game

```bash
slm launch "portal 2"
```

If several games match, the tool asks which one you mean.

## Uninstall a game

```bash
slm uninstall "baldur"
```

Example:

```text
Found installed game:

Baldur's Gate 3
Size: 145 GB

Uninstall this game using Steam? [y/N]
```

Uninstall prompts default to **No**.

## Uninstall multiple games

```bash
slm uninstall -m halo sonic portal
```

The tool resolves each query against installed games only, then asks for a final confirmation.

Example:

```text
Uninstall 3 games and free approximately 270 GB?

1. Halo: The Master Chief Collection    125 GB
2. Sonic Frontiers                       45 GB
3. Portal 2                              12 GB

Proceed? [y/N]
```

## Interactive picker

Run install with no game name:

```bash
slm install
```

Example:

```text
Steam Library — Install Games

Search: halo_

[ ] Halo: The Master Chief Collection       Not installed
[ ] Halo: Spartan Assault                   Not installed
[ ] Halo: Spartan Strike                    Not installed

Space = select    Enter = install selected    / = search    q = quit
```

Run uninstall with no game name:

```bash
slm uninstall
```

Example:

```text
Installed Steam Games — Uninstall

Search: _

[ ] Baldur's Gate 3                       145 GB
[ ] Halo: The Master Chief Collection     125 GB
[ ] Portal 2                              12 GB

Space = select    Enter = uninstall selected    q = quit
```

## Refresh your library

```bash
slm refresh
```

This updates the local cache of your Steam library and installed games.

On first run, the tool may ask for:

```text
SteamID64
Steam Web API key
```

Config is stored at:

```text
~/.config/steam-library-manager/config.toml
```

Cache is stored at:

```text
~/.cache/steam-library-manager/library.json
```

## Commands

```bash
slm refresh
slm search <query>
slm list
slm list --installed
slm list --not-installed
slm installed
slm install <query>
slm install -m <query1> <query2> <query3>
slm uninstall <query>
slm uninstall -m <query1> <query2> <query3>
slm launch <query>
slm details <query>
```

## Safety

Steam Library Manager does **not**:

* store your Steam password
* store Steam Guard codes
* buy games
* bypass Steam ownership or DRM
* require sudo
* directly delete game folders by default

Install, uninstall, and launch actions are handed off to Steam.
