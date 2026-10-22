#!/bin/bash
# Windows build via Wine: PyInstaller onedir + Inno Setup installer (per-user, no admin) + onefile portable + zip
set -e
export WINEPREFIX=/workspace/exwifi/.wine WINEDEBUG=-all
cd "$(dirname "$0")"
V=$(grep -oP 'APP_VERSION = "\K[^"]+' ex_sports.py)
PY='C:\Python311\python.exe'
wine "$PY" -m PyInstaller --noconfirm "EX SPORTS SFC 27.spec" > build_dir.log 2>&1; echo DIR_DONE
wine "C:\\InnoSetup\\ISCC.exe" installer.iss > build_iss.log 2>&1; echo ISS_DONE
wine "$PY" -m PyInstaller --noconfirm --workpath build_onefile --distpath dist_onefile "EX SPORTS SFC 27 onefile.spec" > build_1f.log 2>&1
cp "dist_onefile/EX SPORTS SFC 27.exe" dist/EX-SPORTS-SFC27-Portable.exe; echo ONEFILE_DONE
cd dist && rm -f EX-SPORTS-SFC27-$V-Windows-x64.zip && python3 -c "import shutil; shutil.make_archive('EX-SPORTS-SFC27-$V-Windows-x64', 'zip', '.', 'EX SPORTS SFC 27')" && echo ZIP_DONE
ls -la
