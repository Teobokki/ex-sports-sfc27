"""v1.0.5 SHINE ONLINE friend avatars: procedural, original characters for online friends and AI friends.

They never reuse ANA's or DANIEL's meshes, faces or outfits: every avatar is built here from smooth primitives (body,
face, hair style, clothes, accessories) with the same node layout as the crew (armL/armR -> foreL/foreR -> handL/handR with
fingers/fist, legL/legR), so walking, running, driving and football poses come from the shared Person animation code."""
import math, random
import numpy as np
from panda3d.core import NodePath, TextNode
from xs_person import Person
from xs_mesh import mesh_node, shade

SKINS = [("PORCELAIN", (0.96, 0.82, 0.72)), ("PEACH", (0.93, 0.74, 0.6)), ("HONEY", (0.85, 0.62, 0.45)), ("OLIVE", (0.74, 0.56, 0.4)),
         ("TAN", (0.66, 0.46, 0.32)), ("BROWN", (0.5, 0.33, 0.22)), ("DEEP", (0.34, 0.22, 0.15)), ("EBONY", (0.24, 0.16, 0.11))]
HAIRS = ["buzz", "afro", "ponytail", "mohawk", "buns", "curly", "long", "spiky"]
ARENA_HAIRS = ["bob", "braids", "bun", "pixie"]          # v1.0.0.5: SFC 27 ARENA women players (not in the avatar editor)
HAIR_COLS = [("BLACK", (0.05, 0.045, 0.045)), ("BROWN", (0.25, 0.15, 0.08)), ("AUBURN", (0.45, 0.16, 0.07)), ("BLONDE", (0.85, 0.7, 0.4)),
             ("SILVER", (0.78, 0.8, 0.82)), ("TEAL", (0.1, 0.6, 0.6)), ("PINK", (0.95, 0.45, 0.65)), ("PURPLE", (0.45, 0.2, 0.7))]
TOPS = ["hoodie", "jersey", "jacket", "tee", "vest"]
COLS = [("WHITE", (0.92, 0.92, 0.9)), ("BLACK", (0.08, 0.08, 0.09)), ("RED", (0.8, 0.12, 0.12)), ("ORANGE", (0.95, 0.5, 0.1)),
        ("YELLOW", (0.95, 0.82, 0.15)), ("GREEN", (0.15, 0.6, 0.3)), ("TEAL", (0.1, 0.6, 0.62)), ("BLUE", (0.15, 0.35, 0.8)),
        ("NAVY", (0.08, 0.12, 0.3)), ("PURPLE", (0.45, 0.2, 0.7)), ("PINK", (0.95, 0.5, 0.7)), ("GREY", (0.5, 0.5, 0.52)),
        ("KHAKI", (0.62, 0.55, 0.38)), ("DENIM", (0.25, 0.35, 0.55))]
ACCS = ["none", "glasses", "cap", "headphones", "beanie"]

# 8 presets - all original, clearly different from ANA (black bob, tank top, red slacks) and DANIEL (floral shirt)
PRESETS = [
    dict(name="KAITO", skin=2, hair="spiky", hair_col=0, top="hoodie", top_col=7, bottom_col=1, acc="headphones", build=1.0),
    dict(name="RIN", skin=0, hair="buns", hair_col=6, top="jacket", top_col=1, bottom_col=13, acc="none", build=0.93),
    dict(name="JUNO", skin=6, hair="afro", hair_col=0, top="tee", top_col=4, bottom_col=8, acc="glasses", build=0.97),
    dict(name="OBI", skin=7, hair="buzz", hair_col=0, top="jersey", top_col=5, bottom_col=0, acc="cap", build=1.05),
    dict(name="SORA", skin=1, hair="ponytail", hair_col=3, top="vest", top_col=10, bottom_col=11, acc="none", build=0.92),
    dict(name="LENA", skin=3, hair="long", hair_col=2, top="hoodie", top_col=9, bottom_col=1, acc="beanie", build=0.95),
    dict(name="TAKU", skin=4, hair="mohawk", hair_col=5, top="jacket", top_col=3, bottom_col=12, acc="none", build=1.02),
    dict(name="MAYA", skin=5, hair="curly", hair_col=1, top="tee", top_col=6, bottom_col=13, acc="glasses", build=0.94),
]


def preset(i):
    return dict(PRESETS[i % len(PRESETS)])


