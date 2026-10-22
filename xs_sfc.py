"""EX SPORTS(TM) SFC 27 STANDARD EDITION - stadium and match engine.

  * the EX SPORTS SFC 27 STADIUM: a full-size 105 x 68 m pitch with the standard markings, goals with nets, four stands
    with a crowd, roofs and plain floodlight masts (no glow)
  * 7-a-side matches: QUICK MATCH vs AI, or ONLINE (join code) with friends + AI fill
  * pass / shoot / tackle / sprint, kickoff, goals, scoreboard, clock (UNLIMITED by default), END MATCH
Fictional clubs only."""
import math, random, time
from panda3d.core import NodePath, TextNode, CardMaker, TransparencyAttrib
from direct.gui.DirectGui import DirectFrame, DGG
import xs_data as D
import xs_ui as U
from xs_geom import MB

CX, CY = 554.0, 232.5            # pitch centre (world)
HW, HL = 34.0, 52.5              # half width (x) / half length (y)
GOAL_W, GOAL_H, GOAL_D = 3.66, 2.44, 2.0
GATE = (506.5, 232.5)            # entrance (west side, faces the boardwalk)
BALL_R = 0.11

CLUBS = [("SHINE TOKYO FC", "STF", (0.95, 0.35, 0.62), (1.0, 1.0, 1.0)),
         ("HIKARI BEACH UNITED", "HBU", (1.0, 0.8, 0.15), (0.1, 0.15, 0.35)),
         ("NEON HARBOUR CITY", "NHC", (0.1, 0.7, 0.75), (0.08, 0.08, 0.1)),
         ("SAKURA HILL ROVERS", "SHR", (0.95, 0.95, 0.95), (0.85, 0.2, 0.35)),
         ("KUROGANE ATHLETIC", "KGA", (0.18, 0.18, 0.22), (0.95, 0.4, 0.12)),
         ("AKARI WANDERERS", "AKW", (0.25, 0.42, 0.95), (1.0, 1.0, 1.0))]
YELLOW = (1.0, 0.84, 0.05)
AI_NAMES = ["HARU", "MIO", "REN", "YUI", "SOTA", "EMI", "KOJI", "NAO", "RIKU", "AOI", "DAI", "KANA", "SHO", "MEI", "TOMO", "YUKI"]
# 7-a-side shape for the team attacking +v: (u, v, role)
SHAPE = [(0, -50.5, "GK"), (-13, -31, "DF"), (13, -31, "DF"), (-21, -11, "MF"), (0, -15, "MF"), (21, -11, "MF"), (0, 4, "FW")]


def in_stadium(x, y, pad=0.0):
    r = D.STADIUM
    return r[0] - pad <= x <= r[2] + pad and r[1] - pad <= y <= r[3] + pad


