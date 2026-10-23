# EX SPORTS™ SFC 27 STANDARD EDITION

7-a-side football (11-a-side in SFC 27 ARENA) in the EX SPORTS SFC 27 stadium. The pitch is full size with standard markings, goals with nets, four stands with a crowd, and plain floodlights with no glow. Every club and player is fictional.

## Download (Windows 10/11, 64-bit)
Get the latest build from the [Releases](https://github.com/Teobokki/ex-sports-sfc27/releases/latest) page:
- **Setup**: installs for your user account only. No admin rights and no UAC prompt.
- **Portable**: a single exe. Run it from anywhere.
- **Zip**: the full game folder.

The game checks for updates itself (menu > CHECK FOR UPDATES), using `latest.json` in this repo.

## 1.0.0.5: mixed men's and women's squads in SFC 27 ARENA
- Every ARENA team mixes men and women, roughly half and half. This covers the starter squad from your picked team, pack cards, the bench, reserves and AI opponents.
- Each player's gender is fixed by their player id and never changes.
- Women have their own faces: varied skin tones, face shapes, eye colours and ages (18 to 36), and hairstyles including ponytails, buns, braids, bobs, short cuts and curls. They have female first names and a women's player model in ARENA matches.
- Men keep their faces, names and player model.
- Existing ARENA saves keep every card's stats, rating, position, surname and squad place. Women's cards get a female first name.
- Cached portraits are re-rendered once, for the new face version. KICK OFF is unchanged.

## 1.0.0.4: player faces in SFC 27 ARENA
- Every ARENA card shows a head-and-shoulders portrait of that fictional player in their club's kit colours. This covers the starting XI and bench from your picked team, reserves, and pack cards.
- Each face is unique and always the same for that player. Faces vary in skin tone, face shape, hair style and colour, facial hair, eye colour and age (18 to 36).
- Portraits are rendered in the game's own engine, with plain lighting and no glow. They are cached per user in `%APPDATA%\EX SPORTS SFC 27\faces`.
- PLAYER INFO shows a large portrait with number, position, age, rating, tier, club and stats. Open it by clicking a card on the ARENA hub or in a pack reveal, or by switching on PLAYER INFO in SQUAD.

## 1.0.0.3: new main-menu background
- The title screen and main menu show the new SFC 27 artwork, cover-scaled (never stretched), with the buttons in a right-hand column over a subtle dark gradient.

## 1.0.0.2: intro, SFC 27 ARENA, EX SPORTS RECORDER
- **Intro**: a 6-second EX SPORTS logo intro plays on every launch, with an original sting and an en-GB voiceover: "EX SPORTS. IT'S IN THE FAME." Press Esc, Enter or Space, or click, to skip.
- **SFC 27 ARENA**:
  - Pick a team, and its players become your fictional squad of Bronze, Silver, Gold and Elite cards.
  - Set formation, swaps, captain, bench and kits.
  - Open packs with ARENA COINS earned by playing. ADD COINS gives +1,000, +10,000 or +100,000 free, with no real money.
  - Play 11-a-side matches against the AI. CHANGE TEAM is available any time.
- **EX SPORTS RECORDER**:
  - F9 records, and F10 saves the last 30 seconds.
  - Clips are YouTube-ready MP4s (H.264 + AAC 48 kHz) saved to your Downloads folder.
  - Quality is 720p30, 1080p30 or 1080p60, with an optional watermark. Nothing is uploaded.

## 1.0.0.1: update fixes
- In-game updates now start the Setup detached with a clean environment, and portable copies update and relaunch themselves. This fixes the "Failed to remove temporary directory (_MEI…)" warning.
- Versions are compared with all four parts.
- The Setup closes a running copy before installing. It's still per-user with no admin.
- QUICK MATCH VS AI is now **KICK OFF**, and the copyright reads "© 2026 EX SPORTS AND EX INC.".

## Modes
- **KICK OFF**: your club against an AI club.
- **SFC 27 ARENA**: build a squad of fictional player cards from your chosen club, then open packs with ARENA COINS and play 11-a-side matches against the AI. Saved in `%APPDATA%\EX SPORTS SFC 27`.
- **RECORDINGS**: lists your EX SPORTS RECORDER clips and opens Downloads.
- **ONLINE**: one player hosts and gets an `SFC27-XXXX-XXXX` join code. Friends type it in, and the AI fills the empty spots. The host can start ALL OF US VS AI or SPLIT TEAMS, and the host's match settings apply to everyone.
  - Connections are outbound-first. Your game always makes the first call: the guest calls the host, and the host calls the guest back from the REPLY CODE. Keep-alives hold the connection open, so no firewall rule or admin rights are needed.
  - If a friend doesn't connect within a few seconds, they read you their REPLY CODE and you type it into LET A FRIEND IN.
  - Very strict or carrier-grade NAT on both sides can still block a direct connection. In that case, forward UDP 47127 to the host's PC.
- **TEAMS**: pick your club and the opponent, choose club colours or the all-YELLOW KIT, and set your player's name and look.
- **SETTINGS**: match length defaults to **UNLIMITED**: the clock counts up until you press END MATCH (Esc). You can also pick 4, 8, 12 or 90 minutes. There are graphics and audio settings and a controls list.

## Controls
WASD / arrows move · SPACE pass · F shoot · R tackle · SHIFT sprint · ESC pause / END MATCH · F9 record · F10 save last 30 s

## Build
Linux + Wine: `./build.sh` runs PyInstaller (onedir + onefile) and Inno Setup, then zips the folder.

© 2026 EX SPORTS AND EX INC. Engine: Panda3D. Fonts: Exo 2 (SIL OFL). Recorder: FFmpeg (GPL), bundled as a separate program. Voice: Piper TTS (MIT) with the VCTK voice (CC BY 4.0). See assets/THIRD_PARTY.txt.