def clean(cfg):
    """validate a (possibly remote) avatar config: everything clamped to known values"""
    p = preset(0)
    if not isinstance(cfg, dict): return p
    out = dict(p)
    out["name"] = "".join(ch for ch in str(cfg.get("name", p["name"])).upper() if ch.isalnum() or ch in " -_")[:12] or p["name"]
    for k, n in (("skin", len(SKINS)), ("hair_col", len(HAIR_COLS)), ("top_col", len(COLS)), ("bottom_col", len(COLS))):
        try: out[k] = int(cfg.get(k, p[k])) % n
        except Exception: pass
    for k, opts in (("hair", HAIRS + ARENA_HAIRS), ("top", TOPS), ("acc", ACCS)):
        if cfg.get(k) in opts: out[k] = cfg[k]
    try: out["build"] = max(0.88, min(1.08, float(cfg.get("build", 1.0))))
    except Exception: pass
    if cfg.get("body") in ("M", "F"): out["body"] = cfg["body"]
    for k in ("kit_top", "kit_bottom", "skin_rgb", "hair_rgb"):
        v = cfg.get(k)
        if isinstance(v, (list, tuple)) and len(v) == 3: out[k] = tuple(max(0.0, min(1.0, float(x))) for x in v)
    if "number" in cfg:
        try: out["number"] = int(cfg["number"]) % 100
        except Exception: pass
    return out


class Mesh:
    """accumulate coloured ellipsoids / tubes into one GeomNode"""
    def __init__(self): self.V, self.N, self.C, self.T, self.tris = [], [], [], [], []

    def blob(self, c, r, col, seg=14, ring=9):
        cx, cy, cz = c; rx, ry, rz = r; base = len(self.V); col = tuple(col) + ((1,) if len(col) == 3 else ())
        for i in range(ring + 1):
            th = math.pi * i / ring
            for j in range(seg + 1):
                ph = 2 * math.pi * j / seg
                nx, ny, nz = math.sin(th) * math.cos(ph), math.sin(th) * math.sin(ph), math.cos(th)
                self.V.append((cx + rx * nx, cy + ry * ny, cz + rz * nz))
                n = (nx / rx, ny / ry, nz / rz); L = math.sqrt(sum(a * a for a in n)) or 1; self.N.append(tuple(a / L for a in n))
                self.C.append(col); self.T.append((1, 0, 0, 1))
        for i in range(ring):
            for j in range(seg):
                a = base + i * (seg + 1) + j; b = a + seg + 1
                self.tris.append((a, b, b + 1)); self.tris.append((a, b + 1, a + 1))

    def tube(self, p0, p1, r0, r1, col, seg=12, rx=1.0):
        col = tuple(col) + ((1,) if len(col) == 3 else ())
        ax = np.array(p1, float) - np.array(p0, float); L = np.linalg.norm(ax) or 1e-6; ax /= L
        up = np.array((0, 0, 1.0)) if abs(ax[2]) < 0.9 else np.array((1.0, 0, 0))
        u = np.cross(ax, up); u /= np.linalg.norm(u); v = np.cross(ax, u)
        base = len(self.V)
        for k, (p, r) in enumerate(((p0, r0), (p1, r1))):
            for j in range(seg + 1):
                a = 2 * math.pi * j / seg; d = u * math.cos(a) * rx + v * math.sin(a)
                self.V.append(tuple(np.array(p, float) + d * r)); n = u * math.cos(a) / rx + v * math.sin(a); n /= np.linalg.norm(n)
                self.N.append(tuple(n)); self.C.append(col); self.T.append((1, 0, 0, 1))
        for j in range(seg):
            a = base + j; b = base + seg + 1 + j
            self.tris.append((a, a + 1, b + 1)); self.tris.append((a, b + 1, b))
        self.blob(p0, (r0 * rx, r0, r0) if abs(ax[2]) > 0.9 else (r0, r0, r0), col, seg, 6)
        self.blob(p1, (r1 * rx, r1, r1) if abs(ax[2]) > 0.9 else (r1, r1, r1), col, seg, 6)

    def lathe(self, prof, col, seg=20, yoff=0.0):
        """smooth closed body of elliptical rings: prof = [(z, rx, ry)] bottom -> top"""
        col = tuple(col) + ((1,) if len(col) == 3 else ()); base = len(self.V)
        for k, (z, rx, ry) in enumerate(prof):
            z0 = prof[max(0, k - 1)][0]; z1 = prof[min(len(prof) - 1, k + 1)][0]
            r0 = prof[max(0, k - 1)][1]; r1 = prof[min(len(prof) - 1, k + 1)][1]
            slope = -(r1 - r0) / max(1e-4, (z1 - z0))
            for j in range(seg + 1):
                a = 2 * math.pi * j / seg; ca, sa = math.cos(a), math.sin(a)
                u = np.array((ca / rx, sa / ry)); u /= np.linalg.norm(u)
                self.V.append((rx * ca, yoff + ry * sa, z)); n = np.array((u[0], u[1], slope)); n /= np.linalg.norm(n)
                self.N.append(tuple(n)); self.C.append(col); self.T.append((1, 0, 0, 1))
        for k in range(len(prof) - 1):
            for j in range(seg):
                a = base + k * (seg + 1) + j; b = a + seg + 1
                self.tris.append((a, a + 1, b + 1)); self.tris.append((a, b + 1, b))

    def node(self, name):
        if not self.V: return None
        return mesh_node(name, np.array(self.V, np.float32), np.array(self.N, np.float32), np.array(self.C, np.float32),
                         np.array(self.T, np.float32), self.tris)


