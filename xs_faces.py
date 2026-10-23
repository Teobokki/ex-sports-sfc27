"""EX SPORTS(TM) SFC 27 (v1.0.0.4): head-and-shoulders portraits for the fictional SFC 27 ARENA players.

Every card gets its own face, seeded from the player (card id + name + club), so the same player always looks the same:
skin tone, face shape (width, jaw, chin, cheekbones, nose, lips, eyes, ears), age (18-36: hairline, grey, lines), hair
style + colour, eyebrows, facial hair, eye colour, and the shirt in the player's club colours.
The head is one smooth procedural surface (nose, lips, brow ridge and cheekbones are shaped into it, not stuck on),
with real eyes under upper/lower lids, hair and beard shells that follow the scalp, and ears. It is rendered offscreen
in the game's own engine (plain lights, no glow) 16 at a time and cached as PNGs in %APPDATA%\\EX SPORTS SFC 27\\faces.
All players are fictional; no real person is depicted."""
import os, math, zlib, random
import numpy as np
from panda3d.core import (NodePath, GeomVertexFormat, GeomVertexData, GeomTriangles, Geom, GeomNode, Texture, PNMImage, Filename,
                          Camera, PerspectiveLens, DirectionalLight, AmbientLight, Material, FrameBufferProperties, WindowProperties,
                          GraphicsPipe, GraphicsOutput, Vec4, SamplerState, AntialiasAttrib, LColor)

FACE_VERSION = 5                       # bump to re-render cached portraits after a look change
SIZE = 256                             # stored portrait size (px); rendered at 2x and filtered down
# ------------------------------------------------------------------ deterministic look
SKIN = [(0.98, 0.84, 0.74), (0.95, 0.78, 0.66), (0.92, 0.74, 0.6), (0.88, 0.68, 0.52), (0.82, 0.62, 0.46), (0.76, 0.55, 0.39),
        (0.68, 0.47, 0.32), (0.6, 0.4, 0.27), (0.5, 0.33, 0.22), (0.42, 0.27, 0.18), (0.34, 0.22, 0.15), (0.27, 0.18, 0.12)]
HAIR_NAT = [(0.04, 0.035, 0.035), (0.09, 0.06, 0.045), (0.17, 0.11, 0.07), (0.28, 0.18, 0.1), (0.42, 0.28, 0.15),
            (0.62, 0.46, 0.26), (0.78, 0.63, 0.4), (0.48, 0.2, 0.08)]
EYES = [(0.22, 0.13, 0.07), (0.3, 0.18, 0.09), (0.14, 0.08, 0.05), (0.38, 0.28, 0.14), (0.28, 0.42, 0.55), (0.32, 0.44, 0.3)]
STYLES = ["crop", "buzz", "textured", "sidepart", "curlytop", "afro", "bun", "locs", "shaved", "slick", "fringe", "fade"]
# v1.0.0.5: women players (mixed ARENA squads)
FSTYLES = ["ponytail", "bun", "braids", "bob", "pixie", "curls", "long", "ponytail", "bob", "curls"]
FSTYLES_TEXTURED = ["afro", "braids", "curls", "locs", "bun", "pixie", "ponytail"]


def gender_of(card_or_id):
    """'F' or 'M', fixed per player id (about half and half)"""
    cid = card_or_id.get("id") if isinstance(card_or_id, dict) else card_or_id
    return "F" if zlib.crc32(("g|%s" % cid).encode("utf-8")) & 1 else "M"
BEARDS = ["none", "none", "none", "stubble", "stubble", "short", "full", "goatee", "moustache"]


def seed_of(card):
    return zlib.crc32(("%s|%s|%s" % (card.get("id"), card.get("name"), card.get("club"))).encode("utf-8")) & 0x7FFFFFFF


def look_for(card):
    """the player's look (a plain dict, deterministic from the card)"""
    r = random.Random(seed_of(card))
    if (card.get("g") or gender_of(card)) == "F": return _look_f(card, r)
    sk = r.random() ** 0.9 * (len(SKIN) - 1); i0 = int(sk); f = sk - i0
    skin = tuple(SKIN[i0][k] * (1 - f) + SKIN[min(i0 + 1, len(SKIN) - 1)][k] * f for k in range(3))
    warm = r.uniform(-0.03, 0.03); skin = (min(1, skin[0] + warm), skin[1], max(0, skin[2] - warm))
    dark = sum(skin) < 1.6
    age = r.randint(18, 36)
    if dark: hair = HAIR_NAT[r.choice([0, 0, 0, 1, 1, 2])]
    else: hair = HAIR_NAT[r.choice([0, 1, 1, 2, 2, 3, 3, 4, 5, 6, 7])]
    if r.random() < 0.05: hair = r.choice([(0.85, 0.8, 0.62), (0.6, 0.6, 0.62)])              # bleached / ash
    style = r.choice(STYLES)
    if dark and r.random() < 0.45: style = r.choice(["afro", "locs", "curlytop", "fade", "shaved", "buzz"])
    if not dark and style in ("afro", "locs") and r.random() < 0.7: style = r.choice(["crop", "textured", "sidepart", "fringe"])
    beard = r.choice(BEARDS)
    if age < 21 and beard in ("full", "short"): beard = "stubble"
    eye = EYES[r.choice([0, 0, 1, 1, 2, 3])] if dark or sum(skin) < 2.2 else EYES[r.randrange(len(EYES))]
    return dict(seed=seed_of(card), skin=skin, hair=hair, style=style, beard=beard, eye=eye, age=age,
                wf=r.uniform(0.93, 1.07), jaw=r.uniform(0.8, 0.97), chin=r.uniform(-0.006, 0.01), cheek=r.uniform(0.0, 1.0),
                nose=r.uniform(0.85, 1.25), nosew=r.uniform(0.85, 1.3), lips=r.uniform(0.8, 1.35), eyesp=r.uniform(-0.003, 0.003),
                brow=r.uniform(0.7, 1.3), ears=r.uniform(0.9, 1.12), hh=r.uniform(0.97, 1.04), smile=r.uniform(0.0, 0.6),
                grey=max(0.0, (age - 30) / 6.0) * r.uniform(0.0, 0.7), recede=max(0.0, (age - 26) / 10.0) * r.uniform(0.0, 1.0),
                tilt=r.uniform(-4, 4), turn=r.uniform(-12, 12), collar=r.choice(["crew", "vneck", "polo"]), g="M", ridge=1.0)