# ====================================================================== stadium geometry
def build_stadium(w):
    ch = (2, 1); f = w.M("flat", ch); R = D.STADIUM; rng = random.Random(27)
    Z = 0.035
    # concourse floor + grass with mowing stripes
    f.quad((R[0], R[1], Z - 0.01), (R[2], R[1], Z - 0.01), (R[2], R[3], Z - 0.01), (R[0], R[3], Z - 0.01), (0.32, 0.32, 0.34, 1), n=(0, 0, 1))
    gx0, gx1, gy0, gy1 = CX - HW - 4, CX + HW + 4, CY - HL - 4, CY + HL + 4
    n = 16; dy = (gy1 - gy0) / n
    for k in range(n):
        c = (0.16, 0.42, 0.14, 1) if k % 2 == 0 else (0.2, 0.5, 0.17, 1)
        y0 = gy0 + k * dy; y1 = y0 + dy
        f.quad((gx0, y0, Z), (gx1, y0, Z), (gx1, y1, Z), (gx0, y1, Z), c, n=(0, 0, 1))
    LZ = Z + 0.012; L = 0.06; Wt = (0.95, 0.95, 0.95, 1)
    def line(x0, y0, x1, y1):
        dx, dy_ = x1 - x0, y1 - y0; l = math.hypot(dx, dy_) or 1; nx, ny = -dy_ / l * L, dx / l * L
        f.quad((x0 + nx, y0 + ny, LZ), (x0 - nx, y0 - ny, LZ), (x1 - nx, y1 - ny, LZ), (x1 + nx, y1 + ny, LZ), Wt, n=(0, 0, 1))
    def arc(cx, cy, r, a0, a1, seg=40):
        for i in range(seg):
            t0 = a0 + (a1 - a0) * i / seg; t1 = a0 + (a1 - a0) * (i + 1) / seg
            line(cx + r * math.cos(t0), cy + r * math.sin(t0), cx + r * math.cos(t1), cy + r * math.sin(t1))
    def spot(cx, cy, r=0.12):
        for i in range(12):
            t0 = 2 * math.pi * i / 12; t1 = 2 * math.pi * (i + 1) / 12
            f.quad((cx, cy, LZ), (cx + r * math.cos(t0), cy + r * math.sin(t0), LZ), (cx + r * math.cos(t1), cy + r * math.sin(t1), LZ), (cx, cy, LZ), Wt, n=(0, 0, 1))
    X0, X1, Y0, Y1 = CX - HW, CX + HW, CY - HL, CY + HL
    line(X0, Y0, X1, Y0); line(X1, Y0, X1, Y1); line(X1, Y1, X0, Y1); line(X0, Y1, X0, Y0)
    line(X0, CY, X1, CY); arc(CX, CY, 9.15, 0, 2 * math.pi, 64); spot(CX, CY, 0.15)
    for sg in (-1, 1):
        gy = CY + sg * HL
        # penalty area 40.32 x 16.5, goal area 18.32 x 5.5, spot at 11 m, arc r 9.15 outside the box
        for (hw_, d) in ((20.16, 16.5), (9.16, 5.5)):
            line(CX - hw_, gy, CX - hw_, gy - sg * d); line(CX + hw_, gy, CX + hw_, gy - sg * d); line(CX - hw_, gy - sg * d, CX + hw_, gy - sg * d)
        spot(CX, gy - sg * 11.0)
        a = math.acos(5.5 / 9.15)
        base = -math.pi / 2 if sg > 0 else math.pi / 2
        arc(CX, gy - sg * 11.0, 9.15, base - a, base + a, 20)
        for sx in (-1, 1):
            cxp = CX + sx * HW
            a0 = (math.pi if sx > 0 else 0) ; a1 = a0 + (math.pi / 2 if (sx > 0) == (sg > 0) else -math.pi / 2)
            arc(cxp, gy, 1.0, min(a0, a1), max(a0, a1), 8)
            f.box(cxp - 0.03, gy - 0.03, Z, cxp + 0.03, gy + 0.03, 1.5, (0.9, 0.9, 0.9, 1))            # corner flag pole
            f.quad((cxp, gy, 1.5), (cxp, gy - sg * 0.5, 1.5), (cxp, gy - sg * 0.5, 1.15), (cxp, gy, 1.15), (1.0, 0.3, 0.1, 1))
            f.quad((cxp, gy, 1.15), (cxp, gy - sg * 0.5, 1.15), (cxp, gy - sg * 0.5, 1.5), (cxp, gy, 1.5), (1.0, 0.3, 0.1, 1))
        # goal: posts + crossbar + net (white mesh of thin bars), behind the goal line
        P = 0.06; nb = 0.012; gd = sg * GOAL_D; NC = (0.92, 0.92, 0.92, 1)
        for sx in (-1, 1):
            f.box(CX + sx * GOAL_W - P, gy - P, Z, CX + sx * GOAL_W + P, gy + P, GOAL_H + P, (1, 1, 1, 1))
            f.box(CX + sx * GOAL_W - nb, min(gy, gy + gd) , Z, CX + sx * GOAL_W + nb, max(gy, gy + gd), Z + 0.05, NC)
            for k in range(9):            # side nets
                t = k / 8.0
                yy = gy + gd * t
                f.box(CX + sx * GOAL_W - nb, yy - nb, Z, CX + sx * GOAL_W + nb, yy + nb, GOAL_H - (GOAL_H * 0.25) * t, NC)
            for k in range(10):
                zz = GOAL_H * k / 10.0
                f.box(CX + sx * GOAL_W - nb, min(gy, gy + gd) , zz - nb, CX + sx * GOAL_W + nb, max(gy, gy + gd), zz + nb, NC)
        f.box(CX - GOAL_W - P, gy - P, GOAL_H - P, CX + GOAL_W + P, gy + P, GOAL_H + P, (1, 1, 1, 1))
        by = gy + gd; bz = GOAL_H * 0.75
        for k in range(31):            # back net verticals + roof net
            xx = CX - GOAL_W + 2 * GOAL_W * k / 30.0
            f.box(xx - nb, by - nb, Z, xx + nb, by + nb, bz, NC)
        for k in range(9):
            zz = bz * k / 8.0
            f.box(CX - GOAL_W, by - nb, zz - nb, CX + GOAL_W, by + nb, zz + nb, NC)
        for k in range(9):            # sloped roof net from the crossbar back to the top of the back net
            t = k / 8.0; yy = gy + gd * t; zz = GOAL_H - (GOAL_H - bz) * t
            f.box(CX - GOAL_W, yy - nb, zz - nb, CX + GOAL_W, yy + nb, zz + nb, NC)
        for k in range(0, 31, 2):
            xx = CX - GOAL_W + 2 * GOAL_W * k / 30.0
            for j in range(8):
                t0 = j / 8.0; t1 = (j + 1) / 8.0
                y0_, y1_ = gy + gd * t0, gy + gd * t1; z0_, z1_ = GOAL_H - (GOAL_H - bz) * t0, GOAL_H - (GOAL_H - bz) * t1
                f.box(xx - nb, min(y0_, y1_), min(z0_, z1_) - nb, xx + nb, max(y0_, y1_), max(z0_, z1_) + nb, NC)
    # advertising boards around the pitch (fictional)
    ads = [(0.95, 0.35, 0.62), (0.1, 0.7, 0.75), (1.0, 0.8, 0.15), (0.25, 0.42, 0.95), (0.95, 0.45, 0.1)]
    k = 0
    for (x0, y0, x1, y1) in ((X0 - 2.5, Y0 - 2.5, X1 + 2.5, Y0 - 2.3), (X0 - 2.5, Y1 + 2.3, X1 + 2.5, Y1 + 2.5),
                             (X0 - 2.5, Y0 - 2.5, X0 - 2.3, Y1 + 2.5), (X1 + 2.3, Y0 - 2.5, X1 + 2.5, Y1 + 2.5)):
        horiz = (x1 - x0) > (y1 - y0); a, b = (x0, x1) if horiz else (y0, y1); seg = 8.0; t = a
        while t < b - 0.1:
            e = min(b, t + seg); c = ads[k % len(ads)]; k += 1
            if horiz: f.box(t, y0, Z, e, y1, 0.95, (c[0], c[1], c[2], 1))
            else:
                if x0 < CX and abs((t + e) / 2 - CY) < 6: t = e; continue       # players' tunnel gap on the west side
                f.box(x0, t, Z, x1, e, 0.95, (c[0], c[1], c[2], 1))
            t = e
    # stands: stepped terraces on all four sides, rising outward, with a crowd
    seat_cols = [(0.85, 0.2, 0.45), (0.15, 0.55, 0.75), (0.95, 0.95, 0.95)]
    shirt = [(0.95, 0.35, 0.62), (1.0, 0.8, 0.15), (0.95, 0.95, 0.95), (0.15, 0.2, 0.4), (0.1, 0.7, 0.75), (0.85, 0.2, 0.2), (0.2, 0.2, 0.22)]
    skins = [(0.95, 0.8, 0.68), (0.85, 0.65, 0.5), (0.62, 0.43, 0.3), (0.38, 0.25, 0.17)]
    IN = (X0 - 4.5, Y0 - 4.5, X1 + 4.5, Y1 + 4.5); T = 8; TD = 1.0; TH = 0.55
    def terrace(side):
        for i in range(T):
            z1 = 0.5 + TH * (i + 1)
            if side == "W": rect = (IN[0] - TD * (i + 1), IN[1], IN[0] - TD * i, IN[3])
            elif side == "E": rect = (IN[2] + TD * i, IN[1], IN[2] + TD * (i + 1), IN[3])
            elif side == "S": rect = (IN[0] - TD * T, IN[1] - TD * (i + 1), IN[2] + TD * T, IN[1] - TD * i)
            else: rect = (IN[0] - TD * T, IN[3] + TD * i, IN[2] + TD * T, IN[3] + TD * (i + 1))
            parts = [rect]
            if side == "W":       # the gate tunnel cuts through the west stand
                parts = [(rect[0], rect[1], rect[2], CY - 4.0), (rect[0], CY + 4.0, rect[2], rect[3])]
            for (a0, b0, a1, b1) in parts:
                c = seat_cols[i % 3]
                f.box(a0, b0, Z, a1, b1, z1, (c[0] * 0.8, c[1] * 0.8, c[2] * 0.8, 1))
                # crowd: little seated fans along the row
                horiz = side in ("S", "N"); L0, L1 = (a0, a1) if horiz else (b0, b1); t = L0 + 0.3
                cc = (a1 + a0) / 2 if not horiz else (b1 + b0) / 2
                while t < L1 - 0.3:
                    if rng.random() < 0.72:
                        sc = rng.choice(shirt); sk = rng.choice(skins)
                        px, py = (t, cc) if horiz else (cc, t)
                        f.box(px - 0.2, py - 0.15, z1, px + 0.2, py + 0.15, z1 + 0.55, (sc[0], sc[1], sc[2], 1))
                        f.box(px - 0.1, py - 0.1, z1 + 0.55, px + 0.1, py + 0.1, z1 + 0.78, (sk[0], sk[1], sk[2], 1))
                    t += rng.uniform(0.6, 0.9)
        top = 0.5 + TH * T
        if side == "W": back = (IN[0] - TD * T - 0.4, IN[1], IN[0] - TD * T, IN[3])
        elif side == "E": back = (IN[2] + TD * T, IN[1], IN[2] + TD * T + 0.4, IN[3])
        elif side == "S": back = (IN[0] - TD * T - 0.4, IN[1] - TD * T - 0.4, IN[2] + TD * T + 0.4, IN[1] - TD * T)
        else: back = (IN[0] - TD * T - 0.4, IN[3] + TD * T, IN[2] + TD * T + 0.4, IN[3] + TD * T + 0.4)
        bparts = [back] if side != "W" else [(back[0], back[1], back[2], CY - 4.0), (back[0], CY + 4.0, back[2], back[3])]
        for bp in bparts:
            f.box(bp[0], bp[1], Z, bp[2], bp[3], top + 4.5, (0.82, 0.84, 0.88, 1))
            w.grid.add_rect(bp, "b")
        # roof canopy over the long stands
        if side in ("W", "E"):
            x0, x1 = (IN[0] - TD * T - 0.4, IN[0] - 1.5) if side == "W" else (IN[2] + 1.5, IN[2] + TD * T + 0.4)
            f.box(x0, IN[1], top + 4.5, x1, IN[3], top + 4.8, (0.9, 0.92, 0.95, 1))
            for yy in range(int(IN[1]) + 4, int(IN[3]), 18):
                xx = x0 + 0.2 if side == "W" else x1 - 0.4
                f.box(xx, yy, Z, xx + 0.25, yy + 0.25, top + 4.6, (0.75, 0.77, 0.8, 1))
    for sd in ("W", "E", "S", "N"): terrace(sd)
    # collision: the terraces (west one split around the gate tunnel)
    o = TD * T
    w.grid.add_rect((IN[0] - o, IN[1] - o, IN[0], CY - 4.0), "b"); w.grid.add_rect((IN[0] - o, CY + 4.0, IN[0], IN[3] + o), "b")
    w.grid.add_rect((IN[2], IN[1] - o, IN[2] + o, IN[3] + o), "b")
    w.grid.add_rect((IN[0], IN[1] - o, IN[2], IN[1]), "b"); w.grid.add_rect((IN[0], IN[3], IN[2], IN[3] + o), "b")
    # tunnel walls + gate arch at the outer west face
    gx = IN[0] - o - 0.4
    for sy in (-1, 1):
        f.box(gx - 1.2, CY + sy * 4.0 - (0.6 if sy > 0 else 0.0), Z, gx + 0.4, CY + sy * 4.0 + (0.0 if sy > 0 else 0.6), 9.0, (0.12, 0.16, 0.32, 1))
    f.box(gx - 1.2, CY - 4.6, 7.2, gx + 0.4, CY + 4.6, 9.0, (0.12, 0.16, 0.32, 1))
    f.box(gx - 1.25, CY - 4.0, 7.35, gx - 1.2, CY + 4.0, 8.85, (0.95, 0.35, 0.62, 1))          # pink sign band
    # floodlight masts (plain - no glow): grey lattice-ish pole + lamp bank
    for (mx, my) in ((IN[0] - o - 1.5, IN[1] - o - 1.5), (IN[2] + o + 1.5, IN[1] - o - 1.5), (IN[0] - o - 1.5, IN[3] + o + 1.5), (IN[2] + o + 1.5, IN[3] + o + 1.5)):
        f.box(mx - 0.35, my - 0.35, Z, mx + 0.35, my + 0.35, 30.0, (0.6, 0.62, 0.66, 1))
        sx = 1 if mx < CX else -1; sy = 1 if my < CY else -1
        f.box(mx - 2.2, my - 2.2, 29.5, mx + 2.2, my + 2.2, 32.5, (0.55, 0.57, 0.6, 1))
        for i in range(4):
            for j in range(3):
                f.box(mx - 1.9 + i * 1.0, my - 2.25 * sy - 0.02, 29.8 + j * 0.9, mx - 1.1 + i * 1.0, my - 2.25 * sy + 0.02, 30.5 + j * 0.9, (0.92, 0.92, 0.88, 1))
        w.grid.add_circle(mx, my, 0.5, "p")
    # goals collide (posts) so players don't run through the net
    for sg in (-1, 1):
        gy = CY + sg * HL
        for sx in (-1, 1): w.grid.add_rect((CX + sx * GOAL_W - 0.08, min(gy, gy + sg * GOAL_D), CX + sx * GOAL_W + 0.08, max(gy, gy + sg * GOAL_D)), "p")
        w.grid.add_rect((CX - GOAL_W, gy + sg * GOAL_D - 0.05 if sg > 0 else gy - GOAL_D - 0.05, CX + GOAL_W, gy + sg * GOAL_D + 0.05 if sg > 0 else gy - GOAL_D + 0.05), "p")
    w.stadium_sign = (gx - 1.27, CY, 8.1)


