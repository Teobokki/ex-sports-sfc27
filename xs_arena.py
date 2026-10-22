"""EX SPORTS(TM) SFC 27 STANDARD EDITION - SFC 27 ARENA (v1.0.0.2): build a squad of player cards and play ARENA matches.

  * PICK A TEAM from the KICK OFF club list: its name, kit colours and squad (as player cards) become your ARENA club
  * player cards: fictional players only (generated names), ratings, positions, tiers BRONZE / SILVER / GOLD / ELITE
  * squad: 11-a-side FORMATION, starting XI, captain, bench (subs), reserves and kit (HOME / AWAY / YELLOW)
  * packs bought with ARENA COINS earned by playing; ADD COINS tops them up for free. No real money, nothing to buy.
  * ARENA matches vs AI clubs on the SFC 27 pitch with your squad; coins on finish
Saved per user in %APPDATA%\\EX SPORTS SFC 27\\arena.json (no admin)."""
import os, json, random, time
from panda3d.core import TextNode
from direct.gui.DirectGui import DirectFrame, DGG
import xs_ui as U
import xs_sfc as F

TIERS = [("BRONZE", 50, 64), ("SILVER", 65, 74), ("GOLD", 75, 84), ("ELITE", 85, 94)]
TIER_STYLE = {   # (card fill, edge, text) - flat colours, no glow
    "BRONZE": ((0.55, 0.36, 0.2, 1), (0.8, 0.55, 0.32, 1), (1, 0.95, 0.88, 1)),
    "SILVER": ((0.62, 0.65, 0.7, 1), (0.88, 0.9, 0.94, 1), (0.08, 0.1, 0.14, 1)),
    "GOLD":   ((0.86, 0.69, 0.2, 1), (1.0, 0.88, 0.45, 1), (0.12, 0.08, 0.02, 1)),
    "ELITE":  ((0.45, 0.02, 0.09, 1), (1.0, 1.0, 1.0, 1), (1.0, 0.86, 0.3, 1)),
}
PACKS = [  # name, price, cards, guaranteed tier, odds per extra card (silver, gold, elite)
    ("BRONZE PACK", 750, 3, "BRONZE", (0.15, 0.02, 0.0)),
    ("SILVER PACK", 2500, 5, "SILVER", (0.45, 0.1, 0.0)),
    ("GOLD PACK", 7500, 5, "GOLD", (0.5, 0.3, 0.05)),
    ("ELITE PACK", 25000, 3, "ELITE", (0.2, 0.6, 0.2)),
]
COIN_TOPUPS = (1000, 10000, 100000)
START_COINS = 5000
FIRST = ["KAITO", "RYO", "HARUTO", "SORA", "TAKUMI", "YUTO", "KENTA", "DAICHI", "SHUN", "TAIGA", "MINATO", "ITSUKI", "LEO", "MARCO",
         "NICO", "TOMAS", "ELIAS", "OSKAR", "RAFA", "JONAS", "MATEO", "IVO", "ARLO", "FINN", "ZANE", "KOFI", "AMARU", "TEO", "LUKA",
         "NOAH", "REI", "JIN", "KAEL", "DARIO", "EMRE", "SAMI", "TOBIAS", "ALVI", "CASPIAN", "ORIN"]
LAST = ["AOKI", "KIRISHIMA", "NAKAHARA", "SHIRAKAWA", "TAKEDA", "MORIYAMA", "HOSHINO", "KUDO", "ARAKI", "FUJIWARA", "OKAMURA",
        "VALDEN", "MERINO", "KASTOV", "LINDHOLT", "DORREN", "SALVETTI", "OYELARAN", "BRANKOVIC", "QUILLER", "MARVANE", "TESSARO",
        "HALVIK", "RENWICK", "DUVALLE", "CORRADI", "ISHIGURO", "VANTERMOL", "KORVEN", "ASHBRIDGE", "MIRANTE", "SOLBERG", "TAKASAGO",
        "NERIMA", "OKUBO", "YAMASAKI", "PELLARO", "DRAVEN", "HOLLOWAY", "STRANDE"]
