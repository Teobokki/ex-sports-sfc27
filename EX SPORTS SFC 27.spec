# -*- mode: python ; coding: utf-8 -*-
exec(open('specs_common.py').read())
a = Analysis(['ex_sports.py'], pathex=['.'], datas=ASSETS + DATAS, binaries=BINS, hiddenimports=HIDDEN, excludes=EXCL, noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='EX SPORTS SFC 27', console=False, upx=False, version='version.txt', icon=['assets/icon.ico'])
coll = COLLECT(exe, a.binaries, a.datas, upx=False, name='EX SPORTS SFC 27')