def _look_f(card, r):
    """a woman player's look: natural, sporty, no make-up beyond natural lip colour, no facial hair"""
    sk = r.random() ** 0.9 * (len(SKIN) - 1); i0 = int(sk); f = sk - i0
    skin = tuple(SKIN[i0][k] * (1 - f) + SKIN[min(i0 + 1, len(SKIN) - 1)][k] * f for k in range(3))
    warm = r.uniform(-0.03, 0.03); skin = (min(1, skin[0] + warm), skin[1], max(0, skin[2] - warm))
    dark = sum(skin) < 1.6
    age = r.randint(18, 36)
    if dark: hair = HAIR_NAT[r.choice([0, 0, 0, 1, 1, 2])]
    else: hair = HAIR_NAT[r.choice([0, 1, 1, 2, 2, 3, 3, 4, 5, 6, 6, 7])]
    if r.random() < 0.04: hair = (0.85, 0.8, 0.62)
    style = r.choice(FSTYLES_TEXTURED if dark and r.random() < 0.6 else FSTYLES)
    eye = EYES[r.choice([0, 0, 1, 1, 2, 3])] if dark or sum(skin) < 2.2 else EYES[r.randrange(len(EYES))]
    return dict(seed=seed_of(card), skin=skin, hair=hair, style=style, beard="none", eye=eye, age=age,
                wf=r.uniform(0.92, 1.0), jaw=r.uniform(0.8, 0.87), chin=r.uniform(-0.005, 0.004), cheek=r.uniform(0.3, 1.0),
                nose=r.uniform(0.78, 1.02), nosew=r.uniform(0.8, 1.02), lips=r.uniform(1.05, 1.35), eyesp=r.uniform(-0.002, 0.002),
                brow=r.uniform(0.6, 0.85), ears=r.uniform(0.88, 1.0), hh=r.uniform(0.97, 1.02), smile=r.uniform(0.1, 0.7),
                grey=0.0, recede=0.0, tilt=r.uniform(-4, 4), turn=r.uniform(-12, 12), collar=r.choice(["crew", "vneck", "polo"]),
                g="F", ridge=0.45, part=r.choice((-1, 0, 1)), fringe=r.random() < 0.45)


# ------------------------------------------------------------------ geometry helpers
_FMT = None
def _node(name, V, N, C, tris):
    global _FMT
    if _FMT is None:
        from panda3d.core import GeomVertexArrayFormat, InternalName
        af = GeomVertexArrayFormat()
        af.add_column(InternalName.get_vertex(), 3, Geom.NT_float32, Geom.C_point)
        af.add_column(InternalName.get_normal(), 3, Geom.NT_float32, Geom.C_normal)
        af.add_column(InternalName.get_color(), 4, Geom.NT_float32, Geom.C_color)
        _FMT = GeomVertexFormat.register_format(GeomVertexFormat(af))
    vd = GeomVertexData(name, _FMT, Geom.UH_static); vd.unclean_set_num_rows(len(V))
    arr = np.concatenate([V, N, C], 1).astype(np.float32)
    memoryview(vd.modify_array(0)).cast("B")[:] = arr.tobytes()
    tr = GeomTriangles(Geom.UH_static); tr.set_index_type(Geom.NT_uint32)
    ta = tr.modify_vertices(); ta.unclean_set_num_rows(tris.size)
    memoryview(ta).cast("B")[:] = np.ascontiguousarray(tris, np.uint32).ravel().tobytes()
    g = Geom(vd); g.add_primitive(tr); gn = GeomNode(name); gn.add_geom(g); return gn


def _grid_tris(nr, nc, wrap=True):
    i = np.arange(nr - 1)[:, None] * nc; j = np.arange(nc - (0 if wrap else 1))[None, :]
    a = (i + j).ravel(); b = (i + (j + 1) % nc).ravel(); c = a + nc; d = b + nc
    return np.stack([np.stack([a, c, d], 1), np.stack([a, d, b], 1)], 1).reshape(-1, 3)


def _grid_normals(P):
    """normals of an (rows, cols, 3) wrapped grid from central differences"""
    du = np.roll(P, -1, 1) - np.roll(P, 1, 1)
    dv = np.concatenate([P[1:2] - P[0:1], P[2:] - P[:-2], P[-1:] - P[-2:-1]], 0)
    n = np.cross(dv, du); L = np.linalg.norm(n, axis=2, keepdims=True); L[L < 1e-9] = 1
    return n / L


def _g(P, c, s, sx=None, sy=None, sz=None):
    """anisotropic gaussian weight around point c"""
    sx = sx or s; sy = sy or s; sz = sz or s
    d = (P[..., 0] - c[0]) ** 2 / sx ** 2 + (P[..., 1] - c[1]) ** 2 / sy ** 2 + (P[..., 2] - c[2]) ** 2 / sz ** 2
    return np.exp(-d)


def _smooth(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t)


class _Mesh:
    def __init__(self): self.parts = []
    def add(self, V, N, C, tris): self.parts.append((V.reshape(-1, 3), N.reshape(-1, 3), C.reshape(-1, 4), tris))
    def ellipsoid(self, c, r, col, nr=14, nc=20, th0=0.0, th1=math.pi, rot=None):
        th = np.linspace(th0, th1, nr)[:, None]; ph = np.linspace(0, 2 * math.pi, nc, endpoint=False)[None, :]
        d = np.stack([np.sin(th) * np.cos(ph), np.sin(th) * np.sin(ph), np.cos(th) * np.ones_like(ph)], 2)
        V = d * np.array(r); N = d / np.array(r); N /= np.linalg.norm(N, axis=2, keepdims=True)
        if rot is not None: V = V @ rot.T; N = N @ rot.T
        V = V + np.array(c); C = np.broadcast_to(np.array(tuple(col) + (1,) * (4 - len(col)), np.float32), V.shape[:2] + (4,))
        self.add(V, N, C, _grid_tris(nr, nc))
    def tube(self, pts, rads, col, nc=10):
        pts = np.asarray(pts, float); n = len(pts); out = []; nor = []
        for k in range(n):
            t = pts[min(k + 1, n - 1)] - pts[max(k - 1, 0)]; t /= (np.linalg.norm(t) or 1)
            up = np.array((0, 0, 1.0)) if abs(t[2]) < 0.9 else np.array((1.0, 0, 0))
            u = np.cross(t, up); u /= np.linalg.norm(u); v = np.cross(t, u)
            a = np.linspace(0, 2 * math.pi, nc, endpoint=False)
            d = np.cos(a)[:, None] * u + np.sin(a)[:, None] * v
            out.append(pts[k] + d * rads[k]); nor.append(d)
        V = np.array(out); N = np.array(nor)
        C = np.broadcast_to(np.array(tuple(col) + (1,) * (4 - len(col)), np.float32), V.shape[:2] + (4,))
        self.add(V, N, C, _grid_tris(n, nc))
        self.ellipsoid(pts[0], (rads[0],) * 3, col, 6, nc); self.ellipsoid(pts[-1], (rads[-1],) * 3, col, 6, nc)
    def node(self, name):
        Vs, Ns, Cs, Ts, off = [], [], [], [], 0
        for V, N, C, T in self.parts: Vs.append(V); Ns.append(N); Cs.append(C); Ts.append(T + off); off += len(V)
        return _node(name, np.concatenate(Vs), np.concatenate(Ns), np.concatenate(Cs), np.concatenate(Ts))