def _put(parent, name, mesh, app, gloss=0.18, sheen=0.5):
    gn = mesh.node(name)
    if gn is None: return parent.attach_new_node(name)
    n = parent.attach_new_node(gn); shade(n, app, gloss, sheen); return n


class Avatar(Person):
    """a SHINE ONLINE friend: original procedural character with the crew's animation rig"""
    def __init__(self, game, cfg, x=0.0, y=0.0, h=0.0):
        self.cfg = clean(cfg)
        Person.__init__(self, game, "avatar", x, y, h, ped=True)
        self.name = self.cfg["name"]

    def set_outfit(self, outfit): pass
    def set_expression(self, expr="neutral"): self.expression = expr; self.face_np = None
    def set_chew(self, k): pass

    def build_model(self):
        app = self.app; c = self.cfg; s = c.get("build", 1.0)
        skin = tuple(c.get("skin_rgb") or SKINS[c["skin"]][1]); hairc = tuple(c.get("hair_rgb") or HAIR_COLS[c["hair_col"]][1])
        fem = c.get("body") == "F"; w = 0.9 if fem else 1.0          # women players: narrower shoulders and arms, same rig
        top = tuple(c.get("kit_top") or COLS[c["top_col"]][1]); bot = tuple(c.get("kit_bottom") or COLS[c["bottom_col"]][1])
        dark = (top[0] * 0.7, top[1] * 0.7, top[2] * 0.7)
        m = NodePath("avatar"); m.reparent_to(self.np); m.set_h(180); self.model = m
        kit = c.get("kit_top") is not None             # football kit: short-sleeve shirt, shorts, socks, boots
        if kit: c = dict(c, top="jersey")
        long_sleeve = c["top"] in ("hoodie", "jacket") and not kit
        # ---- torso (clothes) + neck/head (skin)
        t = Mesh()
        t.lathe([(0.8, 0.02, 0.02), (0.83, 0.12 * s, 0.085), (0.88, 0.16 * s, 0.105), (0.95, 0.168 * s, 0.112), (1.03, 0.158 * s, 0.106)], bot)
        if fem:
            t.lathe([(0.99, 0.162 * s, 0.11), (1.08, 0.146 * s, 0.1), (1.17, 0.152 * s, 0.108), (1.26, 0.166 * s, 0.114),
                     (1.33, 0.178 * s, 0.106), (1.375, 0.168 * s, 0.09), (1.405, 0.115 * s, 0.066), (1.425, 0.054, 0.045), (1.43, 0.01, 0.01)], top, 24)
        else:
            t.lathe([(0.99, 0.162 * s, 0.11), (1.08, 0.156 * s, 0.106), (1.17, 0.172 * s, 0.116), (1.26, 0.186 * s, 0.12),
                     (1.33, 0.2 * s, 0.112), (1.375, 0.19 * s, 0.095), (1.405, 0.13 * s, 0.07), (1.425, 0.06, 0.05), (1.43, 0.01, 0.01)], top, 24)
        for sx in (-1, 1): t.blob((sx * 0.19 * s * w, 0.0, 1.345), (0.065 * w, 0.07 * w, 0.06), top)   # shoulder caps
        if c["top"] == "hoodie":
            t.blob((0, 0.085, 1.43), (0.12, 0.06, 0.07), dark)                                         # hood at the back
            t.blob((0, -0.115, 1.12), (0.11, 0.025, 0.06), dark)                                       # front pocket
            for sx in (-1, 1): t.tube((sx * 0.04, -0.11, 1.38), (sx * 0.045, -0.125, 1.24), 0.006, 0.006, (0.95, 0.95, 0.95))   # drawstrings
        elif c["top"] == "jacket":
            t.tube((0, -0.125, 1.0), (0, -0.12, 1.38), 0.012, 0.012, (0.75, 0.75, 0.78))               # zip
            t.blob((0, -0.03, 1.41), (0.1, 0.09, 0.035), dark)                                         # collar
        elif c["top"] == "jersey":
            t.blob((0, -0.02, 1.405), (0.085, 0.08, 0.02), (1, 1, 1))                                  # collar trim
            for sx in (-1, 1): t.tube((sx * 0.19, -0.02, 1.36), (sx * 0.15, -0.11, 1.0), 0.012, 0.01, (1, 1, 1))   # side stripes
        elif c["top"] == "vest":
            for sx in (-1, 1): t.tube((sx * 0.1, -0.1, 1.38), (sx * 0.06, -0.12, 1.2), 0.03, 0.02, dark)
        tor = _put(m, "tank", t, app, 0.12, 0.6)
        h = Mesh()
        h.tube((0, 0.0, 1.38), (0, -0.005, 1.5), 0.05 * w * 0.95 if fem else 0.05, 0.048 * w if fem else 0.048, skin)   # neck
        if fem:
            h.blob((0, -0.008, 1.62), (0.088, 0.101, 0.114), skin, 18, 12)                             # head
            h.blob((0, -0.03, 1.556), (0.063, 0.072, 0.05), skin)                                      # softer jaw / chin
        else:
            h.blob((0, -0.008, 1.62), (0.092, 0.105, 0.118), skin, 18, 12)                             # head
            h.blob((0, -0.03, 1.55), (0.072, 0.08, 0.055), skin)                                       # jaw / chin
        for sx in (-1, 1): h.blob((sx * 0.092, 0.0, 1.615), (0.014, 0.022, 0.03), skin)                # ears
        h.blob((0, -0.106, 1.6), (0.013, 0.016, 0.024), skin)                                           # nose
        sk = _put(m, "skin", h, app, 0.2, 0.75)
        f = Mesh()
        for sx in (-1, 1):
            f.blob((sx * 0.036, -0.093, 1.638), (0.019, 0.012, 0.012), (0.96, 0.96, 0.95))           # eye whites
            f.blob((sx * 0.036, -0.103, 1.638), (0.0095, 0.006, 0.0095), (0.18, 0.12, 0.08))          # iris
            f.blob((sx * 0.036, -0.108, 1.638), (0.0045, 0.003, 0.0045), (0.02, 0.02, 0.02))          # pupil
            f.tube((sx * 0.018, -0.1, 1.665), (sx * 0.056, -0.094, 1.668), 0.0045, 0.004, (hairc[0] * 0.8, hairc[1] * 0.8, hairc[2] * 0.8), 6)   # brows
        f.blob((0, -0.1, 1.556), (0.022, 0.006, 0.0055) if not fem else (0.021, 0.0065, 0.0068), (0.62, 0.3, 0.29) if not fem else (0.66, 0.32, 0.33), 10, 6)   # lips
        _put(m, "eyes", f, app, 0.6, 0.0)
        # ---- hair
        hr = Mesh(); st = c["hair"]
        cap = lambda: hr.blob((0, 0.012, 1.655), (0.1, 0.112, 0.1), hairc)
        if st == "buzz": hr.blob((0, 0.006, 1.645), (0.095, 0.108, 0.1), hairc)
        elif st == "afro":
            hr.blob((0, 0.02, 1.69), (0.17, 0.17, 0.15), hairc, 18, 12)
        elif st == "ponytail":
            cap(); hr.blob((0, 0.11, 1.64), (0.035, 0.03, 0.03), hairc)
            hr.tube((0, 0.12, 1.64), (0, 0.16, 1.42), 0.035, 0.02, hairc)
        elif st == "mohawk":
            hr.blob((0, 0.006, 1.64), (0.094, 0.107, 0.095), (hairc[0] * 0.4, hairc[1] * 0.4, hairc[2] * 0.4))
            for k in range(7): hr.blob((0, -0.07 + k * 0.03, 1.73 - abs(k - 2) * 0.008), (0.018, 0.022, 0.05), hairc)
        elif st == "buns":
            cap()
            for sx in (-1, 1): hr.blob((sx * 0.075, 0.02, 1.74), (0.045, 0.045, 0.045), hairc)
        elif st == "curly":
            rng = random.Random(7)
            for k in range(26):
                a = rng.uniform(0, 2 * math.pi); e = rng.uniform(0.1, 1.3)
                hr.blob((math.cos(a) * 0.09 * math.cos(e), 0.01 + math.sin(a) * 0.1 * math.cos(e), 1.63 + 0.09 * math.sin(e)), (0.035, 0.035, 0.035), hairc, 8, 6)
        elif st == "long":
            cap(); hr.blob((0, 0.06, 1.5), (0.1, 0.06, 0.17), hairc)
            for sx in (-1, 1): hr.blob((sx * 0.085, -0.02, 1.53), (0.025, 0.05, 0.12), hairc)
        elif st == "bob":
            cap(); hr.blob((0, 0.04, 1.6), (0.108, 0.085, 0.085), hairc)
            for sx in (-1, 1): hr.blob((sx * 0.088, -0.03, 1.585), (0.03, 0.06, 0.07), hairc)
        elif st == "braids":
            cap()
            for sx in (-1, 1):
                for k in range(7):
                    tt = k / 6.0
                    hr.blob((sx * (0.085 + 0.03 * tt), 0.01 - 0.06 * tt, 1.6 - 0.2 * tt), (0.022, 0.022, 0.026), hairc, 8, 6)
        elif st == "bun":
            cap(); hr.blob((0, 0.075, 1.735), (0.05, 0.048, 0.045), hairc)
        elif st == "pixie":
            hr.blob((0, 0.008, 1.65), (0.098, 0.11, 0.1), hairc); hr.blob((0.02, -0.08, 1.7), (0.06, 0.04, 0.03), hairc)
        elif st == "spiky":
            hr.blob((0, 0.01, 1.65), (0.098, 0.11, 0.095), hairc)
            for k in range(9):
                a = -0.9 + k * 0.23
                hr.tube((math.sin(a) * 0.05, -0.02 + abs(a) * 0.03, 1.7), (math.sin(a) * 0.1, -0.05 + abs(a) * 0.06, 1.78), 0.025, 0.004, hairc, 6)
        acc = c["acc"]
        if acc == "cap":
            hr.blob((0, 0.005, 1.68), (0.103, 0.115, 0.07), top); hr.blob((0, -0.13, 1.67), (0.08, 0.06, 0.008), top)
        elif acc == "beanie":
            hr.blob((0, 0.01, 1.675), (0.104, 0.116, 0.095), dark); hr.blob((0, 0.01, 1.775), (0.03, 0.03, 0.03), (0.95, 0.95, 0.95))
        elif acc == "headphones":
            hr.tube((-0.1, 0.0, 1.62), (0, 0.0, 1.75), 0.012, 0.012, (0.1, 0.1, 0.11), 8); hr.tube((0, 0.0, 1.75), (0.1, 0.0, 1.62), 0.012, 0.012, (0.1, 0.1, 0.11), 8)
            for sx in (-1, 1): hr.blob((sx * 0.1, 0.0, 1.61), (0.025, 0.04, 0.045), (0.85, 0.2, 0.25))
        elif acc == "glasses":
            for sx in (-1, 1): hr.tube((sx * 0.036, -0.112, 1.625), (sx * 0.036, -0.112, 1.65), 0.022, 0.022, (0.06, 0.06, 0.07), 10, rx=1.3)
            hr.tube((-0.014, -0.115, 1.642), (0.014, -0.115, 1.642), 0.004, 0.004, (0.06, 0.06, 0.07), 6)
        hn = _put(m, "hair", hr, app, 0.3, 0.3)
        # ---- arms (rig: armX -> foreX -> handX with fingersX / fistX)
        for sd, sx in (("L", 1), ("R", -1)):
            arm = m.attach_new_node("arm" + sd); arm.set_pos(sx * 0.2 * s * w, 0.0, 1.355)
            a = Mesh()
            a.tube((0, 0, 0), (0, 0, -0.27), 0.055 * w, 0.046 * w, top if long_sleeve or c["top"] != "vest" else skin)
            if not long_sleeve and c["top"] != "vest":
                a.tube((0, 0, -0.14), (0, 0, -0.27), 0.046 * w, 0.044 * w, skin)
            _put(arm, "skin" if not long_sleeve else "sleeve" + sd, a, app, 0.15, 0.6)
            fo = arm.attach_new_node("fore" + sd); fo.set_pos(0, 0, -0.27)
            b = Mesh(); b.tube((0, 0, 0), (0, 0, -0.25), 0.043 * w, 0.034 * w, top if long_sleeve else skin)
            if long_sleeve: b.tube((0, 0, -0.21), (0, 0, -0.25), 0.036, 0.034, dark)
            _put(fo, "forearm", b, app, 0.15, 0.6)
            hd = fo.attach_new_node("hand" + sd); hd.set_pos(0, 0, -0.26)
            op = Mesh(); op.blob((0, -0.005, -0.04), (0.022, 0.042, 0.05), skin)
            for k in range(4): op.tube((0, -0.03 + k * 0.018, -0.08), (0, -0.03 + k * 0.018, -0.135), 0.0085, 0.0075, skin, 6)
            op.tube((0, -0.04, -0.03), (0, -0.065, -0.07), 0.009, 0.008, skin, 6)
            _put(hd, "fingers" + sd, op, app, 0.2, 0.75)
            fi = Mesh(); fi.blob((0, -0.005, -0.06), (0.03, 0.05, 0.055), skin)
            _put(hd, "fist" + sd, fi, app, 0.2, 0.75)
        # ---- legs
        for sd, sx in (("L", 1), ("R", -1)):
            lg = m.attach_new_node("leg" + sd); lg.set_pos(sx * 0.09 * s, 0, 0.93)
            l = Mesh()
            if kit:
                sock = tuple(c.get("kit_socks") or bot)
                l.tube((0, 0, 0), (0, 0, -0.27), 0.08 * s, 0.07, bot)                  # shorts
                lw = 0.94 if fem else 1.0
                l.tube((0, 0, -0.2), (0, 0, -0.45), 0.066 * lw, 0.056 * lw, skin)      # knee
                l.tube((0, 0, -0.45), (0, 0.0, -0.86), 0.058 * lw, 0.046 * lw, sock)   # socks
                l.tube((0, 0, -0.47), (0, 0, -0.5), 0.06, 0.06, (1, 1, 1))             # sock band
                shoe = (0.08, 0.08, 0.1)
            else:
                l.tube((0, 0, 0), (0, 0, -0.45), 0.075 * s, 0.058, bot)
                l.tube((0, 0, -0.45), (0, 0.0, -0.86), 0.057, 0.045, bot)
                shoe = (0.95, 0.95, 0.95) if c["bottom_col"] != 0 else (0.12, 0.12, 0.13)
            l.blob((0, -0.045, -0.885), (0.055, 0.12, 0.045), shoe); l.blob((0, -0.045, -0.92), (0.058, 0.125, 0.015), (0.2, 0.2, 0.22))
            _put(lg, "trousers", l, app, 0.1, 0.6)
        if "number" in c:            # football shirt number on the back
            tn = TextNode("num"); tn.set_text(str(c["number"])); tn.set_align(TextNode.A_center); tn.set_text_color(1, 1, 1, 1)
            try:
                import xs_ui as U
                if U.FONT: tn.set_font(U.FONT)
            except Exception: pass
            nn = tor.attach_new_node(tn); nn.set_pos(0, 0.128, 1.17); nn.set_scale(0.14); nn.set_h(180)
            nn.set_light_off(); nn.set_shader_off(); nn.set_depth_offset(1)
            if kit:
                txc = (0.08, 0.1, 0.25, 1) if sum(top) > 1.8 else (1, 1, 1, 1); tn.set_text_color(*txc)
        self.armR = m.find("**/armR"); self.armL = m.find("**/armL"); self.foreR = m.find("**/foreR"); self.foreL = m.find("**/foreL")
        self.handR = m.find("**/handR"); self.handL = m.find("**/handL"); self.scrub_t = None; self.arm_pose = None
        self.hand_np = {sd: (m.find("**/fingers" + sd), m.find("**/fist" + sd)) for sd in ("R", "L")}
        self.set_grip(False, False)
        self.legL = m.find("**/legL"); self.legR = m.find("**/legR")
        self.upper = [ch for ch in m.get_children() if ch.get_name() not in ("legL", "legR")]
        self.set_arms((0, 3), (0, 3), (-10, 0), (-10, 0))
