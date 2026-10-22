# EX SPORTS™ SFC 27 STANDARD EDITION 1.0.0.1: update fixes

- **Check for updates → DOWNLOAD** now starts the downloaded Setup separately from the game, from %TEMP% and with a clean environment, then quits. This means no more "Failed to remove temporary directory ...\_MEI..." warning, and the update really applies.
- **Portable copies now update themselves.** The new exe is downloaded next to the old one, swapped in once the game has closed, and relaunched with a clean environment. Before this, the portable copy only opened the download page.
- Versions are compared with all four parts (1.0.0 = 1.0.0.0 < 1.0.0.1).
- The Setup closes a running EX SPORTS SFC 27 before replacing files (CloseApplications=force). It still installs per-user to %LOCALAPPDATA%\Programs\EX SPORTS SFC 27 with no admin rights.
- The copyright notice now reads "© 2026 EX SPORTS AND EX INC." in the menus, the exe and Setup version info, and the README.
- The main-menu button QUICK MATCH VS AI is now called **KICK OFF** (it works the same way: your club against an AI club).
- Gameplay is the same as 1.0.0.

© 2026 EX SPORTS AND EX INC.
