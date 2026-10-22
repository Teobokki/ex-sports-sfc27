"""EX SPORTS(TM) SFC 27 STANDARD EDITION - 7-a-side football at the SFC 27 stadium. KICK OFF (vs AI) or ONLINE with friends.
(c) 2026 EX SPORTS AND EX INC."""
import os, sys, json, time, math, random, threading, tempfile, urllib.request, shutil, traceback, webbrowser

APP_NAME = "EX SPORTS SFC 27"
APP_TITLE = "EX SPORTS\u2122 SFC 27"
EDITION = "STANDARD EDITION"
APP_VERSION = "1.0.0.2"
REPO = "Teobokki/ex-sports-sfc27"
UPDATE_URL = "https://raw.githubusercontent.com/%s/main/latest.json" % REPO
RELEASES_URL = "https://github.com/%s/releases/latest" % REPO
COPYRIGHT = "\u00a9 2026 EX SPORTS AND EX INC."

BASE = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
if os.environ.get("EXS_DATA_DIR"): DATA = os.environ["EXS_DATA_DIR"]
elif os.name == "nt": DATA = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), APP_NAME)
else: DATA = os.path.join(os.path.expanduser("~"), ".ex-sports-sfc27")
os.makedirs(DATA, exist_ok=True)


def log_error(msg):
    if isinstance(msg, BaseException): msg = "".join(traceback.format_exception(type(msg), msg, msg.__traceback__))
    try:
        with open(os.path.join(DATA, "error.log"), "a", encoding="utf-8") as f: f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + str(msg) + "\n")
    except Exception: pass


from panda3d.core import loadPrcFileData, Filename
_icon = os.path.join(BASE, "assets", "icon.ico")
loadPrcFileData("", """
window-title EX SPORTS SFC 27 STANDARD EDITION
win-size 1280 720
sync-video true
audio-library-name p3openal_audio
textures-power-2 none
framebuffer-multisample 1
multisamples 4
notify-level warning
default-directnotify-level warning
load-display pandagl
want-pstats false
""")
if os.environ.get("EXS_WINSIZE"): loadPrcFileData("", "win-size " + os.environ["EXS_WINSIZE"].replace("x", " "))
if os.path.exists(_icon): loadPrcFileData("", "icon-filename " + Filename.from_os_specific(_icon).get_fullpath())

from direct.showbase.ShowBase import ShowBase
from direct.gui.DirectGui import DirectFrame, DirectEntry, DGG
from direct.gui.OnscreenImage import OnscreenImage
from direct.gui import DirectGuiGlobals
from panda3d.core import (Material, TextNode, TransparencyAttrib, WindowProperties, PTA_LVecBase3f, Texture, PNMImage, Vec3, AntialiasAttrib,
                          SamplerState)
import xs_ui as U
import xs_sfc as F
import xs_avatar as A
from xs_geom import MB
from xs_online import Online


def vtuple(v):
    out = []
    for p in str(v).strip().lstrip("vV").split("."):
        n = "".join(ch for ch in p if ch.isdigit()); out.append(int(n) if n else 0)
    return tuple(out + [0] * (4 - len(out)))


def clean_env():
    """Environment for processes we start (Setup, portable swap helper/relaunch). A PyInstaller onefile parent exports
    _PYI_* / _MEIPASS2; a relaunched copy that inherits them reuses the old _MEI folder (old code keeps running and
    Windows shows 'Failed to remove temporary directory'). Strip them and ask the child bootloader to start fresh."""
    env = {k: v for k, v in os.environ.items() if not (k.upper().startswith("_PYI") or k.upper().startswith("_MEIPASS")
                                                        or k.upper() in ("TCL_LIBRARY", "TK_LIBRARY"))}
    mei = getattr(sys, "_MEIPASS", None)
    if mei and "PATH" in env:
        env["PATH"] = os.pathsep.join(x for x in env["PATH"].split(os.pathsep) if not os.path.normcase(x).startswith(os.path.normcase(mei)))
    env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
    return env


def is_portable():
    if not getattr(sys, "frozen", False) or not hasattr(sys, "_MEIPASS"): return False
    exe = os.path.normcase(os.path.abspath(sys.executable)); mp = os.path.normcase(os.path.abspath(sys._MEIPASS))
    return not mp.startswith(os.path.dirname(exe) + os.sep)


def check_update():
    req = urllib.request.Request(UPDATE_URL + "?t=%d" % time.time(), headers={"User-Agent": "EX-SPORTS-SFC27/" + APP_VERSION})
    m = json.loads(urllib.request.urlopen(req, timeout=10).read(65536).decode("utf-8"))
    ver = str(m["version"])
    if vtuple(ver) > vtuple(APP_VERSION):
        link = m.get("portable_url") if is_portable() else (m.get("installer_url") or m.get("url"))
        return "newer", {"version": ver, "notes": m.get("notes", ""), "link": link or m.get("release_url") or RELEASES_URL,
                         "portable": is_portable(), "page": m.get("release_url") or RELEASES_URL}
    return "latest", "You have the latest version (%s)." % APP_VERSION


INTRO_SECS = 6.0                      # v1.0.0.2 EX SPORTS intro before the title screen (every launch, skippable)
DEFAULT_SETTINGS = {"duration": 0, "home": 1, "away": 0, "home_kit": "yellow", "master": 0.9, "sfx": 0.8, "music": 0.5, "voice": 0.9,
                    "fov": 60, "quality": "HIGH", "fullscreen": False,
                    "rec_quality": "720p30", "rec_watermark": False}
DURATIONS = (0, 4, 8, 12, 90)
SKY = (0.55, 0.7, 0.9)


# ====================================================================== world (stadium + surroundings)
class Grid:
    def __init__(self): self.rects = []
    def add_rect(self, r, tag): self.rects.append((r, tag))
    def add_circle(self, x, y, r, tag): pass