# ------------------------------------------------------------------ the head
NR, NC = 90, 120


def _head_surface(L):
    """(rows, cols, 3) points of the skin surface, plus the unit sphere dirs. Face looks toward -y. Head centre at z=0."""
    th = np.linspace(0.0, math.pi, NR)[:, None]; ph = np.linspace(0, 2 * math.pi, NC, endpoint=False)[None, :] - math.pi / 2
    d = np.stack([np.sin(th) * np.cos(ph), np.sin(th) * np.sin(ph), np.cos(th) * np.ones_like(ph)], 2)
    wf, hh = L["wf"], L["hh"]
    rx, ry, rz = 0.074 * wf, 0.098, 0.112 * hh
    P = d * np.array((rx, ry, rz))
    x, y, z = P[..., 0], P[..., 1], P[..., 2]
    front = _smooth(0.0, -0.06, y)                                     # 1 on the face side
    low = _smooth(0.0, -0.09, z)                                       # 1 towards the jaw
    # cranium a little fuller at the back/top, face slightly flatter
    y = np.where(y > 0, y * 1.04, y * (1 - 0.05 * front * (1 - low)))
    # jaw: the lower half follows a squarer (superellipse) profile so the jaw stays wide instead of tapering to a point
    dz = np.clip(-d[..., 2], 0, 1); hf = np.sqrt(np.maximum(1e-6, 1 - dz ** 2))
    pw = 2.25 + (L["jaw"] - 0.8) / 0.17 * 0.95
    hf2 = np.maximum(0.0, 1 - dz ** pw) ** (1 / pw)
    k = np.where(d[..., 2] < 0, hf2 / hf, 1.0) * np.where(d[..., 2] < 0, 1.0, 1.0)
    k = np.minimum(k, 2.2)
    x = x * (1 + (k - 1) * (0.9 + 0.1 * front)); y = np.where(y < 0, y * (1 + (k - 1) * 0.55), y * (1 + (k - 1) * 0.2))
    z = z - (0.006 + L["chin"]) * low * front * _smooth(0.03, 0.0, np.abs(x))
    y = y - 0.006 * low * front * _smooth(0.03, 0.0, np.abs(x))
    # temples slightly in, cheekbones out
    x = x * (1 - 0.06 * _g(np.stack([np.abs(x), y, z], -1), (0.07, -0.03, 0.04), 0.03))
    P = np.stack([x, y, z], -1)
    N = _grid_normals(P)
    disp = np.zeros(P.shape[:2])
    ax = np.stack([np.abs(P[..., 0]), P[..., 1], P[..., 2]], -1)       # mirrored for symmetric features
    es = 0.034 + L["eyesp"]
    disp += 0.006 * L["cheek"] * _g(ax, (0.048, -0.075, -0.015), 0.018)                     # cheekbones
    disp -= 0.007 * _g(ax, (es, -0.09, 0.012), 0.014, sz=0.011)                              # eye sockets
    disp += 0.006 * L.get("ridge", 1.0) * _g(ax, (0.03, -0.09, 0.034), 0.02, sz=0.007)       # brow ridge
    disp -= 0.004 * _g(ax, (0.0, -0.09, 0.02), 0.006, sz=0.01)                               # between the brows
    n, nw = L["nose"], L["nosew"]
    for k, (zz, a, s) in enumerate(((0.012, 0.004, 0.006), (-0.005, 0.009, 0.0065), (-0.02, 0.016, 0.0075), (-0.031, 0.021 * n, 0.0095))):
        disp += a * n * _g(P, (0, -0.1, zz), s * nw, sx=s * nw, sz=0.009)                    # nose bridge -> tip
    disp += 0.008 * _g(ax, (0.012 * nw, -0.098, -0.035), 0.007)                              # nostril wings
    disp -= 0.003 * _g(P, (0, -0.1, -0.043), 0.006, sz=0.004)                                # under the nose
    sm = L["smile"]; lp = L["lips"]
    disp += 0.006 * lp * _g(P, (0, -0.1, -0.054), 0.017, sz=0.0045)                         # upper lip
    disp += 0.007 * lp * _g(P, (0, -0.1, -0.067), 0.015, sz=0.006)                          # lower lip
    disp -= 0.0035 * _g(P, (0, -0.1, -0.0605), 0.02, sz=0.0018)                              # mouth line
    disp -= 0.003 * _g(ax, (0.022, -0.09, -0.058 + 0.004 * sm), 0.004)                       # mouth corners
    disp += 0.006 * _g(P, (0, -0.1, -0.092), 0.016, sz=0.01)                                 # chin
    disp -= 0.0035 * _g(P, (0, -0.1, -0.079), 0.012, sz=0.004)                               # under the lower lip
    P = P + N * disp[..., None]
    return P, _grid_normals(P), ax, es