ROLES = ("GK", "DF", "MF", "FW")
SQUAD_SHAPE = ["GK"] + ["DF"] * 4 + ["MF"] * 4 + ["FW"] * 2 + ["GK", "DF", "DF", "MF", "MF", "FW", "FW"]   # 11 + 7 subs


def tier_of(r):
    for name, lo, hi in TIERS:
        if r <= hi: return name
    return "ELITE"


def fmt(n): return format(int(n), ",")


def make_card(rng, cid, pos, rating, club):
    """one fictional player card"""
    def st(bias): return max(30, min(99, int(rating + bias + rng.randint(-6, 6))))
    if pos == "GK": stats = {"DIV": st(2), "REF": st(3), "KIC": st(-8), "POS": st(1)}
    else:
        b = {"DF": (-6, -14, -4, 6), "MF": (-2, -4, 6, -4), "FW": (5, 6, -3, -18)}[pos]
        stats = dict(zip(("PAC", "SHO", "PAS", "DEF"), (st(b[0]), st(b[1]), st(b[2]), st(b[3]))))
    return {"id": cid, "name": "%s %s" % (rng.choice(FIRST), rng.choice(LAST)), "pos": pos, "rating": int(rating),
            "tier": tier_of(rating), "club": club, "stats": stats, "num": rng.randint(2, 30) if pos != "GK" else 1}


def club_roster(club_idx, start_id):
    """the fixed squad of a KICK OFF club as cards (deterministic per club): 11 starters + 7 subs"""
    rng = random.Random(2700 + club_idx); club = F.CLUBS[club_idx][0]; base = 62 + (club_idx * 3) % 7
    cards = []
    for k, pos in enumerate(SQUAD_SHAPE):
        r = base + rng.randint(-3, 6) + (4 if k < 11 else -2)
        if k in (9, 10): r += 3                      # the strikers are the club's stars
        cards.append(make_card(rng, start_id + k, pos, max(52, min(84, r)), club))
    nums = list(range(2, 30)); rng.shuffle(nums)
    for k, c in enumerate(cards): c["num"] = 1 if k == 0 else (12 if k == 11 else nums.pop())
    return cards