def add_signs(game):
    """text on the gate (and the big board inside) - real text, no glow"""
    w = game.world; gx, gy, gz = w.stadium_sign
    root = game.app.render.attach_new_node("sfc-signs")
    for txt, pos, h, sc, col in (("EX SPORTS SFC 27 STADIUM", (gx - 0.03, gy, gz - 0.25), -90, 0.95, (1, 1, 1, 1)),
                                 ("EX SPORTS SFC 27", (CX, CY + HL + 4.5 + 8.25, 9.2), 0, 2.6, (1, 1, 1, 1)),
                                 ("EX SPORTS SFC 27", (CX, CY - HL - 4.5 - 8.25, 9.2), 180, 2.6, (1, 1, 1, 1))):
        tn = TextNode("sfc"); tn.set_text(txt); tn.set_align(TextNode.A_center); tn.set_text_color(*col)
        if U.FONT: tn.set_font(U.FONT)
        n = root.attach_new_node(tn); n.set_pos(*pos); n.set_h(h); n.set_scale(sc); n.set_light_off(); n.set_shader_off()
    # scoreboard frames behind both goals (dark boards the text sits on)
    mb = MB("boards")
    for sg in (-1, 1):
        y = CY + sg * (HL + 4.5 + 8.5)
        mb.box(CX - 12, y - 0.2, 7.0, CX + 12, y + 0.2, 12.5, (0.05, 0.06, 0.1, 1))
        for sx in (-1, 1): mb.box(CX + sx * 10 - 0.3, y - 0.3, 0, CX + sx * 10 + 0.3, y + 0.3, 7.0, (0.5, 0.52, 0.55, 1))
    b = mb.node(); b.reparent_to(root)
    try:
        import xs_shaders; xs_shaders.apply(b, game.app, gloss=0.2)
        from panda3d.core import Material; mt = Material("b"); mt.set_base_color((1, 1, 1, 1)); b.set_material(mt, 1)
    except Exception: pass
    game.sfc_signs = root
    return root


# ====================================================================== match
class FP:
    """one footballer"""
    def __init__(self, team, idx, role, home, name, number):
        self.team, self.idx, self.role, self.home, self.name, self.number = team, idx, role, home, name, number
        self.x = self.y = 0.0; self.vx = self.vy = 0.0; self.h = 0.0; self.spd = 0.0
        self.human = None; self.person = None; self.own_person = False
        self.stamina = 1.0; self.tackle_cd = 0.0; self.kick_cd = 0.0; self.stun = 0.0; self.kick_t = 0.0; self.think = 0.0
        self.goal_v = None; self.lunge = 0.0; self.inp = {"mv": (0.0, 0.0), "sp": False}; self.acts = []
        self.ai_target = None