def _hair_mask(P, L):
    x, y, z = P[..., 0], P[..., 1], P[..., 2]; ax = np.abs(x)
    rec = L["recede"]
    hl = 0.058 + 0.018 * rec + 0.012 * rec * _smooth(0.0, 0.05, ax)                         # front hairline height (temples recede)
    hl = hl + 0.02 * _smooth(0.02, 0.06, ax)                                                 # temples sit higher
    front = _smooth(0.0, -0.07, y)
    side_line = np.where(y < 0.02, 0.022, -0.06 + 0.04 * _smooth(0.09, 0.0, y))               # over the ears, down to the nape
    line = front * hl + (1 - front) * side_line
    m = _smooth(line - 0.004, line + 0.006, z)
    if L.get("g") == "F":                                                                     # rounder hairline, no sideburns
        return np.maximum(m, 0.7 * _smooth(0.066, 0.071, ax) * _smooth(-0.012, 0.008, z) * _smooth(0.0, -0.03, y) * _smooth(-0.075, -0.05, y))
    burn = _smooth(0.068, 0.072, ax) * _smooth(-0.02, 0.0, z) * _smooth(0.0, -0.03, y) * _smooth(-0.07, -0.05, y)   # sideburns
    return np.maximum(m, burn * 0.8)


def _drape(L, z_bot, phi_f=1.1, flare=0.0, curl=0.0, jitter=0.0, col=(0.1, 0.08, 0.06), rng=None, out=0.011, nzr=26, nphi=64):
    """a sheet of hair hanging from the crown down to z_bot around the sides and back (the face side stays open)"""
    rx, ry, rz = 0.074 * L["wf"] + out, 0.098 + out + 0.004, 0.112 * L["hh"] + out
    zs = np.linspace(0.085, z_bot, nzr); phis = np.linspace(phi_f, 2 * math.pi - phi_f, nphi)
    rng = rng or np.random.default_rng(0)
    ln = 1 + rng.normal(0, 0.04, nphi)                                   # uneven ends
    V = np.zeros((nzr, nphi, 3)); C = np.ones((nzr, nphi, 4), np.float32)
    for i, z in enumerate(zs):
        if z > 0: k = math.sqrt(max(0.05, 1 - (z / rz) ** 2))
        else: k = 1.0 + flare * (-z) / 0.1
        t = (z - z_bot) / max(1e-6, -z_bot) if z < 0 else 1.0
        kk = k - curl * max(0.0, 1 - t / 0.25)                           # the ends curl in (bob)
        zz = z * ln if z < 0 else np.full(nphi, z)
        rr = 1 + (rng.normal(0, jitter, nphi) if jitter else 0)
        V[i, :, 0] = np.sin(phis) * rx * kk * rr; V[i, :, 1] = -np.cos(phis) * ry * kk * rr + 0.004; V[i, :, 2] = zz
    strand = 1 + 0.09 * np.sin(np.arange(nphi) * 2.3)[None, :] + rng.normal(0, 0.04, (nzr, nphi))
    C[..., :3] = np.clip(np.array(col)[None, None, :] * strand[..., None], 0, 1)
    N = _grid_normals(V)
    ctr = np.zeros_like(V); ctr[..., 2] = V[..., 2]
    N = np.where(((N * (V - ctr)).sum(-1) < 0)[..., None], -N, N)
    tris = []
    for i in range(nzr - 1):
        for j in range(nphi - 1):
            a = i * nphi + j; b = a + nphi
            tris += [(a, b, b + 1), (a, b + 1, a + 1)]
    return _node("drape", V.reshape(-1, 3), N.reshape(-1, 3), C.reshape(-1, 4), np.array(tris, np.int32))


def _hair_f(root, L, P, N, hm, hc, top, frontish, shell, rng):
    st = L["style"]; x, y, z = P[..., 0], P[..., 1], P[..., 2]
    part = L.get("part", 0) * 0.025
    parted = 1 - 0.35 * _g(np.stack([x - part, y, z], -1), (0, -0.04, 0.1), 0.008, sx=0.004)    # a visible parting line
    fr = _smooth(0.035, 0.055, z) * frontish * _smooth(0.065, 0.035, np.abs(x - part * 0.6))     # bangs over the forehead
    hmf = np.maximum(hm, fr) if L.get("fringe") and st in ("bob", "long", "curls", "pixie") else hm
    if st == "pixie":
        side = np.clip(0.5 + (x - part) / 0.1, 0, 1)
        shell(np.maximum(hm, fr * 0.9), 0.004 + 0.012 * top * (0.6 + 0.4 * side), hc, 0.07, "hair", jitter=0.1)
        return
    if st == "afro":
        shell(np.maximum(hm, _smooth(-0.03, 0.0, z) * (1 - frontish * _smooth(0.05, 0.03, z))), 0.01 + 0.045 * top, hc, 0.1, "hair", jitter=0.12)
        return
    if st == "locs":
        shell(hm, 0.007 + 0.004 * top, hc, 0.07, "hair")
        root.attach_new_node(_drape(L, -0.2, 1.2, 0.05, 0.0, 0.05, hc * 0.95, rng, out=0.016, nphi=80))
        return
    tight = st in ("ponytail", "bun", "braids")
    shell(hmf * (parted if tight else 1), (0.0045 + 0.004 * top) if tight else (0.006 + 0.008 * top), hc, 0.06, "hair",
          jitter=0.22 if st == "curls" else 0.0)
    mm = _Mesh()
    if st == "ponytail":
        sx = 1 if L["seed"] & 1 else -1                                                         # high ponytail falling over one shoulder
        mm.ellipsoid((0, 0.088, 0.072), (0.016, 0.014, 0.014), tuple(hc * 0.55))               # hair tie
        pts = [(0, 0.095, 0.074), (0.0, 0.13, 0.06), (sx * 0.03, 0.14, 0.0), (sx * 0.075, 0.095, -0.075), (sx * 0.095, 0.045, -0.14), (sx * 0.1, 0.02, -0.19)]
        mm.tube(pts, [0.02, 0.022, 0.02, 0.017, 0.013, 0.006], tuple(hc), 12)
    elif st == "bun":
        mm.ellipsoid((0, 0.062, 0.108), (0.036, 0.032, 0.03), tuple(hc), 12, 16)
        mm.ellipsoid((0, 0.05, 0.09), (0.02, 0.018, 0.012), tuple(hc * 0.6))                      # tie
    elif st == "braids":
        for sx in (-1, 1):                                       # two braids falling forward over the shoulders
            p0 = np.array((sx * 0.066, 0.03, -0.005)); p1 = np.array((sx * 0.084, 0.0, -0.08)); p2 = np.array((sx * 0.1, -0.035, -0.19))
            for k in range(16):
                t = k / 15.0; p = (1 - t) ** 2 * p0 + 2 * (1 - t) * t * p1 + t * t * p2
                off = (0.004 if k % 2 else -0.004)
                mm.ellipsoid(tuple(p + np.array((off, 0, 0))), (0.012 - 0.004 * t, 0.011 - 0.003 * t, 0.011), tuple(hc * (0.9 if k % 2 else 1.05)), 8, 10)
            mm.ellipsoid(tuple(p2 + np.array((0, 0, -0.012))), (0.008, 0.008, 0.008), tuple(hc * 0.6))
    elif st == "bob":
        root.attach_new_node(_drape(L, -0.072, 1.0, 0.03, 0.012, 0.0, hc, rng))
    elif st == "long":
        root.attach_new_node(_drape(L, -0.21, 1.12, 0.02, 0.0, 0.0, hc, rng))
    elif st == "curls":
        root.attach_new_node(_drape(L, -0.13, 1.05, 0.18, 0.0, 0.05, hc, rng, out=0.016, nphi=80))
    if mm.parts: root.attach_new_node(mm.node("hair2"))