class World:
    def __init__(self, app):
        self.app = app; self.mb = {}; self.grid = Grid(); self.root = app.render.attach_new_node("world")

    def M(self, mat, chunk=(0, 0)):
        k = (chunk, mat)
        if k not in self.mb: self.mb[k] = MB("%s_%s" % (mat, chunk))
        return self.mb[k]

    @staticmethod
    def ground_z(x, y): return 0.035

    def build(self):
        import xs_shaders
        F.build_stadium(self)
        g = self.M("ground"); R = 900.0; cx, cy = F.CX, F.CY
        g.quad((cx - R, cy - R, -0.02), (cx + R, cy - R, -0.02), (cx + R, cy + R, -0.02), (cx - R, cy + R, -0.02), (0.36, 0.48, 0.26, 1), n=(0, 0, 1))
        # plaza around the stadium + a few car parks / paths
        g.quad((cx - 70, cy - 85, -0.01), (cx + 70, cy - 85, -0.01), (cx + 70, cy + 85, -0.01), (cx - 70, cy + 85, -0.01), (0.55, 0.55, 0.53, 1), n=(0, 0, 1))
        # distant skyline (plain blocks, no lights)
        rng = random.Random(7); sk = self.M("skyline")
        for i in range(70):
            a = i / 70.0 * 2 * math.pi + rng.uniform(-0.03, 0.03); d = rng.uniform(260, 420)
            x, y = cx + math.cos(a) * d, cy + math.sin(a) * d; w = rng.uniform(12, 30); h = rng.uniform(20, 95)
            c = rng.choice([(0.62, 0.66, 0.72, 1), (0.7, 0.68, 0.64, 1), (0.5, 0.56, 0.64, 1), (0.78, 0.78, 0.8, 1)])
            sk.box(x - w / 2, y - w / 2, 0, x + w / 2, y + w / 2, h, c)
        for i in range(90):                               # park trees
            a = rng.uniform(0, 2 * math.pi); d = rng.uniform(95, 200); x, y = cx + math.cos(a) * d, cy + math.sin(a) * d
            sk.box(x - 0.25, y - 0.25, 0, x + 0.25, y + 0.25, 2.2, (0.35, 0.25, 0.16, 1))
            sk.box(x - 1.6, y - 1.6, 2.0, x + 1.6, y + 1.6, 5.2, (0.2, 0.42, 0.2, 1))
        for (ch, mat), mb in self.mb.items():
            if not len(mb): continue
            n = mb.node(); n.reparent_to(self.root)
            xs_shaders.apply(n, self.app, gloss=0.05, sheen=0.3)
            mt = Material("world"); mt.set_base_color((1, 1, 1, 1)); mt.set_roughness(0.85); n.set_material(mt, 1)
        self.build_sky()

    def build_sky(self):
        mb = MB("sky"); R = 1500.0; nu, nv = 32, 12
        for i in range(nu):
            for j in range(nv):
                a0, a1 = i / nu * 2 * math.pi, (i + 1) / nu * 2 * math.pi
                b0, b1 = -0.15 + j / nv * (math.pi / 2 + 0.15), -0.15 + (j + 1) / nv * (math.pi / 2 + 0.15)
                P = lambda a, b: (R * math.cos(b) * math.cos(a), R * math.cos(b) * math.sin(a), R * math.sin(b))
                T = lambda a, b: (a / (2 * math.pi), 0.5 + b / math.pi)
                mb.quad(P(a0, b0), P(a0, b1), P(a1, b1), P(a1, b0), (1, 1, 1, 1), (T(a0, b0), T(a0, b1), T(a1, b1), T(a1, b0)))
        s = mb.node(); s.reparent_to(self.app.camera); s.set_compass(); s.set_bin("background", 0); s.set_depth_write(False)
        s.set_light_off(); s.set_fog_off(); s.set_two_sided(True); s.set_shader_off(); s.set_texture(self.app.envday)
        self.sky = s


# ====================================================================== game state
class Game:
    def __init__(self, app):
        self.app = app; self.world = app.world; self.match = None; self.player = None; self.overlay = None
        self.online = Online(self); self._toast = None; self._toast_t = 0.0

    @property
    def settings(self): return self.app.settings

    @property
    def profile(self): return self.app.profile

    def me(self): return self.player

    def down(self, *names): return any(n in self.app.held for n in names)

    def toast(self, msg, t=2.5):
        if self._toast is not None: self._toast.destroy()
        self._toast = U.text(self.app.aspect2d, msg, (0, -0.86), 0.04, fg=(1, 1, 1, 1), shadow=(0, 0, 0, 1), font=U.FONT_PLAIN); self._toast_t = t

    def close_overlay(self):
        if self.overlay is not None and self.overlay is not self.online.ui:
            try: self.overlay.destroy()
            except Exception: pass
        self.overlay = None

    def club_name(self, i): return F.CLUBS[i % len(F.CLUBS)][0]

    def start_match(self, **kw):
        if self.match is not None: return
        self.app.clear_screen(); self.app.play_music(None)
        self.match = F.Match(self, **kw)
        self.app.exrec.begin("ARENA" if kw.get("arena") else "ONLINE" if kw.get("online") is not None else "KICK OFF")

    def quick_match(self, autoplay=False):
        st = self.settings
        self.start_match(home_club=st["home"], away_club=st["away"], minutes_real=float(st["duration"]), kits=[st.get("home_kit"), None], autoplay=autoplay)

    def start_match_view(self, setup):
        if self.match is not None: return
        self.app.clear_screen(); self.app.play_music(None)
        try: self.match = F.Match(self, mode="view", setup=setup, online=self.online)
        except Exception as e: log_error(e); self.match = None
        if self.match is not None: self.app.exrec.begin("ONLINE")

    def match_over(self, again):
        self.app.hide_pause(); self.app.exrec.end()
        if again: return
        if getattr(self, "arena_return", False):
            self.arena_return = False; self.app.play_music("music_menu"); self.app.arena.show_hub(); return
        if self.online.sess is not None: self.app.play_music("music_menu"); self.online.open()
        else: self.app.show_menu()

    def step(self, dt):
        self.online.update(dt)
        m = self.match
        if m is not None:
            paused = self.app.pause_ui is not None and m.online is None and m.mode == "sim"
            if not paused: m.step(dt)
        if self._toast is not None:
            self._toast_t -= dt
            if self._toast_t <= 0: self._toast.destroy(); self._toast = None


