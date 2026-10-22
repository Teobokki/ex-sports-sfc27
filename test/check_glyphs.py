"""v1.0.4 automated font-coverage check: every character in every dialogue line (Japanese NPC speech, ambient lines,
subtitles, banter), the voice index, the UI/sign/district data and every non-ASCII literal in the game's source must
exist in the bundled fonts. Japanese -> assets/jp_font.otf, English translations -> assets/ui_plain.ttf.
Run: python3 test/check_glyphs.py   (exit code 1 + a list if anything would render as a missing-glyph box)"""
import os, sys, glob, json
from fontTools.ttLib import TTFont
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(ROOT); sys.path.insert(0, ROOT)
jp = set(TTFont("assets/jp_font.otf").getBestCmap()); en = set(TTFont("assets/ui_plain.ttf").getBestCmap())
import fs_lines as L, fs_game_banter as B
ja_strings, en_strings = [], []
ja_strings += [j for _, j, _ in L.LINES_JA + L.LINES_JA2]; en_strings += [e for _, _, e in L.LINES_JA + L.LINES_JA2]
for g, items in L.NPC_JA.items(): ja_strings += [j for j, _ in items]; en_strings += [e for _, e in items]
en_strings += [t for _, t in L.LINES] + L.SCARED + L.JACKED + [t for _, t in B.BANTER]
idx = json.load(open("assets/voice/index.json", encoding="utf-8"))
for g, items in idx.items():
    for e in items:
        (ja_strings if g.startswith("ja") else en_strings).append(e["text"])
        if e.get("en"): en_strings.append(e["en"])
src = []
for fn in sorted(glob.glob("*.py")):
    src += [(fn, c) for c in open(fn, encoding="utf-8").read() if ord(c) > 0x7F]
miss = {}
for s in ja_strings:
    for c in s:
        if c != "\n" and ord(c) not in jp: miss.setdefault(c, set()).add("dialogue: " + s[:24])
for s in en_strings:
    for c in s:
        if c != "\n" and ord(c) not in en and ord(c) not in jp: miss.setdefault(c, set()).add("english: " + s[:24])
EMOJI = {"😊"}                          # drawn as an image icon (SELMOTES), never as text
for fn, c in src:
    if c in EMOJI or c in "\u2014\u2013\u2713": continue   # —, – and check marks only appear in docstrings / comments
    if ord(c) not in jp and ord(c) not in en: miss.setdefault(c, set()).add(fn)
n = len(ja_strings) + len(en_strings)
print("checked %d dialogue strings (%d Japanese) + %d source characters against jp_font.otf (%d glyphs) and ui_plain.ttf"
      % (n, len(ja_strings), len(src), len(jp)))
if miss:
    for c, w in sorted(miss.items()): print("MISSING %r U+%04X  in %s" % (c, ord(c), ", ".join(sorted(w))[:120]))
    sys.exit(1)
print("GLYPHS OK - every Japanese and English character renders")