def build_portrait(L, kit):
    """NodePath of the head + shoulders for look L, kit = (shirt, trim)"""
    rng = np.random.default_rng(L["seed"])
    root = NodePath("portrait")
    skin = np.array(L["skin"]); hair = np.array(L["hair"])
    P, N, ax, es = _head_surface(L)
    # ---- skin colours: subtle variation, warmer cheeks / nose / lips, stubble shading, age lines
    C = np.ones(P.shape[:2] + (4,), np.float32); C[..., :3] = skin
    blush = 0.5 * _g(ax, (0.045, -0.08, -0.03), 0.02) + 0.5 * _g(P, (0, -0.11, -0.03), 0.012)
    C[..., :3] = C[..., :3] * (1 - 0.12 * blush[..., None]) + np.array((0.75, 0.3, 0.28)) * 0.12 * blush[..., None] * skin.mean() * 1.6
    lipm = np.clip(_g(P, (0, -0.1, -0.054), 0.016, sz=0.0045) + _g(P, (0, -0.1, -0.067), 0.014, sz=0.0055), 0, 1) * (P[..., 1] < -0.07)
    lipc = skin * np.array((0.84, 0.6, 0.6)) + np.array((0.06, 0.0, 0.0)) if L.get("g") != "F" else skin * np.array((0.86, 0.58, 0.6)) + np.array((0.08, 0.0, 0.01))
    C[..., :3] = C[..., :3] * (1 - lipm[..., None]) + lipc * lipm[..., None]
    C[..., :3] *= (1 - 0.35 * _g(P, (0, -0.1, -0.0605), 0.019, sz=0.0016))[..., None]       # mouth line shadow
    beard = L["beard"]
    zline = -0.047 + 0.62 * np.clip(np.abs(P[..., 0]) - 0.012, 0, 0.07) + 0.012 * np.clip((P[..., 1] + 0.05) / 0.05, 0, 1)   # cheek line: low by the mouth, up to the sideburns
    jawzone = _smooth(zline + 0.012, zline - 0.01, P[..., 2]) * _smooth(0.02, -0.04, P[..., 1]) * (1 - _g(P, (0, -0.1, -0.06), 0.018, sz=0.012))
    stache = _g(P, (0, -0.1, -0.046), 0.02, sz=0.006) * (1 - _g(P, (0, -0.11, -0.054), 0.012, sz=0.003))
    if L.get("g") != "F" and (beard != "none" or L["age"] > 24):
        sh = jawzone * (0.25 if beard != "none" else 0.12) + stache * (0.2 if beard != "none" else 0.08)
        C[..., :3] = C[..., :3] * (1 - sh[..., None]) + (hair * 0.6 + skin * 0.2) * sh[..., None]
    if L["age"] >= 29:                                                                       # faint forehead / eye lines
        ln = sum(_g(P, (0, -0.09, z0), 0.04, sz=0.0016) for z0 in (0.05, 0.062)) * min(1.0, (L["age"] - 28) / 6.0)
        C[..., :3] *= (1 - 0.06 * ln)[..., None]
    C[..., :3] *= (1 + rng.normal(0, 0.012, P.shape[:2]))[..., None]
    C[..., :3] = np.clip(C[..., :3], 0, 1)
    # ---- eyebrows and hair as shells over the skin
    def shell(mask, thick, col, noise=0.0, name="shell", jitter=0.0):
        off = mask * thick - 0.0015 * (mask < 0.02)
        if jitter:
            jn = rng.normal(0, jitter, off.shape); jn = (jn + np.roll(jn, 1, 0) + np.roll(jn, -1, 0) + np.roll(jn, 1, 1) + np.roll(jn, -1, 1)) / 3.0
            off = off * (1 + jn)
        S = P + N * off[..., None]
        cc = np.ones(P.shape[:2] + (4,), np.float32); cc[..., :3] = col
        strand = np.sin(np.arange(NC)[None, :] * 1.9 + np.arange(NR)[:, None] * 0.35) * 0.5
        cc[..., :3] *= (1 + rng.normal(0, noise * 0.6, P.shape[:2]) + strand * noise)[..., None]
        cc[..., :3] = np.clip(cc[..., :3], 0, 1)
        keep = mask > 0.03                                    # only draw the covered part (+1 ring so the edge stays soft)
        rows = np.where(keep.any(1))[0]
        if len(rows) == 0: return
        r0, r1 = max(0, rows.min() - 1), min(NR, rows.max() + 2)
        msk = keep[r0:r1]; tris = _grid_tris(r1 - r0, NC)
        idx = np.arange((r1 - r0) * NC).reshape(r1 - r0, NC); ok = (msk | np.roll(msk, 1, 0) | np.roll(msk, -1, 0)).ravel()
        tris = tris[ok[tris].all(1)]
        mm = _Mesh(); mm.add(S[r0:r1], _grid_normals(S)[r0:r1], cc[r0:r1], tris)
        root.attach_new_node(mm.node(name))
    browc = hair * 0.85 if L["grey"] < 0.5 else hair * 0.6 + 0.2
    bz = 0.034 + 0.002 * (L["brow"] - 1)
    if L.get("g") == "F":              # finer, gently arched brows
        bz = 0.036 + 0.004 * _g(ax, (es + 0.006, -0.09, 0.036), 0.012)[..., None].squeeze(-1) * 0
        brow = np.clip(_g(ax, (es + 0.004, -0.09, 0.037), 0.019, sz=0.0038 * L["brow"] / 0.75) * 1.8 - 0.4, 0, 1) * (P[..., 1] < -0.06)
        brow *= (1 - 0.5 * _smooth(0.05, 0.062, ax[..., 0]))
    else:
        brow = np.clip(_g(ax, (es + 0.003, -0.09, bz), 0.021, sz=0.0055 * L["brow"]) * 1.7 - 0.3, 0, 1) * (P[..., 1] < -0.06)
    brow *= _smooth(0.004, 0.012, ax[..., 0])
    C[..., :3] = C[..., :3] * (1 - 0.7 * brow[..., None]) + browc * 0.7 * brow[..., None]
    shell(brow, 0.0022 if L.get("g") != "F" else 0.0016, browc, 0.06, "brows")
    skin_np = root.attach_new_node(_Mesh().node("x") if False else _node("skin", P.reshape(-1, 3), N.reshape(-1, 3), C.reshape(-1, 4), _grid_tris(NR, NC)))
    hm = _hair_mask(P, L); st = L["style"]
    hc = hair * (1 - L["grey"]) + np.array((0.62, 0.62, 0.62)) * L["grey"]
    top = _smooth(0.02, 0.1, P[..., 2]); frontish = _smooth(0.02, -0.08, P[..., 1])
    if L.get("g") == "F": pass
    elif st == "buzz": shell(hm, 0.0025, hc, 0.08, "hair")
    elif st == "shaved":
        C2 = hm[..., None] * 0.45
        skin_np.remove_node()
        Cs = C.copy(); Cs[..., :3] = C[..., :3] * (1 - C2) + hc * C2
        root.attach_new_node(_node("skin", P.reshape(-1, 3), N.reshape(-1, 3), Cs.reshape(-1, 4), _grid_tris(NR, NC)))
    elif st == "fade": shell(hm, 0.002 + 0.012 * top, hc, 0.06, "hair")
    elif st == "crop": shell(hm, 0.004 + 0.008 * top, hc, 0.06, "hair")
    elif st == "textured": shell(hm, 0.004 + 0.014 * top * (0.6 + 0.4 * frontish), hc, 0.1, "hair", jitter=0.15)
    elif st == "sidepart":
        side = np.clip(0.5 + P[..., 0] / 0.12, 0, 1)
        shell(hm, 0.004 + 0.014 * top * (0.5 + 0.5 * side), hc, 0.05, "hair")
    elif st == "slick": shell(hm, 0.006 + 0.01 * top * (1 - 0.5 * frontish), hc * 0.85, 0.03, "hair")
    elif st == "fringe":
        m2 = np.maximum(hm, _smooth(0.03, 0.05, P[..., 2]) * frontish * _smooth(0.06, 0.03, np.abs(P[..., 0])))
        shell(m2, 0.005 + 0.012 * top, hc, 0.07, "hair", jitter=0.15)
    elif st == "curlytop":
        shell(hm, 0.005 + 0.02 * top, hc, 0.12, "hair", jitter=0.3)
    elif st == "afro":
        shell(np.maximum(hm, _smooth(-0.03, 0.0, P[..., 2]) * (1 - frontish * _smooth(0.05, 0.03, P[..., 2]))), 0.008 + 0.04 * top, hc, 0.1, "hair", jitter=0.12)
    elif st == "bun":
        shell(hm, 0.006 + 0.004 * top, hc, 0.05, "hair"); mm = _Mesh(); mm.ellipsoid((0, 0.075, 0.085), (0.032, 0.03, 0.03), hc); root.attach_new_node(mm.node("bun"))
    elif st == "locs":
        shell(hm, 0.008 + 0.006 * top, hc, 0.08, "hair")
        mm = _Mesh(); rr = random.Random(L["seed"])
        for k in range(34):
            a = -2.5 + k * (5.0 / 33) + rr.uniform(-0.05, 0.05); ca, sa = math.sin(a), math.cos(a)
            if sa < -0.35: continue                                              # leave the face clear
            r0 = 0.085; sx, sy = ca * r0 * 0.95, sa * r0 * 1.1 + 0.005; z0 = 0.075 - 0.02 * max(0.0, sa)
            ln = rr.uniform(0.1, 0.17) if sa > -0.1 else rr.uniform(0.05, 0.08)
            pts = [(sx * 0.8, sy * 0.8, z0 + 0.02), (sx * 1.08, sy * 1.06, z0 - 0.01), (sx * 1.16, sy * 1.12 + 0.01, z0 - ln * 0.55), (sx * 1.2, sy * 1.15 + 0.02, z0 - ln)]
            mm.tube(pts, [0.009, 0.0095, 0.0088, 0.0078], tuple(np.clip(hc * rr.uniform(0.85, 1.15), 0, 1)), 8)
        root.attach_new_node(mm.node("locs"))
    # ---- v1.0.0.5 women's hair: scalp shell + drape (bob / long / curls), ponytail, bun, braids, pixie
    if L.get("g") == "F": _hair_f(root, L, P, N, hm, hc, top, frontish, shell, rng)
    # ---- facial hair shells
    if beard in ("short", "full", "goatee", "moustache"):
        chin = _g(P, (0, -0.08, -0.09), 0.02, sz=0.025)
        if beard == "moustache": bm = np.clip(stache * 2.2 - 0.5, 0, 1) * (P[..., 1] < -0.08)
        elif beard == "goatee": bm = np.clip(np.maximum(stache * 2.2 - 0.5, chin * 1.8 - 0.5), 0, 1) * (P[..., 1] < -0.05)
        else: bm = np.clip(np.maximum(jawzone * 1.4 - 0.2, stache * 2.2 - 0.5), 0, 1) * (1 - np.clip(lipm * 2, 0, 1))
        bc = hair * (1 - L["grey"] * 0.5) + np.array((0.55, 0.55, 0.55)) * L["grey"] * 0.5
        shell(bm, 0.0032 if beard != "full" else 0.007, bc, 0.1, "beard", jitter=0.1)
    # ---- eyes: eyeball, iris, pupil, upper + lower lids, lash line
    mm = _Mesh(); er = 0.0118
    for sx in (-1, 1):
        cx = sx * es; cz = 0.012
        sel = (np.abs(P[..., 0] - cx) < 0.006) & (np.abs(P[..., 2] - cz) < 0.006) & (P[..., 1] < 0)
        ysurf = P[..., 1][sel].min() if sel.any() else -0.085
        cy = ysurf + er * 0.42
        mm.ellipsoid((cx, cy, cz), (er, er, er), (0.93, 0.91, 0.88), 12, 16)
        rot = None
        mm.ellipsoid((cx + sx * 0.0005, cy - er * 0.93, cz), (0.0058, 0.0016, 0.0058), L["eye"], 8, 14)
        mm.ellipsoid((cx + sx * 0.0005, cy - er * 0.99, cz), (0.0027, 0.0008, 0.0027), (0.02, 0.02, 0.02), 6, 10)
        mm.ellipsoid((cx + sx * 0.002, cy - er * 1.0 - 0.0002, cz + 0.003), (0.0012, 0.0003, 0.0012), (0.95, 0.95, 0.95), 4, 6)   # catch light
        lid = tuple(skin * 0.93)
        mm.ellipsoid((cx, cy + 0.0006, cz + 0.0012), (er * 1.14, er * 1.14, er * 1.14), lid, 10, 18, 0.0, math.radians(68))        # upper lid
        mm.ellipsoid((cx, cy + 0.0006, cz - 0.0003), (er * 1.1, er * 1.1, er * 1.1), lid, 8, 18, math.radians(122), math.pi)        # lower lid
        th = np.linspace(-1.05, 1.05, 9)
        lash = [(cx + math.sin(t) * er * 1.13, cy - math.cos(t) * er * 1.13 * 0.98, cz + 0.0012 + er * 1.14 * math.cos(math.radians(68))) for t in th]
        mm.tube(lash, [0.0009 if L.get("g") != "F" else 0.00125] * len(lash), tuple(hair * 0.4 + 0.02) if L.get("g") != "F" else (0.05, 0.04, 0.04), 5)
    root.attach_new_node(mm.node("eyes"))
    # ---- ears
    mm = _Mesh(); es_ = L["ears"]
    for sx in (-1, 1):
        rot = np.array(((math.cos(0.25), sx * -math.sin(0.25), 0), (sx * math.sin(0.25), math.cos(0.25), 0), (0, 0, 1)))
        mm.ellipsoid((sx * 0.073 * L["wf"], 0.008, 0.0), (0.009, 0.019 * es_, 0.028 * es_), tuple(skin * 0.96), 10, 14, rot=rot)
        mm.ellipsoid((sx * 0.077 * L["wf"], 0.004, 0.0), (0.004, 0.012 * es_, 0.019 * es_), tuple(skin * 0.78), 8, 12, rot=rot)
    root.attach_new_node(mm.node("ears"))
    # ---- neck, shoulders and the club shirt
    shirt, trim = np.array(kit[0]), np.array(kit[1])
    mm = _Mesh()
    zs = np.linspace(-0.25, -0.05, 9)
    nk = (1.0 + 0.08 * (L["wf"] - 1) * 5) * (0.86 if L.get("g") == "F" else 1.0)
    shw = 0.88 if L.get("g") == "F" else 1.0                                               # narrower shoulders
    neck = [(0, 0.018, z) for z in np.linspace(-0.24, -0.03, 6)]
    mm.tube(neck, [0.062 * nk, 0.06 * nk, 0.058 * nk, 0.055 * nk, 0.052 * nk, 0.05 * nk], tuple(skin * 0.88), 20)
    rows = []; nrm = []
    prof = [(-0.6, 0.24, 0.135), (-0.42, 0.245, 0.135), (-0.31, 0.24, 0.128), (-0.25, 0.225, 0.118), (-0.22, 0.19, 0.105), (-0.2, 0.14, 0.092),
            (-0.187, 0.095, 0.08), (-0.18, 0.07 * nk, 0.07 * nk)]
    a = np.linspace(0, 2 * math.pi, 40, endpoint=False)
    for z, rx_, ry_ in prof:
        if rx_ > 0.1: rx_ *= shw
        rows.append(np.stack([rx_ * np.cos(a), 0.01 + ry_ * np.sin(a), np.full_like(a, z)], 1))
    V = np.array(rows); Nn = _grid_normals(V)
    ctr = np.zeros_like(V); ctr[..., 2] = V[..., 2]; ctr[..., 1] = 0.01
    Nn = np.where(((Nn * (V - ctr)).sum(-1) < 0)[..., None], -Nn, Nn)       # outward
    Cc = np.ones(V.shape[:2] + (4,), np.float32); Cc[..., :3] = shirt
    side = np.abs(np.cos(a))[None, :] > 0.97
    Cc[..., :3] = np.where(side[..., None] & (np.arange(len(prof))[:, None, None] < 4), trim, Cc[..., :3])     # side panels
    mm.add(V, Nn, Cc, _grid_tris(len(prof), 40))
    col = L["collar"]
    ring = [(0.071 * nk * math.cos(t), 0.01 + 0.071 * nk * math.sin(t), -0.18 - (0.035 * max(0.0, -math.sin(t)) ** 6 if col == "vneck" else 0)) for t in np.linspace(0, 2 * math.pi, 41)]
    mm.tube(ring, [0.0075 if col != "polo" else 0.011] * len(ring), tuple(trim), 8)
    root.attach_new_node(mm.node("shirt"))
    root.set_two_sided(True)
    root.set_h(L["turn"]); root.set_r(L["tilt"] * 0.5)
    return root


