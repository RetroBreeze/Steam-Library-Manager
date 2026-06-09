# Steam Library Manager

Search your Steam library by name and automatically install games using SteamCMD.

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

**Steam Library Manager** is a Linux CLI that searches your Steam library by name and automatically installs games using SteamCMD.

SteamCMD can install games by AppID, but AppIDs are annoying to look up. This tool lets you use the names you actually remember:

```bash
slm install "portal 2"
```

Instead of manually running:

```bash
steamcmd +force_install_dir "~/SteamCMDLibrary/Portal 2" +login "your_username" +app_update 620 validate +quit
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
* Install games by name automatically with SteamCMD
* Install multiple games sequentially from one command
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

Install automatically with SteamCMD? [Y/n]
```

## Automatic installs

By default, `slm install` uses SteamCMD:

```bash
slm install "portal 2"
```

SteamCMD may ask for your Steam password or Steam Guard code. `slm` does not store your Steam password.

If SteamCMD fails for a game, install that game manually in Steam or use:

```bash
slm install "portal 2" --ui
```

## Steam UI fallback

To open Steam's normal install prompt instead of using SteamCMD:

```bash
slm install "portal 2" --ui
```

Equivalent backend selection is also available:

```bash
slm install "portal 2" --backend steam-ui
slm install "portal 2" --backend steamcmd
```

## Install location

By default, automatic installs go to:

```text
~/SteamCMDLibrary
```

Each game is installed into a clear per-game directory, such as:

```text
~/SteamCMDLibrary/Portal 2
```

You can change the base install directory during setup or in:

```text
~/.config/steam-library-manager/config.toml
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
Selected for automatic SteamCMD install:

1. 007 First Light
2. Halo: The Master Chief Collection
3. Sonic Mania

Install these 3 games with SteamCMD? [Y/n]
```

The tool installs games sequentially with SteamCMD.

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

On first run, the tool asks for:

```text
Steam profile URL, custom ID, or SteamID64
Steam Web API key
Steam username for SteamCMD login
SteamCMD install directory
```

Accepted Steam profile inputs:

```text
76561198012345678
https://steamcommunity.com/profiles/76561198012345678
https://steamcommunity.com/id/yourcustomname
yourcustomname
```

SteamID64 is Steam's numeric account ID. You do not need to look it up manually if you paste your Steam profile URL or custom profile name.

Config is stored at:

```text
~/.config/steam-library-manager/config.toml
```

Cache is stored at:

```text
~/.cache/steam-library-manager/library.json
```

If SteamCMD is missing, install it yourself and retry:

```bash
sudo pacman -S steamcmd
```

`slm` does not install SteamCMD automatically.

## Commands

```bash
slm refresh
slm search <query>
slm list
slm list --installed
slm list --not-installed
slm installed
slm install <query>
slm install <query> --ui
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

Automatic installs are handed off to SteamCMD. Uninstall and launch actions are handed off to Steam.