class Arena:
    def __init__(self, app):
        self.app = app; self.ui = None; self.overlay = None; self.sel = None; self.cap_mode = False; self.res_page = 0
        base = getattr(app, "DATA", None) or os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "EX SPORTS SFC 27")
        self.path = os.path.join(base, "arena_smoke.json" if os.environ.get("EXS_SMOKE") else "arena.json")
        if os.environ.get("EXS_SMOKE") and os.path.exists(self.path): os.remove(self.path)   # the smoke test starts clean
        self.d = self._load(); self.last_pack = []

    # ---------------------------------------------------------------- save
    def _load(self):
        try:
            d = json.load(open(self.path, encoding="utf-8"))
            if d.get("club") is not None and d.get("cards"): return d
        except Exception: pass
        return None

    def save(self):
        if not self.d: return
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True); tmp = self.path + ".tmp"
            json.dump(self.d, open(tmp, "w", encoding="utf-8"), indent=1); os.replace(tmp, self.path)
        except Exception as e:
            print("arena save error", e, flush=True)

    # ---------------------------------------------------------------- club / squad logic
    def card(self, cid):
        for c in self.d["cards"]:
            if c["id"] == cid: return c
        return None

    def new_club(self, club_idx):
        """NEW CLUB: fresh start with the chosen KICK OFF team as the squad"""
        cards = club_roster(club_idx, 1)
        self.d = {"v": 1, "club": club_idx, "coins": START_COINS, "cards": cards, "next_id": len(cards) + 1, "formation": "4-4-2",
                  "xi": [c["id"] for c in cards[:11]], "bench": [c["id"] for c in cards[11:18]], "captain": cards[10]["id"],
                  "kit": "HOME", "played": 0, "won": 0, "drawn": 0, "lost": 0, "packs": 0, "created": time.time()}
        self.save()

    def change_team(self, club_idx):
        """CHANGE TEAM: the new base team's squad becomes the XI + bench; coins and every card you own are kept (reserves)"""
        d = self.d; nid = d["next_id"]; cards = club_roster(club_idx, nid); d["next_id"] = nid + len(cards)
        d["cards"].extend(cards); d["club"] = club_idx
        d["xi"] = [c["id"] for c in cards[:11]]; d["bench"] = [c["id"] for c in cards[11:18]]; d["captain"] = cards[10]["id"]
        self.save()

    def club_tuple(self, kit=None):
        c = F.CLUBS[self.d["club"] % len(F.CLUBS)]; kit = kit or self.d.get("kit", "HOME")
        if kit == "AWAY": return (c[0], c[1], c[3], c[2])
        if kit == "YELLOW": return (c[0], c[1], F.YELLOW, F.YELLOW, F.YELLOW)
        return tuple(c[:4])

    def slot_roles(self):
        return [r for (_u, _v, r) in F.FORMATIONS[self.d["formation"]]]

    def chemistry(self):
        """0-33: per starter +1 in his position, +1 with a club-mate in the XI, +1 with two or more"""
        d = self.d; roles = self.slot_roles(); xi = [self.card(i) for i in d["xi"]]; chem = 0
        for k, c in enumerate(xi):
            if c is None: continue
            if c["pos"] == roles[k]: chem += 1
            mates = sum(1 for o in xi if o is not None and o is not c and o["club"] == c["club"])
            chem += (1 if mates >= 1 else 0) + (1 if mates >= 2 else 0)
        return chem

    def player_rating(self, k):
        c = self.card(self.d["xi"][k]); roles = self.slot_roles()
        r = c["rating"] - (0 if c["pos"] == roles[k] else (12 if "GK" in (c["pos"], roles[k]) else 5))
        return r + (2 if c["id"] == self.d.get("captain") else 0)

    def team_rating(self):
        xi = self.d["xi"]
        avg = sum(self.player_rating(k) for k in range(len(xi))) / max(1, len(xi))
        return int(round(avg + self.chemistry() / 33.0 * 3))

    def set_formation(self, f):
        if f in F.FORMATIONS: self.d["formation"] = f; self.save()

    def set_kit(self, k):
        self.d["kit"] = k; self.save()

    def set_captain(self, cid):
        if cid in self.d["xi"]: self.d["captain"] = cid; self.save()

    def reserves(self):
        used = set(self.d["xi"]) | set(self.d["bench"])
        return sorted([c for c in self.d["cards"] if c["id"] not in used], key=lambda c: (-c["rating"], c["name"]))

    def _get(self, ref):
        kind, v = ref
        if kind == "xi": return self.d["xi"][v]
        if kind == "bench": return self.d["bench"][v]
        return v

    def _put(self, ref, cid):
        kind, v = ref
        if kind == "xi": self.d["xi"][v] = cid
        elif kind == "bench": self.d["bench"][v] = cid

    def swap(self, a, b):
        """swap two squad places: ("xi", slot) / ("bench", slot) / ("res", card id)"""
        if a == b: return
        if a[0] == "res" and b[0] == "res": return
        ca, cb = self._get(a), self._get(b)
        self._put(a, cb); self._put(b, ca)
        if self.d.get("captain") not in self.d["xi"]: self.d["captain"] = self.d["xi"][-1]
        self.save()

    def add_coins(self, n):
        """ADD COINS: a free top-up of ARENA COINS (no real money, no purchase)"""
        self.d["coins"] = int(self.d["coins"]) + int(n); self.save(); return self.d["coins"]

    def open_pack(self, idx, rng=None):
        name, price, n, guar, odds = PACKS[idx]
        if self.d["coins"] < price: return None
        rng = rng or random.Random(); self.d["coins"] -= price; self.d["packs"] = self.d.get("packs", 0) + 1
        out = []
        for k in range(n):
            if k == 0: t = guar
            else:
                x = rng.random(); t = "BRONZE"
                if x < odds[2]: t = "ELITE"
                elif x < odds[2] + odds[1]: t = "GOLD"
                elif x < odds[2] + odds[1] + odds[0]: t = "SILVER"
            lo, hi = [(a, b) for tt, a, b in TIERS if tt == t][0]
            c = make_card(rng, self.d["next_id"], rng.choice(("GK", "DF", "DF", "MF", "MF", "MF", "FW", "FW")), rng.randint(lo, hi),
                          rng.choice(F.CLUBS)[0])
            self.d["next_id"] += 1; self.d["cards"].append(c); out.append(c)
        out.sort(key=lambda c: c["rating"]); self.last_pack = out; self.save()
        return out

    def opponent(self):
        """an AI club near your team rating (never your own base club)"""
        rng = random.Random(); others = [i for i in range(len(F.CLUBS)) if i != self.d["club"]]; oi = rng.choice(others)
        cards = club_roster(oi, 0); tr = self.team_rating(); shift = (tr + rng.randint(-4, 3)) - sum(c["rating"] for c in cards[:11]) / 11.0
        players = [{"name": c["name"], "num": c["num"], "rating": int(c["rating"] + shift)} for c in cards[:11]]
        return oi, players, int(sum(p["rating"] for p in players) / 11)

    def match_setup(self):
        d = self.d; oi, opp, orat = self.opponent(); shape = F.FORMATIONS[d["formation"]]
        mine = []
        for k, cid in enumerate(d["xi"]):
            c = self.card(cid); nm = c["name"] + (" (C)" if cid == d.get("captain") else "")
            mine.append({"name": nm, "num": c["num"], "rating": self.player_rating(k)})
        oc = F.CLUBS[oi]
        return {"clubs": [self.club_tuple(), tuple(oc[:4])], "shapes": [shape, F.FORMATIONS[random.choice(list(F.FORMATIONS))]],
                "players": [mine, opp], "on_finish": self.reward, "opp_rating": orat}

    def reward(self, m):
        s = m.score; won = s[0] > s[1]; drew = s[0] == s[1]
        coins = 250 + 100 * s[0] + (500 if won else 200 if drew else 0)
        d = self.d; d["coins"] += coins; d["played"] += 1
        d["won" if won else "drawn" if drew else "lost"] += 1; self.save()
        return coins

    def play_match(self, autoplay=False):
        a = self.app; g = a.game; st = a.settings; setup = self.match_setup(); self.close()
        g.arena_return = True
        g.start_match(minutes_real=float(st.get("duration", 0)), arena=setup, autoplay=autoplay)
        return setup

    # ---------------------------------------------------------------- UI
    def close(self):
        self.close_overlay()
        if self.app.screen and self.app.screen.startswith("arena"): self.app.clear_screen()

    def close_overlay(self):
        if self.overlay is not None: self.overlay.destroy(); self.overlay = None

    def back(self):
        if self.overlay is not None: self.close_overlay(); return
        scr = self.app.screen
        if scr == "arena" or (scr == "arena-pick" and not self.d): self.app.show_menu()
        else: self.show_hub()

    def _frame(self, name):
        self.close_overlay(); a = self.app; o = a._frame_ui(name, 0.6)
        U.panel(o, -1.62, 1.62, -0.9, 0.9, edge=(0.45, 0.02, 0.09, 1))
        U.text(o, "SFC 27 ARENA", (-1.55, 0.79), 0.06, fg=U.PINK, align=TextNode.A_left)
        if self.d:
            U.text(o, "ARENA COINS  %s" % fmt(self.d["coins"]), (1.55, 0.8), 0.04, fg=(1, 0.84, 0.08, 1), align=TextNode.A_right)
        a._footer(o)
        return o

    def draw_card(self, parent, c, pos, s=1.0, sel=False, captain=False, cmd=None):
        """an original flat card: tier colours, rating, position, name, four stats. No glow."""
        fill, edge, fg = TIER_STYLE[c["tier"]]; w, h = 0.13 * s, 0.18 * s
        if sel: edge = (0.3, 1.0, 0.45, 1)
        o = U.button(parent, "", pos, cmd, w=w, h=h, col=fill, edge=edge, scale=0.01) if cmd else \
            DirectFrame(parent=parent, frameColor=edge, frameSize=(-w - 0.006, w + 0.006, -h - 0.006, h + 0.006), pos=(pos[0], 0, pos[1]))
        if not cmd: DirectFrame(parent=o, frameColor=fill, frameSize=(-w, w, -h, h), state=DGG.DISABLED)
        DirectFrame(parent=o, frameColor=edge, frameSize=(-w, w, h * 0.5, h * 0.53), state=DGG.DISABLED)   # thin divider line
        U.text(o, str(c["rating"]), (-w * 0.55, h * 0.62), 0.065 * s, fg=fg)
        U.text(o, c["pos"], (-w * 0.55, h * 0.36), 0.032 * s, fg=fg, font=U.FONT_PLAIN)
        U.text(o, c["tier"], (w * 0.45, h * 0.7), 0.022 * s, fg=fg, font=U.FONT_PLAIN)
        if captain: U.text(o, "C", (w * 0.55, h * 0.36), 0.04 * s, fg=fg)
        nm = c["name"].split(" ")
        U.text(o, nm[0], (0, -h * 0.05), 0.026 * s, fg=fg, font=U.FONT_PLAIN)
        U.text(o, nm[-1], (0, -h * 0.25), 0.03 * s, fg=fg)
        st = list(c["stats"].items())
        U.text(o, "  ".join("%s %d" % kv for kv in st[:2]), (0, -h * 0.55), 0.021 * s, fg=fg, font=U.FONT_PLAIN)
        U.text(o, "  ".join("%s %d" % kv for kv in st[2:]), (0, -h * 0.75), 0.021 * s, fg=fg, font=U.FONT_PLAIN)
        return o

    # hub ---------------------------------------------------------------
    def show_hub(self):
        if not self.d: return self.show_pick(first=True)
        o = self._frame("arena"); d = self.d; c = self.club_tuple()
        U.text(o, c[0], (-1.55, 0.62), 0.07, fg=tuple(c[2][:3]) + (1,), align=TextNode.A_left, shadow=(0, 0, 0, 1))
        cap = self.card(d.get("captain"))
        U.text(o, "TEAM RATING %d    CHEMISTRY %d/33    FORMATION %s    CAPTAIN %s    KIT %s" % (
            self.team_rating(), self.chemistry(), d["formation"], cap["name"] if cap else "-", d.get("kit", "HOME")),
            (-1.55, 0.52), 0.032, align=TextNode.A_left, font=U.FONT_PLAIN)
        U.text(o, "PLAYED %d   WON %d   DRAWN %d   LOST %d   CARDS %d   PACKS OPENED %d" % (
            d["played"], d["won"], d["drawn"], d["lost"], len(d["cards"]), d.get("packs", 0)), (-1.55, 0.45), 0.028,
            fg=(0.85, 0.88, 0.95, 1), align=TextNode.A_left, font=U.FONT_PLAIN)
        items = [("PLAY ARENA MATCH", lambda: self.play_match()), ("SQUAD", self.show_squad), ("PACKS", self.show_packs),
                 ("ADD COINS", self.show_add_coins), ("CHANGE TEAM", lambda: self.show_pick(mode="change")),
                 ("NEW CLUB", lambda: self.show_pick(mode="new")), ("BACK", self.app.show_menu)]
        for i, (t, fn) in enumerate(items):
            U.button(o, t, (1.15, 0.5 - i * 0.12), fn, w=0.32, h=0.045, scale=0.036,
                     edge=(0.3, 1.0, 0.45, 1) if i == 0 else (1, 0.84, 0.08, 1) if t == "ADD COINS" else U.PINK)
        U.text(o, "Match length follows SETTINGS (UNLIMITED by default). Coins on finish: 250 + 100 per goal + 500 win / 200 draw.",
               (-0.35, -0.82), 0.024, fg=(0.85, 0.88, 0.95, 1), font=U.FONT_PLAIN)
        xi = sorted([self.card(i) for i in d["xi"]], key=lambda c: -c["rating"])[:5]
        U.text(o, "YOUR BEST XI CARDS", (-1.55, 0.3), 0.03, fg=U.CYAN, align=TextNode.A_left, font=U.FONT_PLAIN)
        for k, cc in enumerate(xi):
            self.draw_card(o, cc, (-1.35 + k * 0.33, -0.05), 1.1, captain=cc["id"] == d.get("captain"))

    # pick a team ---------------------------------------------------------
    def show_pick(self, first=False, mode="new"):
        o = self._frame("arena-pick"); self.pick_mode = "new" if first else mode
        title = {"new": "PICK A TEAM", "change": "CHANGE TEAM"}[self.pick_mode]
        U.text(o, title, (0, 0.62), 0.07, fg=(1, 1, 1, 1))
        sub = ("Choose your base club from the KICK OFF teams: its name, kit and squad become your ARENA club." if self.pick_mode == "new" and first else
               "NEW CLUB starts over: a fresh squad and %s ARENA COINS. Your current club, cards and coins are replaced." % fmt(START_COINS)
               if self.pick_mode == "new" else "CHANGE TEAM keeps your coins and every card you own; the new team's squad becomes your XI and bench.")
        U.text(o, sub, (0, 0.53), 0.028, fg=(0.85, 0.88, 0.95, 1), font=U.FONT_PLAIN)
        for i, c in enumerate(F.CLUBS):
            x = -0.95 + (i % 3) * 0.95; y = 0.25 - (i // 3) * 0.42; ro = club_roster(i, 0)
            avg = int(sum(r["rating"] for r in ro[:11]) / 11)
            U.button(o, c[0], (x, y), lambda i=i: self.pick(i), w=0.42, h=0.13, scale=0.038, col=tuple(c[2][:3]) + (0.92,), edge=tuple(c[3][:3]) + (1,),
                     fg=(1, 1, 1, 1) if sum(c[2]) < 1.9 else (0.05, 0.05, 0.08, 1))
            U.text(o, "SQUAD RATING %d   %s" % (avg, c[1]), (x, y - 0.18), 0.026, fg=(1, 1, 1, 0.9), font=U.FONT_PLAIN)
        if not first: U.button(o, "BACK", (0, -0.68), self.show_hub, w=0.2, h=0.045, scale=0.038, hint="Esc")
        else: U.button(o, "BACK", (0, -0.68), self.app.show_menu, w=0.2, h=0.045, scale=0.038, hint="Esc")

    def pick(self, i):
        if self.pick_mode == "change" and self.d: self.change_team(i)
        else: self.new_club(i)
        self.sel = None; self.show_squad()

    # squad ---------------------------------------------------------------
    def show_squad(self):
        o = self._frame("arena-squad"); d = self.d; roles = self.slot_roles(); shape = F.FORMATIONS[d["formation"]]
        U.text(o, "SQUAD   %s" % self.club_tuple()[0], (-0.2, 0.79), 0.045, fg=(1, 1, 1, 1))
        U.text(o, "TEAM RATING %d   CHEMISTRY %d/33" % (self.team_rating(), self.chemistry()), (-1.55, 0.7), 0.03, fg=U.CYAN,
               align=TextNode.A_left, font=U.FONT_PLAIN)
        for k, f in enumerate(F.FORMATIONS):
            U.button(o, f, (-1.42 + k * 0.25, 0.6), lambda f=f: (self.set_formation(f), self.show_squad()), w=0.11, h=0.032, scale=0.026,
                     edge=(0.3, 1.0, 0.45, 1) if d["formation"] == f else (0.4, 0.4, 0.45, 1))
        for k, kt in enumerate(("HOME", "AWAY", "YELLOW")):
            U.button(o, "KIT " + kt, (-0.1 + k * 0.27, 0.6), lambda kt=kt: (self.set_kit(kt), self.show_squad()), w=0.12, h=0.032, scale=0.024,
                     edge=(1, 0.84, 0.08, 1) if d.get("kit", "HOME") == kt else (0.4, 0.4, 0.45, 1))
        U.button(o, "SET CAPTAIN: %s" % ("PICK A STARTER" if self.cap_mode else "OFF"), (0.82, 0.6),
                 lambda: (setattr(self, "cap_mode", not self.cap_mode), self.show_squad()), w=0.2, h=0.032, scale=0.024,
                 edge=(1, 0.84, 0.08, 1) if self.cap_mode else (0.4, 0.4, 0.45, 1))
        # pitch
        DirectFrame(parent=o, frameColor=(0.16, 0.42, 0.14, 1), frameSize=(-1.55, 0.25, -0.62, 0.52), state=DGG.DISABLED)
        for k, (u, v, role) in enumerate(shape):
            x = -0.65 + u / 34.0 * 0.82; y = -0.53 + (v + 52.5) / 58.0 * 0.95
            c = self.card(d["xi"][k])
            self.draw_card(o, c, (x, y), 0.62, sel=self.sel == ("xi", k), captain=c["id"] == d.get("captain"),
                           cmd=lambda k=k: self.click(("xi", k)))
            U.text(o, role + ("" if c["pos"] == role else " !"), (x, y - 0.135), 0.022, fg=(1, 1, 1, 1) if c["pos"] == role else (1, 0.5, 0.4, 1),
                   font=U.FONT_PLAIN, shadow=(0, 0, 0, 1))
        # bench
        U.text(o, "BENCH (SUBS)", (-1.55, -0.68), 0.026, fg=U.CYAN, align=TextNode.A_left, font=U.FONT_PLAIN)
        for k, cid in enumerate(d["bench"]):
            self.draw_card(o, self.card(cid), (-1.12 + k * 0.2, -0.78), 0.5, sel=self.sel == ("bench", k), cmd=lambda k=k: self.click(("bench", k)))
        # reserves
        res = self.reserves(); per = 9; pages = max(1, (len(res) + per - 1) // per); self.res_page = min(self.res_page, pages - 1)
        U.text(o, "RESERVES  %d   (page %d/%d)" % (len(res), self.res_page + 1, pages), (0.95, 0.5), 0.028, fg=U.CYAN, font=U.FONT_PLAIN)
        for k, c in enumerate(res[self.res_page * per:(self.res_page + 1) * per]):
            fill, edge, fg = TIER_STYLE[c["tier"]]
            U.button(o, "%d  %s  %s" % (c["rating"], c["pos"], c["name"]), (0.95, 0.4 - k * 0.095), lambda cid=c["id"]: self.click(("res", cid)),
                     w=0.55, h=0.036, scale=0.026, col=fill[:3] + (0.95,), fg=fg,
                     edge=(0.3, 1.0, 0.45, 1) if self.sel == ("res", c["id"]) else edge)
        if pages > 1:
            U.button(o, "<", (0.55, -0.48), lambda: (setattr(self, "res_page", max(0, self.res_page - 1)), self.show_squad()), w=0.04, h=0.03, scale=0.03)
            U.button(o, ">", (1.35, -0.48), lambda: (setattr(self, "res_page", min(pages - 1, self.res_page + 1)), self.show_squad()), w=0.04, h=0.03, scale=0.03)
        hint = ("Click a starter to make him captain." if self.cap_mode else
                "Click a player, then another place (starter, sub or reserve) to swap them." if self.sel is None else "Now click where he should go.")
        U.text(o, hint, (0.95, -0.58), 0.024, fg=(1, 0.9, 0.5, 1), font=U.FONT_PLAIN)
        U.button(o, "DONE", (0.95, -0.72), self.show_hub, w=0.2, h=0.04, scale=0.034, hint="Esc")

    def click(self, ref):
        if self.cap_mode:
            if ref[0] == "xi": self.set_captain(self.d["xi"][ref[1]]); self.cap_mode = False
            self.show_squad(); return
        if self.sel is None: self.sel = ref
        else: self.swap(self.sel, ref); self.sel = None
        self.show_squad()

    # packs / coins ----------------------------------------------------------
    def show_packs(self):
        o = self._frame("arena-packs")
        U.text(o, "PACKS", (0, 0.62), 0.07, fg=(1, 1, 1, 1))
        U.text(o, "Bought with ARENA COINS only. Coins are earned by playing ARENA matches, or added for free with ADD COINS.", (0, 0.53), 0.027,
               fg=(0.85, 0.88, 0.95, 1), font=U.FONT_PLAIN)
        for i, (name, price, n, guar, _o) in enumerate(PACKS):
            x = -1.1 + i * 0.73; fill, edge, fg = TIER_STYLE[guar]
            DirectFrame(parent=o, frameColor=edge, frameSize=(-0.26, 0.26, -0.3, 0.3), pos=(x, 0, 0.12), state=DGG.DISABLED)
            DirectFrame(parent=o, frameColor=fill, frameSize=(-0.25, 0.25, -0.29, 0.29), pos=(x, 0, 0.12), state=DGG.DISABLED)
            U.text(o, name, (x, 0.3), 0.04, fg=fg)
            U.text(o, "%d CARDS" % n, (x, 0.2), 0.03, fg=fg, font=U.FONT_PLAIN)
            U.text(o, "1 %s OR BETTER" % guar if guar != "ELITE" else "1 ELITE GUARANTEED", (x, 0.13), 0.024, fg=fg, font=U.FONT_PLAIN)
            ok = self.d["coins"] >= price
            U.button(o, "OPEN  %s" % fmt(price), (x, -0.06), lambda i=i: self.open_and_show(i), w=0.2, h=0.04, scale=0.03, enabled=ok,
                     edge=(0.3, 1.0, 0.45, 1) if ok else (0.4, 0.4, 0.45, 1))
        U.button(o, "ADD COINS", (-0.3, -0.45), self.show_add_coins, w=0.2, h=0.045, scale=0.036, edge=(1, 0.84, 0.08, 1))
        U.button(o, "BACK", (0.3, -0.45), self.show_hub, w=0.2, h=0.045, scale=0.036, hint="Esc")

    def open_and_show(self, i):
        cards = self.open_pack(i)
        if cards is None: return self.show_packs()
        o = self._frame("arena-open"); name = PACKS[i][0]
        U.text(o, name, (0, 0.62), 0.07, fg=(1, 1, 1, 1))
        n = len(cards); a = self.app
        for k, c in enumerate(cards):                       # reveal one by one, best card last
            x = (k - (n - 1) / 2.0) * 0.6
            node = self.draw_card(o, c, (x, 0.08), 1.6); node.set_scale(0.001)
            a.do_method_later(0.35 + 0.55 * k, lambda t, nd=node: (nd.scaleInterval(0.3, 1.0, startScale=0.001).start() if not nd.is_empty() else None) and None,
                              "arena-reveal-%d" % k)
            if k == n - 1: a.sfx("checkpoint", 0.6)
        U.text(o, "Added to your club. Put them in your XI from SQUAD.", (0, -0.42), 0.03, fg=(0.85, 0.88, 0.95, 1), font=U.FONT_PLAIN)
        ok = self.d["coins"] >= PACKS[i][1]
        U.button(o, "OPEN ANOTHER", (-0.6, -0.6), lambda: self.open_and_show(i), w=0.22, h=0.045, scale=0.034, enabled=ok)
        U.button(o, "SQUAD", (0, -0.6), self.show_squad, w=0.2, h=0.045, scale=0.034)
        U.button(o, "PACKS", (0.6, -0.6), self.show_packs, w=0.2, h=0.045, scale=0.034, hint="Esc")
        return cards

    def show_add_coins(self):
        self.close_overlay(); a = self.app
        o = self.overlay = DirectFrame(parent=a.aspect2d, frameColor=(0, 0, 0, 0.6), frameSize=(-4, 4, -2, 2), state=DGG.NORMAL, sortOrder=200)
        U.panel(o, -0.8, 0.8, -0.38, 0.38, edge=(1, 0.84, 0.08, 1))
        U.text(o, "ADD COINS", (0, 0.24), 0.06, fg=(1, 0.84, 0.08, 1))
        U.text(o, "Free top-up of ARENA COINS. No real money, nothing to buy.", (0, 0.15), 0.028, font=U.FONT_PLAIN)
        self.coin_lbl = U.text(o, "YOU HAVE %s" % fmt(self.d["coins"]), (0, 0.07), 0.035, fg=(1, 1, 1, 1), font=U.FONT_PLAIN)
        def add(n):
            self.add_coins(n); self.coin_lbl.setText("YOU HAVE %s" % fmt(self.d["coins"])); a.sfx("checkpoint", 0.4)
        for k, n in enumerate(COIN_TOPUPS):
            U.button(o, "+%s" % fmt(n), (-0.5 + k * 0.5, -0.07), lambda n=n: add(n), w=0.2, h=0.045, scale=0.036, edge=(0.3, 1.0, 0.45, 1))
        U.button(o, "DONE", (0, -0.25), lambda: self._refresh_after_coins(), w=0.16, h=0.04, scale=0.032, hint="Esc")

    def _refresh_after_coins(self):
        scr = self.app.screen; self.close_overlay()
        {"arena-packs": self.show_packs, "arena": self.show_hub}.get(scr, self.show_hub)()
