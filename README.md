# EX SPORTS™ SFC 27 STANDARD EDITION

7-a-side football in the EX SPORTS SFC 27 stadium. The pitch is full size with standard markings, goals with nets, four stands with a crowd, and plain floodlights with no glow. Every club and player is fictional.

## Download (Windows 10/11, 64-bit)
Get the latest build from the [Releases](https://github.com/Teobokki/ex-sports-sfc27/releases/latest) page:
- **Setup**: installs for your user account only. No admin rights and no UAC prompt.
- **Portable**: a single exe. Run it from anywhere.
- **Zip**: the full game folder.

The game checks for updates itself (menu > CHECK FOR UPDATES), using `latest.json` in this repo.

## 1.0.0.1: update fixes
- In-game updates now start the Setup detached with a clean environment, and portable copies update and relaunch themselves. This fixes the "Failed to remove temporary directory (_MEI…)" warning.
- Versions are compared with all four parts.
- The Setup closes a running copy before installing. It's still per-user with no admin.
- QUICK MATCH VS AI is now **KICK OFF**, and the copyright reads "© 2026 EX SPORTS AND EX INC.".

## Modes
- **KICK OFF**: your club against an AI club.
- **ONLINE**: one player hosts and gets an `SFC27-XXXX-XXXX` join code. Friends type it in, and the AI fills the empty spots. The host can start ALL OF US VS AI or SPLIT TEAMS, and the host's match settings apply to everyone.
  - Connections are outbound-first. Your game always makes the first call: the guest calls the host, and the host calls the guest back from the REPLY CODE. Keep-alives hold the connection open, so no firewall rule or admin rights are needed.
  - If a friend doesn't connect within a few seconds, they read you their REPLY CODE and you type it into LET A FRIEND IN.
  - Very strict or carrier-grade NAT on both sides can still block a direct connection. In that case, forward UDP 47127 to the host's PC.
- **TEAMS**: pick your club and the opponent, choose club colours or the all-YELLOW KIT, and set your player's name and look.
- **SETTINGS**: match length defaults to **UNLIMITED**: the clock counts up until you press END MATCH (Esc). You can also pick 4, 8, 12 or 90 minutes. There are graphics and audio settings and a controls list.

## Controls
WASD / arrows move · SPACE pass · F shoot · R tackle · SHIFT sprint · ESC pause / END MATCH

## Build
Linux + Wine: `./build.sh` runs PyInstaller (onedir + onefile) and Inno Setup, then zips the folder.

© 2026 EX SPORTS AND EX INC. Engine: Panda3D. Fonts: Exo 2 (SIL OFL).