# ------------------------------------------------------------------ offscreen renderer + cache
class FaceBank:
    """renders portraits 16 at a time into an offscreen buffer and caches PNGs in DATA/faces"""
    GRID = 4

    def __init__(self, app):
        self.app = app; self.dir = os.path.join(getattr(app, "DATA", None) or ".", "faces"); self.tex = {}; self.buf = None; self.failed = False

    def key(self, card, kit):
        k = "".join("%02x" % int(max(0, min(1, v)) * 255) for v in tuple(kit[0])[:3] + tuple(kit[1])[:3])
        return "f%d_%d_%s" % (FACE_VERSION, seed_of(card), k)

    def kit_of(self, card):
        import xs_sfc as F
        for c in F.CLUBS:
            if c[0] == card.get("club"): return (c[2], c[3])
        return ((0.85, 0.85, 0.88), (0.1, 0.1, 0.12))

    def path(self, key): return os.path.join(self.dir, key + ".png")

    def texture(self, card):
        """the portrait texture of a card (rendered now if it isn't cached yet); None if offscreen rendering is unavailable"""
        kit = self.kit_of(card); key = self.key(card, kit)
        t = self.tex.get(key)
        if t is not None: return t
        if not os.path.exists(self.path(key)): self.ensure([card])
        if not os.path.exists(self.path(key)): return None
        img = PNMImage()
        if not img.read(Filename.from_os_specific(self.path(key))): return None
        t = Texture(key); t.load(img); t.set_minfilter(SamplerState.FT_linear_mipmap_linear); t.set_magfilter(SamplerState.FT_linear)
        t.set_wrap_u(SamplerState.WM_clamp); t.set_wrap_v(SamplerState.WM_clamp); self.tex[key] = t
        return t

    def ensure(self, cards):
        """render every missing portrait for these cards (batches of 16)"""
        if self.failed: return 0
        if not getattr(self, "_pruned", False):          # drop portraits cached by older FACE_VERSIONs (re-rendered only when needed)
            self._pruned = True
            try:
                for fn in os.listdir(self.dir):
                    if fn.endswith(".png") and not fn.startswith("f%d_" % FACE_VERSION): os.remove(os.path.join(self.dir, fn))
            except Exception: pass
        todo = []; seen = set()
        for c in cards:
            if c is None: continue
            kit = self.kit_of(c); key = self.key(c, kit)
            if key in seen or os.path.exists(self.path(key)): continue
            seen.add(key); todo.append((c, kit, key))
        n = self.GRID * self.GRID; done = 0
        for i in range(0, len(todo), n):
            try: done += self._render(todo[i:i + n])
            except Exception as e:
                print("faces: render failed", e, flush=True); self.failed = True; break
        return done

    def _setup(self):
        a = self.app; R = 2 * SIZE * self.GRID
        fb = FrameBufferProperties(); fb.set_rgba_bits(8, 8, 8, 8); fb.set_depth_bits(24)
        wp = WindowProperties.size(R, R)
        flags = GraphicsPipe.BF_refuse_window
        buf = a.graphicsEngine.make_output(a.pipe, "exs-faces", -50, fb, wp, flags, a.win.get_gsg(), a.win)
        if buf is None: raise RuntimeError("no offscreen buffer")
        self.out = Texture("faces-out"); buf.add_render_texture(self.out, GraphicsOutput.RTM_copy_ram)
        buf.set_clear_color_active(True); buf.set_clear_color(LColor(0, 0, 0, 0))
        buf.get_display_region(0).set_active(False)
        self.scene = NodePath("faces-scene"); self.scene.set_shader_auto(); self.scene.set_antialias(AntialiasAttrib.M_multisample)
        key = DirectionalLight("key"); key.set_color((1.05, 1.0, 0.95, 1)); kn = self.scene.attach_new_node(key); kn.set_hpr(-38, -26, 0)
        fill = DirectionalLight("fill"); fill.set_color((0.3, 0.33, 0.4, 1)); fn = self.scene.attach_new_node(fill); fn.set_hpr(40, -5, 0)
        rim = DirectionalLight("rim"); rim.set_color((0.55, 0.55, 0.6, 1)); rn = self.scene.attach_new_node(rim); rn.set_hpr(170, -30, 0)
        amb = AmbientLight("amb"); amb.set_color((0.22, 0.22, 0.24, 1)); an = self.scene.attach_new_node(amb)
        for ln in (kn, fn, rn, an): self.scene.set_light(ln)
        mt = Material("skin"); mt.set_specular((0.1, 0.1, 0.1, 1)); mt.set_shininess(16)
        self.scene.set_material(mt)
        self.slots = []; g = self.GRID
        for k in range(g * g):
            cx, cy = k % g, k // g
            dr = buf.make_display_region(cx / g, (cx + 1) / g, 1 - (cy + 1) / g, 1 - cy / g)
            dr.set_clear_color_active(True); dr.set_clear_color(LColor(0, 0, 0, 0)); dr.set_clear_depth_active(True)
            holder = self.scene.attach_new_node("slot%d" % k); holder.set_pos(k * 3.0, 0, 0)
            cam = Camera("fcam%d" % k); lens = PerspectiveLens(); lens.set_fov(20); lens.set_near_far(0.1, 10); cam.set_lens(lens)
            cn = holder.attach_new_node(cam); cn.set_pos(0, -1.25, 0.0); cn.look_at(0, 0, -0.06)
            dr.set_camera(cn); self.slots.append(holder)
        buf.set_active(False); self.buf = buf

    def _render(self, batch):
        if self.buf is None: self._setup()
        os.makedirs(self.dir, exist_ok=True)
        nodes = []
        for k, (c, kit, key) in enumerate(batch):
            n = build_portrait(look_for(c), kit); n.reparent_to(self.slots[k]); nodes.append(n)
        self.buf.set_active(True)
        self.app.graphicsEngine.render_frame(); self.app.graphicsEngine.render_frame()
        self.buf.set_active(False)
        for n in nodes: n.remove_node()
        img = PNMImage()
        if not self.out.store(img): raise RuntimeError("no portrait image")
        R = img.get_x_size() // self.GRID; done = 0
        for k, (c, kit, key) in enumerate(batch):
            cx, cy = k % self.GRID, k // self.GRID
            big = PNMImage(R, R, 4); big.copy_sub_image(img, 0, 0, cx * R, cy * R, R, R)
            small = PNMImage(SIZE, SIZE, 4); small.gaussian_filter_from(0.7, big)
            tmp = self.path(key) + ".tmp.png"
            if small.write(Filename.from_os_specific(tmp)): os.replace(tmp, self.path(key)); done += 1
        return done


def preview_sheet(app, cards, out):
    """dev helper: a contact sheet of portraits"""
    fb = FaceBank(app); fb.dir = os.path.dirname(out) or "."; fb.ensure(cards); return fb