class Match:
    """host / offline simulation (mode 'sim') or online client view (mode 'view')"""
    def __init__(self, game, home_club=0, away_club=1, minutes_real=0.0, online=None, versus=False, mode="sim", setup=None, autoplay=False, kits=None):
        self.g = game; self.app = game.app; self.mode = mode; self.online = online; self.versus = versus
        # v1.0.5.1: minutes_real 0 = UNLIMITED (the default): the clock counts up, no full-time whistle, you end it yourself
        self.secs = 0.0 if not minutes_real else max(20.0, minutes_real * 60.0); self.clock = 0.0; self.score = [0, 0]; self.ended_by = None
        self.clubs = [CLUBS[home_club % len(CLUBS)], CLUBS[away_club % len(CLUBS)]]; self.kits = kits; self.club_idx = (home_club, away_club)
        if mode == "sim": self._apply_kits(kits)
        self.root = self.app.render.attach_new_node("sfc-match"); self.fps = []; self.ball = [CX, CY, BALL_R]; self.bv = [0.0, 0.0, 0.0]
        self.owner = None; self.last_touch = None; self.state = "kickoff"; self.state_t = 2.0; self.kick_team = 0
        self.banner_txt = ""; self.banner_t = 0.0; self.events = []; self.done = False; self.result_ui = None; self.goals = []
        self.local = None; self.cam = None; self.snap_t = 0.0; self.sprint_btn = False; self.restart = None
        self.stats = {"passes": 0, "shots": 0, "tackles": 0, "goals": 0, "saves": 0}
        self._build_ball(); self._hide_world()
        if mode == "sim":
            self._make_teams()
            if autoplay and self.local is not None: self.local.human = None       # test / demo: the AI plays your slot too
        else: self._make_view(setup)
        self._hud(); self.kickoff(0, first=True)

    # ---------------- setup
    def _hide_world(self):
        self.hidden = []; g = self.g
        if hasattr(g, "close_overlay"): g.close_overlay()

    def _build_ball(self):
        from xs_avatar import Mesh, _put
        m = Mesh(); r = BALL_R
        m.blob((0, 0, 0), (r, r, r), (0.97, 0.97, 0.97), 16, 10)
        for k in range(12):            # dark panels
            a = k * 2.4; b = math.acos(1 - 2 * ((k + 0.5) / 12)); d = (math.sin(b) * math.cos(a), math.sin(b) * math.sin(a), math.cos(b))
            m.blob(tuple(r * 0.93 * c for c in d), (0.035, 0.035, 0.035), (0.08, 0.08, 0.1), 8, 5)
        self.ball_np = _put(self.root, "ball", m, self.app, 0.5, 0.0)
        sh = MB("bsh")
        for i in range(12):
            t0 = 2 * math.pi * i / 12; t1 = 2 * math.pi * (i + 1) / 12
            sh.quad((0, 0, 0), (0.14 * math.cos(t0), 0.14 * math.sin(t0), 0), (0.14 * math.cos(t1), 0.14 * math.sin(t1), 0), (0, 0, 0), (0, 0, 0, 0.35), n=(0, 0, 1))
        self.shadow = sh.node(); self.shadow.reparent_to(self.root); self.shadow.set_light_off(); self.shadow.set_transparency(TransparencyAttrib.M_alpha)
        self.shadow.set_shader_off(); self.shadow.set_depth_offset(2)
        ring = MB("ring")
        for i in range(24):
            t0 = 2 * math.pi * i / 24; t1 = 2 * math.pi * (i + 1) / 24
            for (r0, r1) in ((0.55, 0.68),):
                ring.quad((r0 * math.cos(t0), r0 * math.sin(t0), 0), (r1 * math.cos(t0), r1 * math.sin(t0), 0), (r1 * math.cos(t1), r1 * math.sin(t1), 0),
                          (r0 * math.cos(t1), r0 * math.sin(t1), 0), (1, 1, 1, 0.9), n=(0, 0, 1))
        self.ring = ring.node(); self.ring.reparent_to(self.root); self.ring.set_light_off(); self.ring.set_shader_off(); self.ring.set_two_sided(True)
        self.ring.set_transparency(TransparencyAttrib.M_alpha); self.ring.set_depth_offset(3)

    def _kit(self, team):
        c = self.clubs[team]
        return {"kit_top": c[2], "kit_bottom": c[3], "kit_socks": c[4] if len(c) > 4 else c[2]}

    def _apply_kits(self, kits):
        """kits: per team None (club colours) or "yellow" (all-yellow alternate kit). Two yellow teams can't play each other."""
        kits = list(kits or [None, None])
        if kits[0] == "yellow" and kits[1] == "yellow": kits[1] = None
        for t in (0, 1):
            c = self.clubs[t]
            if kits[t] == "yellow": self.clubs[t] = (c[0], c[1], YELLOW, YELLOW, YELLOW)
        if self.clubs[0][2] == self.clubs[1][2] or (kits[0] == "yellow" and sum(self.clubs[1][2]) > 1.9 and self.clubs[1][2][2] < 0.3):
            c = self.clubs[1]; self.clubs[1] = (c[0], c[1], c[3], c[2])            # clash: away team wears its second colours

    def _make_person(self, fp, cfg=None, who=None):
        import xs_avatar as A
        c = dict(cfg or A.preset(random.randrange(8))); c.update(self._kit(fp.team)); c["number"] = fp.number
        p = A.Avatar(self.g, c, fp.x, fp.y, fp.h)
        p.np.reparent_to(self.root); fp.person = p

    def slots(self):
        """the team sheet: who plays where (used to build the client view)"""
        return [{"team": f.team, "idx": f.idx, "role": f.role, "name": f.name, "num": f.number, "human": f.human,
                 "cfg": getattr(f.person, "cfg", None), "who": None if hasattr(f.person, "cfg") else f.person.who} for f in self.fps]

    def _make_teams(self):
        g = self.g; import xs_avatar as A
        humans = [("local", None)]
        fr = getattr(g, "online", None)
        friends = list(fr.ai_friends) if fr is not None else []
        remote = []
        if self.online is not None and fr is not None and fr.sess is not None and fr.sess.role == "host":
            remote = [(pid, p) for pid, p in fr.sess.peers.items()]
        names = list(AI_NAMES); random.shuffle(names)
        for team in (0, 1):
            for i, (u, v, role) in enumerate(SHAPE):
                fp = FP(team, i, role, (u, v), names.pop() if names else "AI", 1 if role == "GK" else i + 1)
                self.fps.append(fp)
        # place humans: local on home team as the forward (or midfield); remote friends on home (co-op) or alternate (versus)
        order = [6, 4, 3, 5, 1, 2]
        home_free = list(order); away_free = list(order)
        def take(team):
            lst = home_free if team == 0 else away_free
            return self.fps[team * len(SHAPE) + lst.pop(0)] if lst else None
        f = take(0); f.human = "local"; f.name = g.profile.get("name", "YOU"); self.local = f
        f.cfg = A.clean(dict(g.profile)); f.number = 10
        for k, (pid, p) in enumerate(remote):
            team = (k + 1) % 2 if self.versus else 0
            ff = take(team) or take(1 - team)
            if ff is None: break
            ff.human = pid; ff.name = p["name"]; ff.cfg = A.clean(p.get("cfg") or {})
        for k, a in enumerate(friends):          # BRING THEM IN friends play for your team
            ff = take(0)
            if ff is None: break
            ff.name = a.cfg["name"]; ff.cfg = dict(a.cfg)
        for fp in self.fps:
            if fp.person is None:
                if fp.human is None and not hasattr(fp, "cfg"):
                    fp.cfg = A.preset(random.randrange(8)); fp.cfg["name"] = fp.name
                self._make_person(fp, getattr(fp, "cfg", None))
        g.player = self.local.person

    def _make_view(self, setup):
        g = self.g; self.setup = setup; my = setup.get("you")
        self.clubs = [tuple(c) for c in setup.get("clubs", self.clubs)]; self.secs = setup.get("secs", self.secs)
        for s in setup["slots"]:
            fp = FP(s["team"], s["idx"], s["role"], (0, 0), s["name"], s["num"]); fp.human = s.get("human"); self.fps.append(fp)
            if fp.human == my:
                self.local = fp; self._make_person(fp, dict(g.profile)); g.player = fp.person
            else:
                self._make_person(fp, s.get("cfg"), s.get("who"))

    # ---------------- helpers
    def dir_of(self, team):
        return 1.0 if team == 0 else -1.0

    def to_world(self, team, u, v):
        d = self.dir_of(team); return CX + u * d, CY + v * d

    def opp_goal(self, team):
        return CX, CY + HL * self.dir_of(team)

    def own_goal(self, team):
        return CX, CY - HL * self.dir_of(team)

    def banner(self, txt, t=2.5):
        self.banner_txt = txt; self.banner_t = t
        if hasattr(self, "ban"): self.ban.setText(txt)

    # ---------------- restarts
    def kickoff(self, team, first=False):
        self.state = "kickoff"; self.state_t = 2.2 if not first else 3.0; self.kick_team = team; self.owner = None
        self.ball = [CX, CY, BALL_R]; self.bv = [0.0, 0.0, 0.0]
        for f in self.fps:
            u, v = f.home; v = min(v * 0.9, -1.5)
            if f.team == team and f.role == "FW": u, v = 0.0, -0.4
            if f.team == team and f.idx == 4: u, v = -4.0, -2.0
            f.x, f.y = self.to_world(f.team, u, v); f.vx = f.vy = 0.0
            f.h = 0.0 if f.team == 0 else 180.0; f.stun = 0.0
        self.banner("KICK OFF" if not first else "%s  vs  %s" % (self.clubs[0][0], self.clubs[1][0]), 2.0)
        self.app.sfx("checkpoint", 0.5) if hasattr(self.app, "sfx") else None

    def set_restart(self, team, x, y, label):
        """throw-in / goal kick / corner: the nearest player of `team` takes it"""
        self.owner = None; self.bv = [0.0, 0.0, 0.0]; self.ball = [x, y, BALL_R]
        cand = [f for f in self.fps if f.team == team and (f.role != "GK" or label == "GOAL KICK")]
        if label == "GOAL KICK": cand = [f for f in self.fps if f.team == team and f.role == "GK"] or cand
        best = min(cand, key=lambda f: math.hypot(f.x - x, f.y - y))
        best.x, best.y = x - (x - CX) * 0.02, y - (y - CY) * 0.01
        self.state = "restart"; self.state_t = 0.9; self.restart = best; self.banner(label, 1.2)

    # ---------------- input
    def key(self, k):
        """keys while the match runs (True = consumed)"""
        if self.mode == "sim" and self.local is None: return False
        if k == "escape":
            return False
        if k == "space": self.act("pass"); return True
        if k == "f": self.act("shoot"); return True
        if k == "r": self.act("tackle"); return True
        if k in ("q", "e", "c", "h", "m", "t", "b", "n", "l", "j", "1", "2", "3", "enter", "arrow_up", "f2"): return True
        return False

    def act(self, a):
        if self.done: return
        if self.mode == "view":
            self.g.online.fb_input(act=a); return
        if self.local is not None: self.local.acts.append(a)

    def local_input(self):
        g = self.g; up = g.down("w", "arrow_up", "v_up"); dn = g.down("s", "arrow_down", "v_down")
        lf = g.down("a", "arrow_left", "v_left"); rt = g.down("d", "arrow_right", "v_right")
        sp = g.down("shift", "v_nitro") or self.sprint_btn
        team = self.local.team if self.local else 0; d = self.dir_of(team)
        mx = (rt - lf) * d; my = (up - dn) * d
        L = math.hypot(mx, my)
        if L > 0: mx, my = mx / L, my / L
        return (mx, my), bool(sp)

    # ---------------- simulation
    def step(self, dt):
        dt = min(dt, 0.05)
        if self.mode == "view":
            self._view_step(dt); return
        if self.local is not None:
            mv, sp = self.local_input(); self.local.inp = {"mv": mv, "sp": sp}
        if self.state not in ("fulltime",):
            if self.state in ("play", "restart"): self.clock += dt
            if self.secs and self.clock >= self.secs and self.state == "play": self.full_time()
        if self.state == "kickoff":
            self.state_t -= dt
            if self.state_t <= 0:
                self.state = "play"; ft = [f for f in self.fps if f.team == self.kick_team and f.role == "FW"][0]; self.owner = ft
                self.app.sfx("whistle", 0.6) if "whistle" in getattr(self.app, "sfx_names", ()) else None
        elif self.state == "restart":
            self.state_t -= dt; r = self.restart
            if r is not None: r.vx = r.vy = 0.0
            if self.state_t <= 0: self.state = "play"; self.owner = r; self.restart = None
        elif self.state == "goal":
            self.state_t -= dt
            if self.state_t <= 0: self.kickoff(1 - self.goals[-1][0])
        elif self.state == "fulltime":
            self.state_t -= dt
        for f in self.fps: self._player(f, dt)
        self._ball(dt)
        self._separate()
        self._sync(dt)
        self._camera(dt)
        self._hud_update(dt)
        if self.online is not None: self.online.fb_tick(self, dt)

    def _speed(self, f, sprint):
        base = 5.6 if f.role != "GK" else 5.0
        if sprint and f.stamina > 0.05: base = 7.6
        return base * (1.0 if f.human else 0.97)

    def _player(self, f, dt):
        f.tackle_cd = max(0.0, f.tackle_cd - dt); f.kick_cd = max(0.0, f.kick_cd - dt); f.kick_t = max(0.0, f.kick_t - dt)
        f.lunge = max(0.0, f.lunge - dt)
        if self.state in ("kickoff", "goal", "fulltime") or (self.state == "restart"):
            f.vx *= 0.8; f.vy *= 0.8
            if self.state == "goal" or self.state == "fulltime":
                f.x += f.vx * dt; f.y += f.vy * dt
            f.spd = math.hypot(f.vx, f.vy); return
        if f.stun > 0:
            f.stun -= dt; f.vx *= 0.9; f.vy *= 0.9; f.x += f.vx * dt; f.y += f.vy * dt; f.spd = math.hypot(f.vx, f.vy); return
        if f.human is not None:
            (mx, my), sp = f.inp.get("mv", (0, 0)), f.inp.get("sp", False)
            for a in f.acts: self._do(f, a)
            f.acts = []
            tx, ty = mx, my
        else:
            tx, ty, sp = self._ai(f, dt)
        spd = self._speed(f, sp) * (1.6 if f.lunge > 0 else 1.0)
        if self.owner is f: spd *= 0.9
        moving = math.hypot(tx, ty) > 0.05
        f.stamina = max(0.0, min(1.0, f.stamina + (-0.12 if (sp and moving) else 0.08) * dt))
        ax = tx * spd - f.vx; ay = ty * spd - f.vy; k = min(1.0, dt * (7.0 if f.human else 6.0))
        f.vx += ax * k; f.vy += ay * k
        f.x += f.vx * dt; f.y += f.vy * dt
        f.x = max(CX - HW - 3.5, min(CX + HW + 3.5, f.x)); f.y = max(CY - HL - 3.5, min(CY + HL + 3.5, f.y))
        f.spd = math.hypot(f.vx, f.vy)
        if f.spd > 0.3: 
            th = math.degrees(math.atan2(-f.vx, f.vy)); dh = (th - f.h + 180) % 360 - 180; f.h += dh * min(1.0, dt * 10)

    def _facing(self, f):
        r = math.radians(f.h); return -math.sin(r), math.cos(r)

    # actions -------------------------------------------------------------
    def _do(self, f, a):
        if a == "pass" and self.owner is f:
            mv = f.inp.get("mv", (0, 0)) if f.human else (0, 0)
            d = mv if math.hypot(*mv) > 0.1 else self._facing(f)
            t = self._pick_pass(f, d)
            if t is not None: self._pass(f, t)
            else: self._kick(f, d[0], d[1], 16.0, 0.5)
        elif a == "shoot" and self.owner is f:
            self._shoot(f)
        elif a == "tackle":
            self._tackle(f)

    def _kick(self, f, dx, dy, speed, up):
        L = math.hypot(dx, dy) or 1.0
        self.owner = None; self.last_touch = f.team; f.kick_cd = 0.35; f.kick_t = 0.3
        self.ball[0] = f.x + dx / L * 0.6; self.ball[1] = f.y + dy / L * 0.6
        self.bv = [dx / L * speed, dy / L * speed, up]
        self.app.sfx("bump", 0.35) if hasattr(self.app, "sfx") else None

    def _pass(self, f, t):
        lead = 0.45 if t.spd > 1 else 0.0
        tx, ty = t.x + t.vx * lead, t.y + t.vy * lead
        d = math.hypot(tx - f.x, ty - f.y)
        sp = max(9.0, min(24.0, 6.0 + d * 0.62)); up = 0.6 if d < 22 else 3.5 + d * 0.06
        self._kick(f, tx - f.x, ty - f.y, sp, up); self.stats["passes"] += 1

    def _pick_pass(self, f, d):
        best, bs = None, -1e9
        for t in self.fps:
            if t is f or t.team != f.team: continue
            dx, dy = t.x - f.x, t.y - f.y; dist = math.hypot(dx, dy)
            if dist < 3 or dist > 45: continue
            ali = (dx * d[0] + dy * d[1]) / dist
            if ali < 0.35: continue
            fwd = (t.y - f.y) * self.dir_of(f.team)
            block = min([self._seg_dist(o.x, o.y, f.x, f.y, t.x, t.y) for o in self.fps if o.team != f.team] or [99])
            s = ali * 22 + fwd * 0.25 - dist * 0.12 + min(block, 6) * 2.0
            if s > bs: best, bs = t, s
        return best

    @staticmethod
    def _seg_dist(px, py, ax, ay, bx, by):
        dx, dy = bx - ax, by - ay; L2 = dx * dx + dy * dy or 1.0
        t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
        return math.hypot(px - ax - dx * t, py - ay - dy * t)

    def _shoot(self, f):
        gx, gy = self.opp_goal(f.team); dist = math.hypot(gx - f.x, gy - f.y)
        mv = f.inp.get("mv", (0, 0)) if f.human else (0, 0)
        side = mv[0] * self.dir_of(f.team) if f.human and abs(mv[0]) > 0.2 else random.choice((-1, 1))
        aim = side * random.uniform(1.6, 3.2) + random.gauss(0, 0.4 + dist * 0.04)
        tx = gx + aim * (1 if f.team == 0 else -1) * self.dir_of(f.team)
        sp = min(30.0, 20.0 + dist * 0.25); up = 1.2 + dist * 0.09 + random.uniform(-0.6, 1.2)
        self._kick(f, tx - f.x, gy - f.y, sp, up); self.stats["shots"] += 1
        self.shot_by = f

    def _tackle(self, f):
        if f.tackle_cd > 0: return
        f.tackle_cd = 1.1
        o = self.owner
        if o is not None and o.team != f.team and math.hypot(o.x - f.x, o.y - f.y) < 2.1:
            p = 0.55 + (0.2 if f.human else 0.0) - (0.15 if o.human else 0.0)
            if random.random() < p:
                self.owner = f; self.last_touch = f.team; o.stun = 0.7; self.stats["tackles"] += 1
                self.app.sfx("bump", 0.5) if hasattr(self.app, "sfx") else None
            else:
                f.stun = 0.5
        else:
            f.lunge = 0.45
            if self.owner is None and math.hypot(self.ball[0] - f.x, self.ball[1] - f.y) < 2.2:
                self.owner = f; self.last_touch = f.team

    # AI ------------------------------------------------------------------
    def _ai(self, f, dt):
        team = f.team; d = self.dir_of(team); bx, by = self.ball[0], self.ball[1]; own = self.owner
        we_have = own is not None and own.team == team
        if f.role == "GK": return self._gk(f, dt)
        if own is f:
            f.think -= dt
            gx, gy = self.opp_goal(team); dg = math.hypot(gx - f.x, gy - f.y)
            near = min([math.hypot(o.x - f.x, o.y - f.y) for o in self.fps if o.team != team] or [99])
            if f.think <= 0:
                f.think = random.uniform(0.25, 0.5)
                if dg < 26 and (random.random() < (0.35 if dg > 18 else 0.75)): self._shoot(f); return 0, 0, False
                if near < 3.2 and random.random() < 0.6 or random.random() < 0.08:
                    t = self._pick_pass(f, ((gx - f.x) / max(dg, 1), (gy - f.y) / max(dg, 1)))
                    if t is None: t = self._pick_pass(f, self._facing(f))
                    if t is not None: self._pass(f, t); return 0, 0, False
            dx, dy = gx - f.x, gy - f.y; L = math.hypot(dx, dy) or 1; dx /= L; dy /= L
            for o in self.fps:
                if o.team == team: continue
                ox, oy = o.x - f.x, o.y - f.y; od = math.hypot(ox, oy)
                if od < 6 and (ox * dx + oy * dy) > 0:
                    side = 1 if (ox * dy - oy * dx) > 0 else -1          # steer around the defender
                    dx += -dy * side * 0.8 * (6 - od) / 6; dy += dx * side * 0.8 * (6 - od) / 6
            L = math.hypot(dx, dy) or 1
            return dx / L, dy / L, near < 4
        # chase or hold shape
        chasers = self._chasers(team)
        if f in chasers:
            px, py = bx + self.bv[0] * 0.35, by + self.bv[1] * 0.35
            dx, dy = px - f.x, py - f.y; L = math.hypot(dx, dy)
            if own is not None and own.team != team and L < 1.9 and f.tackle_cd <= 0 and random.random() < dt * 2.5: self._tackle(f)
            if L < 0.2: return 0, 0, False
            return dx / L, dy / L, L > 6
        u, v = f.home; bu, bv = (bx - CX) * d, (by - CY) * d
        tv = v + bv * 0.5 + (10 if we_have else -2); tu = u + bu * 0.3
        tv = max(-HL + 4, min(HL - 6, tv)); tu = max(-HW + 2, min(HW - 2, tu))
        tx, ty = self.to_world(team, tu, tv); dx, dy = tx - f.x, ty - f.y; L = math.hypot(dx, dy)
        if L < 1.0: return 0, 0, False
        k = min(1.0, L / 6.0)
        return dx / L * k, dy / L * k, L > 14

    def _chasers(self, team):
        cand = sorted([f for f in self.fps if f.team == team and f.role != "GK"], key=lambda f: math.hypot(f.x - self.ball[0], f.y - self.ball[1]))
        own = self.owner
        n = 2 if own is not None and own.team != team else 1
        out = []
        for f in cand:
            if f.human is not None: n -= 1; continue          # a human near the ball counts as the presser
            out.append(f)
            if len(out) >= max(0, n): break
        return out if n > 0 else []

    def _gk(self, f, dt):
        team = f.team; gx, gy = self.own_goal(team); d = self.dir_of(team)
        bx, by = self.ball[0], self.ball[1]
        if self.owner is f:
            f.think -= dt
            if f.think <= 0:
                t = self._pick_pass(f, (0, d)) or max([o for o in self.fps if o.team == team and o is not f], key=lambda o: (o.y - f.y) * d)
                self._pass(f, t)
            return 0, 0, False
        dist = math.hypot(bx - gx, by - gy)
        loose = self.owner is None and dist < 15 and abs(bx - CX) < 20
        if loose and (self.bv[1] * -d > -1.0):
            dx, dy = bx - f.x, by - f.y; L = math.hypot(dx, dy) or 1
            return dx / L, dy / L, True
        tu = max(-GOAL_W + 0.4, min(GOAL_W - 0.4, (bx - CX) * 0.2)); ty = gy + d * (1.2 + min(4.0, dist * 0.05))
        dx, dy = CX + tu - f.x, ty - f.y; L = math.hypot(dx, dy)
        if L < 0.15: return 0, 0, False
        k = min(1.0, L / 2.0); return dx / L * k, dy / L * k, L > 3

    # ball physics -------------------------------------------------------------
    def _ball(self, dt):
        b, v = self.ball, self.bv
        if self.state in ("kickoff",):
            return
        if self.owner is not None and self.state in ("play", "restart"):
            o = self.owner; fx, fy = self._facing(o)
            b[0] = o.x + fx * 0.55; b[1] = o.y + fy * 0.55; b[2] = BALL_R; v[0], v[1], v[2] = o.vx, o.vy, 0.0
            self.last_touch = o.team
            self.roll = getattr(self, "roll", 0.0) + o.spd * dt / BALL_R * 57.3
            return
        b[0] += v[0] * dt; b[1] += v[1] * dt; b[2] += v[2] * dt
        if b[2] > BALL_R + 0.01 or v[2] > 0:
            v[2] -= 9.81 * dt; v[0] *= math.exp(-0.05 * dt); v[1] *= math.exp(-0.05 * dt)
        if b[2] < BALL_R:
            b[2] = BALL_R
            if v[2] < -1.5: v[2] = -v[2] * 0.5; v[0] *= 0.85; v[1] *= 0.85
            else:
                v[2] = 0.0; sp = math.hypot(v[0], v[1])
                if sp > 0:
                    ns = max(0.0, sp - (1.2 + 0.35 * sp) * dt); v[0] *= ns / sp; v[1] *= ns / sp
        self.roll = getattr(self, "roll", 0.0) + math.hypot(v[0], v[1]) * dt / BALL_R * 57.3
        if self.state == "goal":            # the net catches it
            for sg in (-1, 1):
                gy = CY + sg * HL
                if (b[1] - gy) * sg > 0 and abs(b[0] - CX) < GOAL_W + 0.2:
                    if (b[1] - gy) * sg > GOAL_D - 0.15: b[1] = gy + sg * (GOAL_D - 0.15); v[1] = -v[1] * 0.15; v[0] *= 0.4
                    if abs(b[0] - CX) > GOAL_W - 0.12: b[0] = CX + math.copysign(GOAL_W - 0.12, b[0] - CX); v[0] = -v[0] * 0.2
                    if b[2] > GOAL_H - 0.12: b[2] = GOAL_H - 0.12; v[2] = -abs(v[2]) * 0.2
            return
        if self.state != "play": return
        # goal / out of play
        for sg in (-1, 1):
            gy = CY + sg * HL
            if (b[1] - gy) * sg > 0:
                if abs(b[0] - CX) < GOAL_W - BALL_R and b[2] < GOAL_H - BALL_R:
                    self.goal(0 if sg > 0 else 1); return
                if abs(b[0] - CX) < GOAL_W + 0.1 and b[2] < GOAL_H + 0.15:       # off the post / bar
                    v[1] = -v[1] * 0.6; b[1] = gy - sg * 0.15; return
                att = 0 if sg > 0 else 1                       # team attacking this end
                if self.last_touch == att:
                    self.set_restart(1 - att, CX + math.copysign(9.0, b[0] - CX), gy - sg * 5.5, "GOAL KICK")
                else:
                    self.set_restart(att, CX + math.copysign(HW - 0.4, b[0] - CX), gy - sg * 0.4, "CORNER")
                return
        if abs(b[0] - CX) > HW:
            self.set_restart(1 - (self.last_touch if self.last_touch is not None else 0), CX + math.copysign(HW - 0.3, b[0] - CX),
                             max(CY - HL + 1, min(CY + HL - 1, b[1])), "THROW IN"); return
        # pick up / intercept / keeper save
        sp = math.hypot(v[0], v[1])
        best = None
        for f in self.fps:
            if f.kick_cd > 0 or f.stun > 0: continue
            dx, dy = b[0] - f.x, b[1] - f.y; dist = math.hypot(dx, dy)
            reach = 0.85 if f.role != "GK" else 1.7
            hz = 1.3 if f.role != "GK" else 2.5
            if dist < reach and b[2] < hz:
                if f.role == "GK" and abs(f.y - CY) > HL - 18 and sp > 6:
                    if random.random() < 0.72:
                        self.stats["saves"] += 1; self.banner("SAVE!  %s" % f.name, 1.3)
                    else:
                        v[0] = -v[0] * 0.35 + random.uniform(-4, 4); v[1] = -v[1] * 0.35; v[2] = abs(v[2]) * 0.3 + 2.0
                        f.kick_cd = 0.6; self.last_touch = f.team; continue
                elif sp > 17 and random.random() > 0.35:
                    continue            # too hot to control
                if best is None or dist < best[0]: best = (dist, f)
        if best is not None:
            self.owner = best[1]; self.last_touch = best[1].team

    def goal(self, team):
        self.score[team] += 1; self.state = "goal"; self.state_t = 3.2; self.owner = None
        sc = getattr(self, "shot_by", None); who = sc.name if sc is not None and sc.team == team else "OWN GOAL"
        self.goals.append((team, who, int(self.minute()))); self.stats["goals"] += 1
        self.banner("GOAL!  %s  -  %s" % (self.clubs[team][0], who), 3.0)
        self.app.sfx("checkpoint", 0.9) if hasattr(self.app, "sfx") else None
        for f in self.fps:                # scorers celebrate, the others jog back
            if f.team == team: r = random.uniform(0, 6.28); f.vx, f.vy = math.cos(r) * 3, math.sin(r) * 3

    def unlimited(self):
        return not self.secs

    def minute(self):
        if self.unlimited(): return self.clock / 60.0
        return min(90.0, self.clock / self.secs * 90.0)

    def clock_text(self):
        if self.unlimited():
            c = int(self.clock); return "%d:%02d" % (c // 60, c % 60)
        return "%d'" % int(self.minute())

    def end_match(self):
        """END MATCH (offline / host: final score for everyone) or LEAVE MATCH (online guest: AI takes the slot)"""
        if self.done: return
        if self.mode == "view":
            self.done = True; self.state = "fulltime"; self.ended_by = "left"
            try: self.g.online.fb_leave()
            except Exception: pass
            self._result(); return
        self.ended_by = "ended"; self.full_time()

    def full_time(self):
        self.state = "fulltime"; self.state_t = 4.0; self.owner = None; self.done = True
        s = self.score
        res = "DRAW" if s[0] == s[1] else ("%s WIN" % self.clubs[0 if s[0] > s[1] else 1][0])
        self.banner("%s  %d - %d   %s" % ("FINAL SCORE" if self.ended_by else "FULL TIME", s[0], s[1], res), 99)
        print("SFC FULLTIME", s, self.goals, self.stats, flush=True)
        self.app.sfx("checkpoint", 0.8) if hasattr(self.app, "sfx") else None
        self._result()

    def _separate(self):
        fs = self.fps
        for i in range(len(fs)):
            a = fs[i]
            for j in range(i + 1, len(fs)):
                b = fs[j]; dx, dy = b.x - a.x, b.y - a.y; d2 = dx * dx + dy * dy
                if 1e-6 < d2 < 0.49:
                    d = math.sqrt(d2); p = (0.7 - d) * 0.5; dx /= d; dy /= d
                    a.x -= dx * p; a.y -= dy * p; b.x += dx * p; b.y += dy * p

    def _sync(self, dt):
        for f in self.fps:
            p = f.person
            if p is None: continue
            p.x, p.y, p.h = f.x, f.y, f.h; p.np.set_pos(f.x, f.y, 0.04); p.np.set_h(f.h)
            p.walk_anim(dt, f.spd)
            if f.kick_t > 0 and not p.legR.is_empty():
                k = math.sin((0.3 - f.kick_t) / 0.3 * math.pi); p.legR.set_p(-70 * k + 20 * (1 - k))
            if f.stun > 0: p.model.set_p(-25)
        b = self.ball
        self.ball_np.set_pos(b[0], b[1], b[2] + 0.04); self.ball_np.set_p(-getattr(self, "roll", 0.0))
        self.ball_np.set_h(math.degrees(math.atan2(-self.bv[0], self.bv[1])) if math.hypot(self.bv[0], self.bv[1]) > 0.2 else self.ball_np.get_h())
        self.shadow.set_pos(b[0], b[1], 0.05)
        if self.local is not None:
            c = self.clubs[self.local.team][2]
            self.ring.set_pos(self.local.x, self.local.y, 0.06); self.ring.set_color_scale(c[0], c[1], c[2], 1)

    def _camera(self, dt):
        cam = self.app.camera
        f = self.local
        if f is None: fx, fy, d = self.ball[0], self.ball[1], 1.0
        else: fx, fy, d = f.x, f.y, self.dir_of(f.team)
        bx, by = self.ball[0], self.ball[1]
        tx = fx * 0.55 + bx * 0.45; ty = fy * 0.55 + by * 0.45
        want = (tx, ty - d * 15.0, 8.0)
        if self.cam is None: self.cam = list(want)
        k = min(1.0, dt * 3.0)
        for i in range(3): self.cam[i] += (want[i] - self.cam[i]) * k
        cam.set_pos(*self.cam); cam.look_at(tx, ty + d * 9.0, 0.0); self.app.camLens.set_fov(getattr(self.app, "settings", {}).get("fov", 60))

    # ---------------- HUD
    def _hud(self):
        a = self.app; r = self.hud = DirectFrame(parent=a.a2dTopCenter, frameColor=(0, 0, 0, 0))
        U.panel(r, -0.62, 0.62, -0.135, -0.025, edge=(0.95, 0.35, 0.62, 1))
        self.sb = U.text(r, "", (0, -0.1), 0.05, fg=(1, 1, 1, 1))
        self.ban = U.text(a.aspect2d, "", (0, 0.42), 0.075, fg=(1, 0.9, 0.3, 1), shadow=(0, 0, 0, 1)); self.ban.reparent_to(r)
        self.ban.set_pos(0, 0, -0.45)
        bot = self.bot = DirectFrame(parent=a.a2dBottomCenter, frameColor=(0, 0, 0, 0))
        sm = dict(w=0.12, h=0.045, scale=0.032)
        U.button(bot, "PASS", (-0.42, 0.1), lambda: self.act("pass"), hint="Space", edge=(0.3, 0.9, 1.0, 1), **sm)
        U.button(bot, "SHOOT", (-0.14, 0.1), lambda: self.act("shoot"), hint="F", edge=(1.0, 0.5, 0.2, 1), **sm)
        U.button(bot, "TACKLE", (0.14, 0.1), lambda: self.act("tackle"), hint="R", edge=(1.0, 0.3, 0.3, 1), **sm)
        U.button(bot, "SPRINT", (0.42, 0.1), None, hint="Shift", edge=(0.4, 1.0, 0.5, 1),
                 press=lambda: setattr(self, "sprint_btn", True), release=lambda: setattr(self, "sprint_btn", False), **sm)
        U.button(bot, "LEAVE MATCH" if self.mode == "view" else "END MATCH", (0, 0.22), self.end_match, hint="Esc menu", w=0.16, h=0.035, scale=0.026, edge=(1.0, 0.75, 0.3, 1))
        self.help = U.text(bot, "WASD move   SPACE pass   F shoot   R tackle   SHIFT sprint", (0, 0.29), 0.028, fg=(1, 1, 1, 0.85), font=U.FONT_PLAIN, shadow=(0, 0, 0, 1))
        self.stam = U.bar(bot, (-0.2, 0.035), 0.4, 0.008, 1.0, col=(0.4, 1.0, 0.5, 1))

    def _hud_update(self, dt):
        c0, c1 = self.clubs
        m = self.minute()
        self.sb.setText("%s  %d - %d  %s     %s" % (c0[1], self.score[0], self.score[1], c1[1], self.clock_text()))
        if self.banner_t > 0:
            self.banner_t -= dt
            if self.banner_t <= 0: self.ban.setText("")
        if self.local is not None: self.stam[1].set_sx(max(0.001, self.local.stamina))

    def _result(self):
        if self.result_ui is not None: return
        a = self.app; o = self.result_ui = DirectFrame(parent=a.aspect2d, frameColor=(0, 0, 0, 0.35), frameSize=(-4, 4, -2, 2))
        U.panel(o, -0.75, 0.75, -0.42, 0.3, edge=(0.95, 0.35, 0.62, 1))
        U.text(o, {"ended": "FINAL SCORE", "left": "YOU LEFT THE MATCH"}.get(self.ended_by, "FULL TIME"), (0, 0.2), 0.07, fg=(1, 0.9, 0.3, 1))
        if self.unlimited(): U.text(o, "played %s" % self.clock_text(), (0, 0.145), 0.03, fg=(0.85, 0.9, 1, 1), font=U.FONT_PLAIN)
        U.text(o, "%s  %d - %d  %s" % (self.clubs[0][0], self.score[0], self.score[1], self.clubs[1][0]), (0, 0.1), 0.042, font=U.FONT_PLAIN)
        sc = ",  ".join("%s %d'" % (w, mn) for (t, w, mn) in self.goals[:8]) or "no goals"
        U.text(o, sc, (0, 0.02), 0.03, fg=(0.85, 0.9, 1, 1), font=U.FONT_PLAIN, wrap=44)
        if self.mode == "sim":
            U.button(o, "PLAY AGAIN", (-0.3, -0.25), self.again, w=0.2, h=0.05, scale=0.035, edge=(0.3, 1.0, 0.45, 1))
        U.button(o, "LEAVE STADIUM", (0.3 if self.mode == "sim" else 0, -0.25), self.quit, w=0.2, h=0.05, scale=0.035)

    def again(self):
        g = self.g; args = dict(home_club=self.club_idx[0], away_club=self.club_idx[1], minutes_real=self.secs / 60.0,
                                online=self.online, versus=self.versus, kits=self.kits)
        self.quit(again=True); g.start_match(**args)

    def quit(self, again=False):
        g = self.g
        if self.online is not None and self.mode == "sim": self.online.fb_end(self)
        for f in self.fps:
            if f.person is not None: f.person.destroy(); f.person = None
        for n in (self.hud, self.bot, self.result_ui):
            if n is not None: n.destroy()
        self.root.remove_node(); g.match = None; g.player = None
        self.app.camLens.set_fov(getattr(self.app, "settings", {}).get("fov", 60))
        g.match_over(again)

    # ---------------- online snapshot (host -> clients)
    def snapshot(self):
        r = lambda v: round(v, 2)
        return {"c": r(self.clock), "s": self.score, "st": self.state, "b": [r(x) for x in self.ball],
                "p": [[r(f.x), r(f.y), int(f.h), r(f.spd), 1 if f.kick_t > 0 else 0, 1 if f.stun > 0 else 0] for f in self.fps],
                "bn": self.banner_txt if self.banner_t > 0 else "", "g": self.goals[-6:], "eb": self.ended_by}

    def apply_snapshot(self, s):
        self.target = s

    def _view_step(self, dt):
        s = getattr(self, "target", None)
        if self.local is not None:
            mv, sp = self.local_input(); self.g.online.fb_input(mv=mv, sp=sp)
        if s is not None:
            self.clock = s["c"]; self.score = s["s"]; self.goals = [tuple(x) for x in s.get("g", [])]
            k = min(1.0, dt * 12)
            for f, p in zip(self.fps, s["p"]):
                f.x += (p[0] - f.x) * k; f.y += (p[1] - f.y) * k
                dh = (p[2] - f.h + 180) % 360 - 180; f.h += dh * k; f.spd = p[3]; f.kick_t = 0.2 if p[4] else 0.0; f.stun = 0.3 if p[5] else 0.0
            for i in range(3): self.ball[i] += (s["b"][i] - self.ball[i]) * k
            if s.get("bn") and s["bn"] != self.banner_txt: self.banner(s["bn"], 2.5)
            if s.get("st") == "fulltime" and not self.done:
                self.done = True; self.state = "fulltime"; self.ended_by = s.get("eb")
                self.banner("%s  %d - %d" % (("FINAL SCORE" if self.ended_by else "FULL TIME"),) + tuple(self.score), 99); self._result()
        self._sync(dt); self._camera(dt); self._hud_update(dt)