# ====================================================================== app
class App(ShowBase):
    VERSION = APP_VERSION
    BASE = BASE
    DATA = DATA

    def __init__(self):
        ShowBase.__init__(self)
        self.disable_mouse(); self.log_error = log_error
        self.settings = dict(DEFAULT_SETTINGS); self.profile = A.clean(dict(A.preset(1), name="PLAYER"))
        try:
            sd = json.load(open(os.path.join(DATA, "settings.json"), encoding="utf-8"))
            self.settings.update(sd.get("settings", {})); self.profile = A.clean(sd.get("profile") or self.profile)
        except Exception: pass
        Aj = lambda *p: os.path.join(BASE, "assets", *p)
        U.init_fonts(self.loader, Aj("ui_font.ttf"), Aj("ui_plain.ttf"), None)
        U.SFX = lambda n: self.sfx(n, 0.5)
        DirectGuiGlobals.setDefaultClickSound(None); DirectGuiGlobals.setDefaultRolloverSound(None)
        if U.FONT_PLAIN: DirectGuiGlobals.setDefaultFont(U.FONT_PLAIN)
        wp = WindowProperties(); wp.set_title(APP_TITLE + " " + EDITION); self.win.request_properties(wp) if hasattr(self.win, "request_properties") else None
        self.set_background_color(*SKY, 1)
        self.camLens.set_fov(60); self.camLens.set_near_far(0.2, 3000)
        self.render.set_antialias(AntialiasAttrib.M_multisample)
        # shader inputs (daylight only - no bloom, no glow)
        self.campos = PTA_LVecBase3f.empty_array(1); self.campos_np = self.campos
        self.fogcol = Vec3(*SKY); self.fogden = 0.0011
        self.envtex = self.loader.load_texture(Filename.from_os_specific(Aj("tex", "env.png")))
        self.envday = self.loader.load_texture(Filename.from_os_specific(Aj("tex", "sky_day.jpg")))
        img = PNMImage(4, 4, 3); img.fill(0.5, 0.5, 1.0); self.flat_nmap = Texture("flatn"); self.flat_nmap.load(img)
        self.render.set_shader_input("dayk", 1.0); self.render.set_shader_input("fogday", Vec3(0.72, 0.8, 0.9))
        self.render.set_shader_input("sundir", Vec3(0.45, -0.55, 0.62)); self.render.set_shader_input("envday", self.envday)
        self._sfx = {}
        for n in ("click", "checkpoint", "beep", "go", "win", "switch", "bump"):
            try: self._sfx[n] = self.loader.load_sfx(Filename.from_os_specific(Aj("sfx", n + ".wav")))
            except Exception: pass
        for n in ("intro", "intro_vo1", "intro_vo2"):
            try: self._sfx[n] = self.loader.load_sfx(Filename.from_os_specific(Aj("sfx", n + ".wav")))
            except Exception: pass
        self.music = {}
        try:
            s = self.loader.load_music(Filename.from_os_specific(Aj("sfx", "music_menu.wav"))); s.set_loop(True); self.music["music_menu"] = s
        except Exception: pass
        self.cur_music = None
        self.tex_title = self.loader.load_texture(Filename.from_os_specific(Aj("title.jpg")))
        self.world = World(self); self.world.build()
        self.game = Game(self); F.add_signs(self.game)
        self.screen = None; self.pause_ui = None; self.dialog = None; self._upd = None; self.t = 0.0
        self.held = set()
        for k in ("w", "a", "s", "d", "arrow_up", "arrow_down", "arrow_left", "arrow_right", "shift", "lshift", "rshift"):
            self.accept(k, self.held.add, [k if "shift" not in k else "shift"])
            self.accept(k + "-up", self.held.discard, [k if "shift" not in k else "shift"])
        for k in ("space", "f", "r"): self.accept(k, self.key, [k])
        self.accept("escape", self.on_escape); self.accept("enter", self.on_enter)
        self.accept("window-event", self._on_window_event)
        if self.settings.get("fullscreen"): self.apply_fullscreen()
        self.task_mgr.add(self._frame, "frame", sort=50)
        self.intro = None
        import xs_arena; self.arena = xs_arena.Arena(self)
        import xs_recorder; self.exrec = xs_recorder.Recorder(self)
        self.accept("f9", self.exrec.toggle); self.accept("f10", self.exrec.save_moment)
        if os.environ.get("EXS_NO_INTRO"): self.show_title()
        else: self.start_intro()
        if os.environ.get("EXS_SMOKE"): self.do_method_later(1.0, self._smoke, "exs-smoke")
        ts = os.environ.get("EXS_TESTSCRIPT")
        if ts and not getattr(sys, "frozen", False):
            self.do_method_later(1.0, lambda t: exec(open(ts).read(), {"app": self, "__name__": "exstest"}) or t.done, "exs-test")

    # needed by the stadium / avatar code
    @property
    def sfx_names(self): return tuple(self._sfx)

    def club_name(self, i): return F.CLUBS[i % len(F.CLUBS)][0]

    # ------------------------------------------------------------ helpers
    def vol(self, kind): return float(self.settings.get("master", 0.9)) * float(self.settings.get(kind, 0.8))

    def sfx(self, name, vol=1.0):
        s = self._sfx.get(name)
        if s: s.set_volume(vol * self.vol("sfx")); s.play()
        rec = getattr(self, "exrec", None)
        if s and rec is not None: rec.note_sound(name, vol * self.vol("sfx"))    # EX SPORTS RECORDER mixes the game's own sounds

    def play_music(self, name):
        if self.cur_music == name:
            s = self.music.get(name)
            if s: s.set_volume(self.vol("music") * 0.6)
            return
        for k, s in self.music.items():
            if k != name: s.stop()
        s = self.music.get(name); self.cur_music = name
        if s: s.set_volume(self.vol("music") * 0.6); s.play()

    def save(self):
        try:
            json.dump({"settings": self.settings, "profile": self.profile}, open(os.path.join(DATA, "settings.json"), "w", encoding="utf-8"), indent=1)
        except Exception as e: log_error(e)

    def apply_fullscreen(self):
        wp = WindowProperties()
        if self.settings.get("fullscreen"): wp.set_fullscreen(True); wp.set_size(self.pipe.get_display_width(), self.pipe.get_display_height())
        else: wp.set_fullscreen(False); wp.set_size(1280, 720)
        if hasattr(self.win, "request_properties"): self.win.request_properties(wp)

    def _on_window_event(self, win):
        if win is self.win and win is not None and not win.get_properties().get_open(): self.userExit()

    def _frame(self, task):
        dt = min(globalClock.get_dt(), 0.1); self.t += dt
        cam = self.camera.get_pos(self.render); self.campos.set_element(0, cam)
        self.game.step(dt)
        if self.game.match is None:                     # slow orbit over the stadium behind the menus
            a = self.t * 0.05; r = 95.0
            self.camera.set_pos(F.CX + math.cos(a) * r, F.CY + math.sin(a) * r * 1.2, 26 + 6 * math.sin(self.t * 0.07))
            self.camera.look_at(F.CX, F.CY, 0); self.camLens.set_fov(55)
        return task.cont

    # ------------------------------------------------------------ input
    def key(self, k):
        if self.intro is not None:
            if k == "space": self.skip_intro()
            return
        m = self.game.match
        if m is not None and self.pause_ui is None: m.key(k)

    def on_enter(self):
        if self.intro is not None: self.skip_intro(); return
        if self.screen == "title": self.show_menu()

    def on_escape(self):
        g = self.game
        if self.intro is not None: self.skip_intro(); return
        if self.dialog is not None: self._close_dialog(); return
        if self.screen and self.screen.startswith("arena") and g.match is None: self.arena.back(); return
        if g.match is not None:
            if self.pause_ui is not None: self.hide_pause()
            else: self.show_pause()
            return
        if g.online.ui is not None:
            if g.online.view != "main": g.online.goto("main")
            else: g.online.back()
            return
        if self.screen in ("teams", "settings", "recordings"): self.save(); self.show_menu()

    # ------------------------------------------------------------ screens
    def clear_screen(self):
        if getattr(self, "_scr", None) is not None: self._scr.destroy()
        self._scr = None; self.screen = None
        self.game.online.close()

    def _frame_ui(self, name, dim=0.35):
        self.clear_screen(); self.screen = name
        o = self._scr = DirectFrame(parent=self.aspect2d, frameColor=(0, 0, 0, dim), frameSize=(-4, 4, -2, 2), state=DGG.NORMAL)
        return o

    def _footer(self, o):
        U.text(o, COPYRIGHT + "     v" + APP_VERSION, (0, -0.95), 0.03, fg=(1, 1, 1, 0.85), font=U.FONT_PLAIN, shadow=(0, 0, 0, 1))

    def _title_block(self, o, x, y, sc=1.0):
        U.text(o, APP_TITLE, (x, y), 0.13 * sc, fg=(1, 0.84, 0.08, 1), shadow=(0, 0, 0, 1))
        U.text(o, EDITION, (x, y - 0.1 * sc), 0.055 * sc, fg=(1, 1, 1, 1), shadow=(0, 0, 0, 1))

    # ------------------------------------------------------------ v1.0.0.2 intro (6 s, skippable, every launch)
    def start_intro(self):
        """Black screen, the EX SPORTS logo fades and scales in (~1 s), holds with a slow gentle scale, then everything
        fades out (0.8 s) into the title screen. Original sting + en-GB voiceover. No glow / bloom."""
        self.show_title(music=False)                       # built now, under the black intro card (no stall at the fade)
        tex = self.loader.load_texture(Filename.from_os_specific(os.path.join(BASE, "assets", "intro_logo.png")))
        tex.set_minfilter(SamplerState.FT_linear_mipmap_linear); tex.set_magfilter(SamplerState.FT_linear); tex.set_anisotropic_degree(4)
        tex.set_wrap_u(SamplerState.WM_clamp); tex.set_wrap_v(SamplerState.WM_clamp)
        o = DirectFrame(parent=self.aspect2d, frameColor=(0.0, 0.0, 0.0, 1), frameSize=(-60, 60, -60, 60), state=DGG.NORMAL, sortOrder=1000)
        o.set_bin("gui-popup", 1000); o.set_transparency(TransparencyAttrib.M_alpha)
        o.bind(DGG.B1PRESS, lambda e: self.skip_intro())
        logo = OnscreenImage(image=tex, parent=o, pos=(0, 0, 0), scale=0.45)
        logo.set_transparency(TransparencyAttrib.M_alpha); logo.set_color_scale(1, 1, 1, 0)
        self.intro = {"root": o, "logo": logo, "t0": None, "fired": set(), "titled": False}
        self.task_mgr.add(self._intro_task, "exs-intro", sort=60)

    def _intro_play(self, name, kind):
        s = self._sfx.get(name)
        if s:
            s.set_volume(float(self.settings.get("master", 0.9)) * float(self.settings.get(kind, 0.8)))
            s.play()

    def _intro_task(self, task):
        it = self.intro
        if it is None: return task.done
        now = time.time()
        if it["t0"] is None: it["t0"] = now                 # start counting on the first drawn frame
        e = now - it["t0"]
        ease = lambda x: 1 - (1 - max(0.0, min(1.0, x))) ** 3
        # timeline (s): 0.2-1.2 logo in | 1.2-5.2 hold, slow scale | 5.2-6.0 fade out to the title screen
        a_in = ease((e - 0.2) / 1.0)
        a_out = 1.0 - max(0.0, min(1.0, (e - 5.2) / 0.8))
        sc = 0.86 + 0.14 * a_in + 0.04 * ease((e - 1.2) / 4.8)
        top = float(getattr(self, "a2dTop", 1.0)) or 1.0; right = float(getattr(self, "a2dRight", 1.0)) or 1.0
        r = min(0.45 * top, 0.92 * right)                   # ~45 % of the screen height, never wider than the window
        it["logo"].set_scale(r * sc); it["logo"].set_color_scale(1, 1, 1, a_in * a_out)
        it["root"]["frameColor"] = (0.0, 0.0, 0.0, a_out)
        for at, name, kind in ((0.1, "intro", "sfx"), (1.0, "intro_vo1", "voice"), (2.75, "intro_vo2", "voice")):
            if e >= at and name not in it["fired"]:
                it["fired"].add(name); self._intro_play(name, kind)
        if e >= 5.2 and not it["titled"]:
            it["titled"] = True                              # the title is already built underneath; the fade reveals it
            if self.screen == "title": self.play_music("music_menu")
        if e >= INTRO_SECS:
            self._end_intro(e); return task.done
        return task.cont

    def _end_intro(self, e, skipped=False):
        it = self.intro
        if it is None: return
        self.intro = None; it["root"].destroy(); self.task_mgr.remove("exs-intro")
        if skipped:
            for n in ("intro", "intro_vo1", "intro_vo2"):
                s = self._sfx.get(n)
                if s: s.stop()
        if not it["titled"] and self.screen == "title": self.play_music("music_menu")
        self.intro_secs = e; self.intro_skipped = skipped

    def skip_intro(self):
        it = self.intro
        if it is None: return
        self._end_intro(time.time() - (it["t0"] or time.time()), skipped=True)

    def show_title(self, music=True):
        o = self._frame_ui("title", 0.25)
        if music: self.play_music("music_menu")
        img = OnscreenImage(image=self.tex_title, parent=o, pos=(-0.62, 0, 0.04), scale=(0.78, 1, 0.78))
        U.panel(o, -1.42, 0.18, -0.76, 0.84, col=(0, 0, 0, 0), edge=(1, 0.84, 0.08, 1)); img.reparent_to(o)
        self._title_block(o, 0.85, 0.32)
        U.button(o, "PRESS PLAY", (0.85, -0.12), self.show_menu, w=0.3, h=0.07, scale=0.06, hint="Enter")
        self._footer(o)

    def show_menu(self):
        self.hide_pause(); o = self._frame_ui("menu", 0.35); self.play_music("music_menu")
        img = OnscreenImage(image=self.tex_title, parent=o, pos=(-0.85, 0, 0.0), scale=(0.55, 1, 0.55))
        self._title_block(o, 0.55, 0.66, 0.8)
        d = self.settings["duration"]
        items = [("KICK OFF", lambda: self.game.quick_match()), ("SFC 27 ARENA", self.arena.show_hub),
                 ("ONLINE", lambda: (self.clear_screen(), self.game.online.open())),
                 ("TEAMS", self.show_teams), ("SETTINGS", self.show_settings), ("RECORDINGS", self.show_recordings), ("CHECK FOR UPDATES", self.check_updates),
                 ("QUIT", self.userExit)]
        self.menu_labels = [t for t, _ in items]
        for i, (t, fn) in enumerate(items):
            U.button(o, t, (0.55, 0.44 - i * 0.105), fn, w=0.36, h=0.042, scale=0.04,
                     edge=(0.3, 1.0, 0.45, 1) if i == 0 else (1, 0.35, 0.3, 1) if t == "QUIT" else U.PINK)
        c0, c1 = self.club_name(self.settings["home"]), self.club_name(self.settings["away"])
        U.text(o, "%s%s  vs  %s   -   %s" % (c0, " (YELLOW KIT)" if self.settings.get("home_kit") == "yellow" else "", c1, "UNLIMITED" if not d else "%d MIN" % d),
               (0.55, -0.56), 0.028, fg=(1, 1, 1, 0.9), font=U.FONT_PLAIN, shadow=(0, 0, 0, 1))
        self._footer(o)

    def show_recordings(self, page=0):
        import xs_recorder as XR
        o = self._frame_ui("recordings", 0.6)
        U.panel(o, -1.3, 1.3, -0.82, 0.82, edge=(0.9, 0.15, 0.15, 1))
        U.text(o, "RECORDINGS", (0, 0.7), 0.07, fg=(1, 0.3, 0.3, 1))
        d = XR.downloads_dir(); clips = self.exrec.clips(); per = 8; pages = max(1, (len(clips) + per - 1) // per); page = min(page, pages - 1)
        U.text(o, "EX SPORTS RECORDER clips in your Downloads folder:  %s" % d, (0, 0.6), 0.026, fg=(0.85, 0.88, 0.95, 1), font=U.FONT_PLAIN)
        if not clips:
            U.text(o, "No clips yet. During a match press F9 to record, or F10 to save the last 30 seconds.", (0, 0.2), 0.03, font=U.FONT_PLAIN)
        for k, p in enumerate(clips[page * per:(page + 1) * per]):
            y = 0.47 - k * 0.11; mb = os.path.getsize(p) / 1e6
            U.text(o, "%s   (%.1f MB)" % (os.path.basename(p)[:-4], mb), (-1.2, y - 0.012), 0.027, align=TextNode.A_left, font=U.FONT_PLAIN)
            U.button(o, "PLAY", (1.12, y), lambda p=p: XR.open_path(p), w=0.1, h=0.035, scale=0.028, edge=(0.3, 1.0, 0.45, 1))
        if pages > 1:
            U.button(o, "<", (-0.2, -0.45), lambda: self.show_recordings(max(0, page - 1)), w=0.04, h=0.03, scale=0.03)
            U.text(o, "%d/%d" % (page + 1, pages), (0, -0.46), 0.03, font=U.FONT_PLAIN)
            U.button(o, ">", (0.2, -0.45), lambda: self.show_recordings(min(pages - 1, page + 1)), w=0.04, h=0.03, scale=0.03)
        U.button(o, "OPEN DOWNLOADS FOLDER", (-0.35, -0.62), lambda: XR.open_path(d), w=0.3, h=0.045, scale=0.032)
        U.button(o, "BACK", (0.35, -0.62), self.show_menu, w=0.2, h=0.045, scale=0.036, hint="Esc")

    def show_teams(self):
        o = self._frame_ui("teams", 0.55); st = self.settings; pf = self.profile
        U.panel(o, -1.2, 1.2, -0.82, 0.82, edge=U.PINK)
        U.text(o, "TEAMS", (0, 0.7), 0.07, fg=U.PINK)
        U.text(o, "All clubs are fictional.", (0, 0.63), 0.028, fg=(0.85, 0.88, 0.95, 1), font=U.FONT_PLAIN)
        def cyc(key, d):
            st[key] = (st[key] + d) % len(F.CLUBS)
            if st["home"] == st["away"]: st[key] = (st[key] + d) % len(F.CLUBS)
            self.show_teams()
        for k, (lbl, key) in enumerate((("YOUR CLUB", "home"), ("OPPONENT", "away"))):
            yy = 0.5 - k * 0.11; c = F.CLUBS[st[key]]
            col = F.YELLOW if (key == "home" and st.get("home_kit") == "yellow") else c[2]
            U.text(o, lbl, (-1.05, yy - 0.012), 0.034, align=TextNode.A_left, font=U.FONT_PLAIN)
            U.text(o, c[0], (0.05, yy - 0.012), 0.04, fg=tuple(col) + (1,), shadow=(0, 0, 0, 1))
            U.button(o, "<", (-0.5, yy), lambda key=key: cyc(key, -1), w=0.035, h=0.035, scale=0.035)
            U.button(o, ">", (0.6, yy), lambda key=key: cyc(key, 1), w=0.035, h=0.035, scale=0.035)
        yk = st.get("home_kit") == "yellow"
        U.text(o, "YOUR KIT", (-1.05, 0.26), 0.034, align=TextNode.A_left, font=U.FONT_PLAIN)
        U.button(o, "CLUB COLOURS", (-0.2, 0.275), lambda: (st.__setitem__("home_kit", None), self.show_teams()), w=0.17, h=0.035, scale=0.03,
                 edge=(1, 1, 1, 1) if not yk else (0.4, 0.4, 0.45, 1))
        U.button(o, "YELLOW KIT", (0.25, 0.275), lambda: (st.__setitem__("home_kit", "yellow"), self.show_teams()), w=0.17, h=0.035, scale=0.03,
                 edge=F.YELLOW + (1,) if yk else (0.4, 0.4, 0.45, 1))
        U.text(o, "YOUR PLAYER (also how online friends see you)", (0, 0.12), 0.034, fg=U.CYAN, font=U.FONT_PLAIN)
        U.text(o, "NAME", (-1.05, 0.02), 0.032, align=TextNode.A_left, font=U.FONT_PLAIN)
        ne = DirectEntry(parent=o, initialText=pf["name"], width=10, numLines=1, scale=0.042, pos=(-0.55, 0, 0.015), frameColor=(0.06, 0.08, 0.18, 1),
                         text_fg=(1, 1, 1, 1), entryFont=U.FONT_PLAIN, command=lambda t: self._set_prof(name=t)); self._name_ent = ne
        U.button(o, "OK", (0.0, 0.03), lambda: self._set_prof(name=ne.get()), w=0.05, h=0.03, scale=0.028)
        rows = [("LOOK", "preset", [p["name"] for p in A.PRESETS]), ("SKIN", "skin", [n for n, _ in A.SKINS]), ("HAIR", "hair", A.HAIRS),
                ("HAIR COLOUR", "hair_col", [n for n, _ in A.HAIR_COLS])]
        for k, (lbl, key, opts) in enumerate(rows):
            yy = -0.1 - k * 0.1
            if key == "preset": i = getattr(self, "_preset_i", 0)
            else: cur = pf[key]; i = cur if isinstance(cur, int) else opts.index(cur)
            U.text(o, lbl, (-1.05, yy - 0.01), 0.032, align=TextNode.A_left, font=U.FONT_PLAIN)
            U.text(o, str(opts[i]).upper(), (-0.05, yy - 0.01), 0.032, fg=(1, 0.9, 0.3, 1), font=U.FONT_PLAIN)
            def c2(d, key=key, opts=opts):
                if key == "preset":
                    self._preset_i = (getattr(self, "_preset_i", 0) + d) % len(A.PRESETS)
                    self.profile = A.clean(dict(A.preset(self._preset_i), name=self.profile["name"])); self.show_teams(); return
                cur = self.profile[key]; i = cur if isinstance(cur, int) else opts.index(cur); i = (i + d) % len(opts)
                self._set_prof(**{key: i if isinstance(cur, int) else opts[i]})
            U.button(o, "<", (-0.4, yy), lambda c=c2: c(-1), w=0.03, h=0.03, scale=0.03)
            U.button(o, ">", (0.3, yy), lambda c=c2: c(1), w=0.03, h=0.03, scale=0.03)
        U.button(o, "DONE", (0, -0.68), lambda: (self.save(), self.show_menu()), w=0.2, h=0.045, scale=0.04, hint="Esc")

    def _set_prof(self, **kw):
        self.profile = A.clean(dict(self.profile, **kw)); self.save(); self.show_teams()

    def show_settings(self):
        o = self._frame_ui("settings", 0.55); st = self.settings
        U.panel(o, -1.2, 1.2, -0.82, 0.82, edge=U.PINK)
        U.text(o, "SETTINGS", (0, 0.7), 0.07, fg=U.PINK)
        U.text(o, "MATCH LENGTH", (-1.05, 0.52), 0.034, align=TextNode.A_left, font=U.FONT_PLAIN)
        for k, mn in enumerate(DURATIONS):
            U.button(o, "UNLIMITED" if not mn else "%d MIN" % mn, (-0.38 + k * 0.29, 0.535), lambda mn=mn: (st.__setitem__("duration", mn), self.show_settings()),
                     w=0.13, h=0.035, scale=0.028, edge=U.PINK if st["duration"] == mn else (0.4, 0.4, 0.45, 1))
        U.text(o, "Unlimited: the clock counts up and the match goes on until you press END MATCH (Esc).", (0, 0.45), 0.025,
               fg=(0.85, 0.88, 0.95, 1), font=U.FONT_PLAIN)
        U.text(o, "GRAPHICS", (-1.05, 0.33), 0.034, align=TextNode.A_left, font=U.FONT_PLAIN)
        U.button(o, "FULLSCREEN: %s" % ("ON" if st.get("fullscreen") else "OFF"), (-0.25, 0.345),
                 lambda: (st.__setitem__("fullscreen", not st.get("fullscreen")), self.apply_fullscreen(), self.show_settings()), w=0.2, h=0.035, scale=0.028)
        U.button(o, "CAMERA FOV: %d" % st.get("fov", 60), (0.25, 0.345),
                 lambda: (st.__setitem__("fov", {50: 60, 60: 70, 70: 50}.get(st.get("fov", 60), 60)), self.show_settings()), w=0.2, h=0.035, scale=0.028)
        U.button(o, "QUALITY: %s" % st.get("quality", "HIGH"), (0.72, 0.345),
                 lambda: (st.__setitem__("quality", "LOW" if st.get("quality") == "HIGH" else "HIGH"), self.apply_quality(), self.show_settings()),
                 w=0.2, h=0.035, scale=0.028)
        U.text(o, "AUDIO", (-1.05, 0.17), 0.034, align=TextNode.A_left, font=U.FONT_PLAIN)
        for k, (lbl, key) in enumerate((("MASTER", "master"), ("EFFECTS", "sfx"), ("MUSIC", "music"), ("VOICE", "voice"))):
            yy = 0.17 - k * 0.09
            U.text(o, "%s  %d%%" % (lbl, round(st[key] * 100)), (-0.3, yy - 0.01), 0.03, align=TextNode.A_left, font=U.FONT_PLAIN)
            for j, d in enumerate((-0.1, 0.1)):
                U.button(o, "-" if d < 0 else "+", (0.3 + j * 0.1, yy), lambda key=key, d=d: self._vol(key, d), w=0.035, h=0.03, scale=0.035)
        U.text(o, "CONTROLS", (-1.05, -0.17), 0.034, align=TextNode.A_left, font=U.FONT_PLAIN)
        U.text(o, "WASD / ARROWS move     SPACE pass     F shoot     R tackle     SHIFT sprint     ESC pause / END MATCH",
               (0, -0.25), 0.027, fg=(0.9, 0.92, 1, 1), font=U.FONT_PLAIN)
        U.text(o, "EX SPORTS RECORDER:   F9 start / stop recording     F10 save the last 30 seconds     clips go to Downloads",
               (0, -0.31), 0.025, fg=(1, 0.6, 0.6, 1), font=U.FONT_PLAIN)
        U.text(o, "RECORDER", (-1.05, -0.5), 0.034, align=TextNode.A_left, font=U.FONT_PLAIN)
        for k, q in enumerate(("720p30", "1080p30", "1080p60")):
            U.button(o, q, (-0.42 + k * 0.27, -0.485), lambda q=q: (st.__setitem__("rec_quality", q), self.show_settings()), w=0.12, h=0.032, scale=0.026,
                     edge=(0.9, 0.15, 0.15, 1) if st.get("rec_quality", "720p30") == q else (0.4, 0.4, 0.45, 1))
        U.button(o, "WATERMARK: %s" % ("ON" if st.get("rec_watermark") else "OFF"), (0.55, -0.485),
                 lambda: (st.__setitem__("rec_watermark", not st.get("rec_watermark")), self.show_settings()), w=0.17, h=0.032, scale=0.026)
        U.text(o, "Online play needs no admin rights or firewall setup. Your game always makes the first call (outbound-first).",
               (0, -0.39), 0.024, fg=(0.8, 0.85, 1, 1), font=U.FONT_PLAIN)
        U.button(o, "DONE", (0, -0.68), lambda: (self.save(), self.show_menu()), w=0.2, h=0.045, scale=0.04, hint="Esc")

    def _vol(self, key, d):
        self.settings[key] = round(max(0.0, min(1.0, self.settings[key] + d)), 2); self.play_music(self.cur_music); self.sfx("click", 0.6); self.show_settings()

    def apply_quality(self):
        hi = self.settings.get("quality", "HIGH") == "HIGH"
        self.render.set_antialias(AntialiasAttrib.M_multisample if hi else AntialiasAttrib.M_none)

    # ------------------------------------------------------------ pause (during a match)
    def show_pause(self):
        m = self.game.match
        if m is None or self.pause_ui is not None: return
        o = self.pause_ui = DirectFrame(parent=self.aspect2d, frameColor=(0, 0, 0, 0.55), frameSize=(-4, 4, -2, 2), state=DGG.NORMAL)
        U.panel(o, -0.45, 0.45, -0.5, 0.5, edge=U.PINK)
        U.text(o, "PAUSED" if (m.online is None and m.mode == "sim") else "MATCH MENU", (0, 0.36), 0.07, fg=U.PINK)
        U.text(o, "%s %d - %d %s   %s" % (m.clubs[0][1], m.score[0], m.score[1], m.clubs[1][1], m.clock_text()), (0, 0.27), 0.035, fg=U.CYAN)
        def end(): self.hide_pause(); m.end_match()
        items = [("RESUME", self.hide_pause)]
        if not m.done: items.append(("LEAVE MATCH" if m.mode == "view" else "END MATCH", end))
        else: items.append(("LEAVE STADIUM", lambda: (self.hide_pause(), m.quit())))
        items.append(("RECORDER", self.show_recorder_panel))
        items.append(("QUIT GAME", self.userExit))
        for i, (t, fn) in enumerate(items):
            U.button(o, t, (0, 0.14 - i * 0.12), fn, w=0.3, h=0.046, scale=0.04, edge=(1.0, 0.75, 0.2, 1) if "MATCH" in t else
                     (0.9, 0.15, 0.15, 1) if t == "RECORDER" else U.PINK)

    def show_recorder_panel(self):
        """pause menu > RECORDER"""
        if self.pause_ui is None: return
        r = self.exrec; o = self.pause_ui
        for c in o.get_children(): c.remove_node()
        U.panel(o, -0.62, 0.62, -0.5, 0.5, edge=(0.9, 0.15, 0.15, 1))
        U.text(o, "EX SPORTS RECORDER", (0, 0.36), 0.06, fg=(1, 0.3, 0.3, 1))
        st = ("RECORDING  %d:%02d" % (int(r.t() - r.recording) // 60, int(r.t() - r.recording) % 60)) if r.recording is not None else "not recording"
        U.text(o, "%s     quality %s     saves to Downloads" % (st, r.quality()), (0, 0.27), 0.028, fg=(1, 1, 1, 0.9), font=U.FONT_PLAIN)
        U.button(o, "STOP RECORDING" if r.recording is not None else "START RECORDING", (0, 0.13),
                 lambda: (self.hide_pause(), r.toggle()), w=0.34, h=0.046, scale=0.036, hint="F9", edge=(0.9, 0.15, 0.15, 1))
        U.button(o, "SAVE MOMENT (LAST 30 S)", (0, 0.01), lambda: (self.hide_pause(), r.save_moment()), w=0.34, h=0.046, scale=0.034, hint="F10")
        U.button(o, "BACK", (0, -0.13), lambda: (self.hide_pause(), self.show_pause()), w=0.34, h=0.046, scale=0.036, hint="Esc")
        U.text(o, "Clips: MP4 (H.264 + AAC), ready to upload to YouTube yourself. Nothing is uploaded automatically.", (0, -0.3), 0.024,
               fg=(0.85, 0.88, 0.95, 1), font=U.FONT_PLAIN, wrap=40)

    def hide_pause(self):
        if self.pause_ui is not None: self.pause_ui.destroy(); self.pause_ui = None

    # ------------------------------------------------------------ updates
    def _dialog(self, msg, buttons):
        self._close_dialog()
        o = self.dialog = DirectFrame(parent=self.aspect2d, frameColor=(0, 0, 0, 0.6), frameSize=(-4, 4, -2, 2), state=DGG.NORMAL)
        U.panel(o, -0.8, 0.8, -0.4, 0.4, edge=U.PINK)
        U.text(o, msg, (0, 0.24), 0.036, font=U.FONT_PLAIN, wrap=40)
        for i, (t, fn) in enumerate(buttons):
            U.button(o, t, ((i - (len(buttons) - 1) / 2) * 0.55, -0.27), fn, w=0.25, h=0.045, scale=0.034)

    def _close_dialog(self):
        if self.dialog is not None: self.dialog.destroy(); self.dialog = None

    def check_updates(self):
        self._dialog("Checking for updates...", [])
        def work():
            try: self._upd = check_update()
            except Exception as e: self._upd = ("error", "Could not check for updates:\n%s" % str(e)[:80])
        threading.Thread(target=work, daemon=True).start()
        self.task_mgr.add(self._poll_update, "poll-upd")

    def _poll_update(self, task):
        r = self._upd
        if r is None: return task.cont
        self._upd = None; kind, data = r
        if kind == "newer":
            self._dialog("%s %s is available!\n%s" % (APP_TITLE, data["version"], data["notes"][:150]),
                         [("DOWNLOAD", lambda: self._download(data)), ("NOT NOW", self._close_dialog)])
        else:
            self._dialog(data, [("OK", self._close_dialog)])
        return task.done

    def _download(self, data):
        link = data["link"]
        if not link.lower().endswith(".exe"):
            webbrowser.open(data.get("page") or RELEASES_URL); self._close_dialog(); return
        if data.get("portable"):
            return self._download_portable(link)
        self._dialog("Downloading the update...", [])
        def work():
            try:
                dst = os.path.join(tempfile.gettempdir(), os.path.basename(link.split("?")[0]))
                req = urllib.request.Request(link, headers={"User-Agent": "EX-SPORTS-SFC27/" + APP_VERSION})
                with urllib.request.urlopen(req, timeout=60) as r, open(dst, "wb") as f: shutil.copyfileobj(r, f)
                self._upd = ("install", dst)
            except Exception as e: self._upd = ("dlerror", str(e)[:90])
        threading.Thread(target=work, daemon=True).start()
        self.task_mgr.add(self._poll_dl, "poll-dl")

    def _poll_dl(self, task):
        r = self._upd
        if r is None: return task.cont
        self._upd = None
        if r[0] == "install":
            try:
                import subprocess, shlex
                extra = shlex.split(os.environ.get("EXS_UPDATE_SETUP_ARGS", ""))   # test hook, e.g. /VERYSILENT
                subprocess.Popen([r[1]] + extra, env=clean_env(), cwd=tempfile.gettempdir(), close_fds=True,
                                 creationflags=0x00000008 | 0x00000200 if os.name == "nt" else 0)   # detached, outside _MEI
                self.userExit()
            except Exception as e: self._dialog("Could not start the installer:\n%s" % e, [("CLOSE", self._close_dialog)])
        else:
            self._dialog("Download failed.\n%s" % r[1], [("OPEN DOWNLOAD PAGE", lambda: webbrowser.open(RELEASES_URL)), ("CLOSE", self._close_dialog)])
        return task.done

    def _download_portable(self, link):
        exe = os.path.abspath(sys.executable); new = exe + ".new"
        self._dialog("Downloading the portable update...", [])
        def work():
            try:
                req = urllib.request.Request(link, headers={"User-Agent": "EX-SPORTS-SFC27/" + APP_VERSION})
                with urllib.request.urlopen(req, timeout=60) as r, open(new, "wb") as f: shutil.copyfileobj(r, f)
                with open(new, "rb") as f: ok = f.read(2) == b"MZ"
                if not ok or os.path.getsize(new) < 5_000_000:
                    os.remove(new); raise IOError("downloaded file is not a valid EX SPORTS executable")
                self._upd = ("swap", new)
            except Exception as e:
                try:
                    if os.path.exists(new): os.remove(new)
                except OSError: pass
                self._upd = ("dlerror", str(e)[:90])
        threading.Thread(target=work, daemon=True).start()
        self.task_mgr.add(self._poll_portable, "poll-dl")

    def _poll_portable(self, task):
        r = self._upd
        if r is None: return task.cont
        self._upd = None
        if r[0] == "swap":
            try: self._launch_swap_helper(os.path.abspath(sys.executable), r[1]); self.userExit()
            except Exception as e:
                log_error("portable update: %r" % e)
                self._dialog("Could not apply the update:\n%s" % str(e)[:90], [("OPEN DOWNLOAD PAGE", lambda: webbrowser.open(RELEASES_URL)), ("CLOSE", self._close_dialog)])
        else:
            self._dialog("Download failed.\n%s" % r[1], [("OPEN DOWNLOAD PAGE", lambda: webbrowser.open(RELEASES_URL)), ("CLOSE", self._close_dialog)])
        return task.done

    def _launch_swap_helper(self, exe, new):
        """Wait for this process (and the onefile bootloader parent) to exit, replace the exe, relaunch it with a clean env."""
        import subprocess
        pids = [os.getpid()]
        try: pids.append(os.getppid())
        except Exception: pass
        bat = os.path.join(tempfile.gettempdir(), "exsports_update_%d.bat" % os.getpid())
        lines = ["@echo off", "setlocal EnableDelayedExpansion", "set N=0"]
        for p in pids:
            lines += [":w%d" % p, 'tasklist /FI "PID eq %d" 2>NUL | find " %d " >NUL' % (p, p),
                      "if not errorlevel 1 (ping -n 2 127.0.0.1 >NUL & set /a N+=1 & if !N! LSS 120 goto w%d)" % p]
        lines += ["set T=0", ":swap", 'move /Y "%s" "%s" >NUL 2>&1' % (new, exe),
                  "if errorlevel 1 (ping -n 2 127.0.0.1 >NUL & set /a T+=1 & if !T! LSS 60 goto swap)",
                  'start "" "%s"' % exe, '(goto) 2>NUL & del "%~f0"']
        with open(bat, "w", encoding="mbcs" if os.name == "nt" else "utf-8") as f: f.write("\r\n".join(lines) + "\r\n")
        subprocess.Popen(["cmd.exe", "/c", bat], creationflags=0x00000008 | 0x00000200, close_fds=True, cwd=os.path.dirname(exe),
                         env=clean_env(), stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # ------------------------------------------------------------ release smoke test (works in the frozen exe)
    def _smoke(self, task):
        out = os.environ.get("EXS_SMOKE_OUT") or DATA
        lp = os.path.join(out, "smoke.log"); lf = open(lp, "w", encoding="utf-8")
        def L(*a):
            lf.write(" ".join(str(x) for x in a) + "\n"); lf.flush()
        import xs_net as N
        st = {"bot": None, "got": {}}
        g = self.game
        def menu(): self.show_menu(); L("version", APP_VERSION, "screen", self.screen, "title", APP_TITLE, EDITION, "menu", self.menu_labels)
        ar = self.arena; ast = {}
        def a_open():
            ar.show_hub(); L("ARENA opened: screen", self.screen, "(first visit -> PICK A TEAM)", "save", ar.path)
        def a_pick():
            ar.pick(1); d = ar.d
            L("picked", ar.club_tuple()[0], "screen", self.screen, "formation", d["formation"], "XI", len(d["xi"]), "bench", len(d["bench"]),
              "coins", d["coins"], "team rating", ar.team_rating(), "chem", ar.chemistry())
            L("XI", [(ar.card(i)["name"], ar.card(i)["pos"], ar.card(i)["rating"], ar.card(i)["tier"]) for i in d["xi"]])
        def a_squad():
            d = ar.d; ar.set_formation("4-3-3"); ar.set_kit("YELLOW"); ar.set_captain(d["xi"][9])
            before = (d["xi"][3], d["bench"][2]); ar.click(("xi", 3)); ar.click(("bench", 2))
            ar.cap_mode = True; ar.click(("xi", 10))
            L("squad: formation", d["formation"], "kit", d["kit"], "captain", ar.card(d["captain"])["name"], "swap xi3<->bench2",
              (d["xi"][3], d["bench"][2]) == (before[1], before[0]), "team rating", ar.team_rating(), "chem", ar.chemistry(), "screen", self.screen)
        def a_coins():
            ar.show_packs(); c0 = ar.d["coins"]; ar.show_add_coins(); L("ADD COINS dialog", ar.overlay is not None)
            for n in (1000, 10000, 100000): ar.add_coins(n)
            L("coins", c0, "->", ar.d["coins"]); ar._refresh_after_coins()
        def a_pack():
            c0 = ar.d["coins"]; cards = ar.open_and_show(2); ast["n"] = len(ar.d["cards"])
            L("GOLD PACK opened: screen", self.screen, "coins", c0, "->", ar.d["coins"], "cards", [(c["name"], c["pos"], c["rating"], c["tier"]) for c in cards])
            ar.open_pack(3); L("ELITE PACK", [(c["name"], c["rating"], c["tier"]) for c in ar.last_pack], "total cards", len(ar.d["cards"]))
        def a_change():
            n0, c0 = len(ar.d["cards"]), ar.d["coins"]; ar.show_pick(mode="change"); L("CHANGE TEAM screen", self.screen)
            ar.pick(3); L("changed to", ar.club_tuple()[0], "cards", n0, "->", len(ar.d["cards"]), "(kept)", "coins kept", ar.d["coins"] == c0,
                          "formation", ar.d["formation"])
            ar.show_hub(); L("hub", self.screen)
        def a_match():
            st = ar.play_match(autoplay=True); m = g.match
            L("ARENA match started", m is not None, "players", len(m.fps), "clubs", m.clubs[0][0], "vs", m.clubs[1][0], "kit", m.clubs[0][2],
              "opp rating", st["opp_rating"], "home XI", [f.name for f in m.fps if f.team == 0])
        def a_end():
            m = g.match; L("ARENA after play: clock", m.clock_text(), "score", m.score); c0 = ar.d["coins"]; m.end_match()
            L("ARENA END MATCH: reward", m.arena_coins, "coins", c0, "->", ar.d["coins"], "played", ar.d["played"]); m.quit()
            L("back to", self.screen, "save exists", os.path.exists(ar.path))
        rec = self.exrec; rst = {}
        def r_start():
            L("RECORDER F9:", rec.toggle(), "label", rec.sess and rec.sess["label"], "quality", rec.quality(), "ffmpeg", rec.ff)
        def r_diag(tag):
            ss = rec.sess
            if ss is None: L("RECORDER diag", tag, "no session", rec.last_error); return
            lg = ""
            try: lg = open(os.path.join(ss["dir"], "ffmpeg.log"), "rb").read().decode("utf-8", "replace")[-300:]
            except Exception: pass
            L("RECORDER diag", tag, "size", ss["size"], "t", round(rec.t(), 2), "frames", ss["n"], "proc", rec.proc and rec.proc.poll(),
              "segs", [(os.path.basename(x[0]), x[1], x[2]) for x in rec.segments()][-4:], "files", sorted(os.listdir(ss["dir"]))[-5:], "ffmpeg.log", repr(lg))
        def r_stop():
            r_diag("before stop")
            rst["kick"] = rec.toggle(); L("RECORDER F9 stop -> saving", rst["kick"]["path"])
        def r_moment():
            r_diag("before moment")
            rst["moment"] = rec.save_moment(); L("RECORDER F10 SAVE MOMENT -> saving", rst["moment"]["path"])
        def r_check():
            for k in ("kick", "moment"):
                r = rst.get(k) or {}; p = r.get("path")
                L("RECORDER clip", k, "ok", r.get("ok"), "exists", bool(p and os.path.exists(p)), "MB", round(os.path.getsize(p) / 1e6, 2) if p and os.path.exists(p) else None,
                  "path", p, "err", rec.last_error)
            self.show_recordings(); L("RECORDINGS screen", self.screen, "clips listed", len(rec.clips())); self.show_menu()
        def quick(): g.quick_match(autoplay=True); m = g.match; L("quick match", m is not None, "unlimited", m.unlimited(), "clubs", m.clubs[0][0], m.clubs[1][0], "home kit", m.clubs[0][2])
        def check1():
            m = g.match; L("after play: clock", m.clock_text(), "done", m.done, "state", m.state, "score", m.score)
        def pause(): self.show_pause(); L("pause menu", self.pause_ui is not None)
        def end():
            m = g.match; self.hide_pause(); m.end_match(); L("END MATCH: done", m.done, "result screen", m.result_ui is not None, "banner", m.banner_txt)
        def leave():
            g.match.quit(); L("left stadium: match", g.match, "screen", self.screen)
        def host():
            g.online.open(); g.online.host(""); L("hosting")
        def bot():
            s = g.online.sess; L("join code", s.code)
            b = N.Session("join", "SMOKEBOT", A.preset(3), upnp=False, stun=False); b.join(s.code, ("127.0.0.1", s.port))
            b.on("fb_start", lambda pid, m: st["got"].__setitem__("start", m)); b.on("fb", lambda pid, m: st["got"].__setitem__("snap", st["got"].get("snap", 0) + 1))
            st["bot"] = b
            def pump(t):
                if st["bot"] is None: return t.done
                st["bot"].poll(time.time(), None); return t.cont
            self.task_mgr.add(pump, "bot-pump")
        def online_match():
            s = g.online.sess; b = st["bot"]; L("host peers", [(p["name"], p.get("ping")) for p in s.peers.values()], "bot", b.state)
            g.online.start_match(False); m = g.match; L("online match", m is not None, "online", m.online is not None if m else None,
                                                       "humans", [(f.name, f.human) for f in m.fps if f.human is not None] if m else None)
        def online_check():
            m = g.match; L("bot got setup", "start" in st["got"], "snapshots", st["got"].get("snap", 0), "clock", m.clock_text())
            m.end_match(); L("host END MATCH: done", m.done); m.quit(); L("back to lobby", g.online.ui is not None)
        def done():
            if st["bot"] is not None: st["bot"].close(); st["bot"] = None
            g.online.leave(quiet=True); L("SMOKE OK"); lf.close(); self.userExit()
        steps = [(3.0, menu), (1.0, quick), (2.0, r_start), (float(os.environ.get("EXS_SMOKE_PLAY", "20")), check1), (0.5, r_stop),
                 (0.5, pause), (1.0, end), (2.0, leave),
                 (1.0, a_open), (1.5, a_pick), (1.5, a_squad), (1.0, a_coins), (1.0, a_pack), (3.0, a_change), (1.0, a_match),
                 (float(os.environ.get("EXS_SMOKE_PLAY", "20")), r_moment), (0.5, a_end), (8.0, r_check), (2.0, host), (8.0, bot), (6.0, online_match), (8.0, online_check), (2.0, done)]
        state = {"i": 0, "t": time.time() + steps[0][0], "intro": False}
        def run(t):
            try:
                if self.intro is not None:                  # v1.0.0.2: let the 6 s intro play first
                    state["t"] = time.time() + steps[0][0]; return t.cont
                if not state["intro"]:
                    state["intro"] = True
                    L("intro finished after %.2f s (skipped %s), screen %s" % (getattr(self, "intro_secs", -1), getattr(self, "intro_skipped", None), self.screen))
                if time.time() < state["t"]: return t.cont
                d, fn = steps[state["i"]]; fn(); state["i"] += 1
                if state["i"] >= len(steps): return t.done
                state["t"] = time.time() + steps[state["i"]][0]
            except Exception as e:
                L("SMOKE ERROR", "".join(traceback.format_exception(type(e), e, e.__traceback__))); log_error(e); lf.close(); self.userExit()
                return t.done
            return t.cont
        self.task_mgr.add(run, "smoke-run")
        return task.done


def main():
    try:
        App().run()
    except SystemExit: raise
    except Exception as e:
        log_error(e); raise


if __name__ == "__main__":
    main()
