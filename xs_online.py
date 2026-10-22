"""EX SPORTS SFC 27 ONLINE: host / join with an SFC27-XXXX-XXXX code (xs_net: STUN + UPnP + outbound-first hole punching,
signed packets, optional password, LAN list), then the host starts a match for everyone (AI fills the empty spots)."""
import time
from direct.gui.DirectGui import DirectFrame, DirectEntry, DGG
from panda3d.core import TextNode
import xs_ui as U
import xs_net as N
import xs_avatar as A

Y = U.PINK; CY_ = U.CYAN; RED = (1, 0.35, 0.3, 1)


class Online:
    def __init__(self, game):
        self.g = game; self.app = game.app; self.sess = None; self.ui = None; self.view = "main"; self.lan = None
        self.ai_friends = []; self.fb_seq = 0; self._fb_t = 0.0; self._fb_last = {}; self.labels = []; self._sig = None; self._t = 0.0

    @property
    def profile(self):
        return self.g.profile

    # ------------------------------------------------------------ session control
    def host(self, password=""):
        self.leave(quiet=True)
        self.sess = N.Session("host", self.profile["name"], self.profile, password=password)
        self._handlers(); self.g.toast("Opening an online session...", 2.5)

    def join(self, code, password="", addr=None):
        if N.parse_code(code) is None:
            self.g.toast("That code looks wrong - it should look like SFC27-XXXX-XXXX", 3.0); return False
        self.leave(quiet=True)
        self.sess = N.Session("join", self.profile["name"], self.profile, password=password)
        self.sess.join(code, addr); self._handlers(); return True

    def _handlers(self):
        s = self.sess
        s.on("fbi", self._on_fb_input); s.on("fb_start", self._on_fb_start); s.on("fb", self._on_fb_snap)
        s.on("fb_end", self._on_fb_end); s.on("fb_leave", self._on_fb_leave)

    def leave(self, quiet=False):
        if self.sess is not None:
            self.sess.close(); self.sess = None
            if not quiet: self.g.toast("Left the online session", 2.0)
        m = getattr(self.g, "match", None)
        if m is not None and m.mode == "view": m.quit()
        self.refresh()

    def kick(self, pid):
        if self.sess and self.sess.role == "host": self.sess.kick(pid); self.refresh()

    def update(self, dt):
        s = self.sess
        if s is None: return
        s.poll(time.time(), None)
        for ev, data in s.events[:]:
            if ev in ("kicked", "ended"): self.g.toast(s.status, 3.0)
        s.events.clear()
        if s.state in ("ended", "error") and getattr(self.g, "match", None) is not None and self.g.match.mode == "view":
            self.g.match.quit()
        # refresh the lobby when something visible changes
        self._t += dt
        if self.ui is not None and self._t > 0.5:
            self._t = 0.0
            sig = (s.state, s.status, s.code, tuple(sorted(s.peers)) if s.role == "host" else len(getattr(s, "roster", [])),
                   s.reply_code() is not None if s.role == "join" else 0, len(self.lan.sessions()) if self.lan else 0)
            if sig != self._sig: self._sig = sig; self.refresh()

    # ------------------------------------------------------------ match glue (same protocol as SHINE ONLINE)
    def start_match(self, versus=False):
        g = self.g; s = self.sess
        if s is not None and s.role == "join":
            g.toast("The host starts online matches - you'll be pulled in automatically", 3.0); return
        self.close()
        st = g.settings
        g.start_match(home_club=st["home"], away_club=st["away"], minutes_real=float(st["duration"]),
                      online=self if (s is not None and s.peers) else None, versus=versus, kits=[st.get("home_kit"), None])
        m = g.match
        if m is not None and m.online is not None:
            for f in m.fps:
                if isinstance(f.human, int):
                    p = s.peers.get(f.human)
                    if p:
                        setup = {"slots": m.slots(), "clubs": [list(c) for c in m.clubs], "secs": m.secs, "you": f.human}
                        for _ in range(3): s.send(p["addr"], {"t": "fb_start", "setup": setup})

    def fb_tick(self, m, dt):
        self._fb_t -= dt
        if self._fb_t <= 0 and self.sess is not None:
            self._fb_t = 1.0 / 15.0; self.sess.broadcast({"t": "fb", "s": m.snapshot()})

    def fb_leave(self):
        s = self.sess
        if s is not None and s.role == "join":
            for _ in range(3): s.to_host({"t": "fb_leave"})

    def _on_fb_leave(self, pid, msg):
        m = getattr(self.g, "match", None)
        if m is None or m.mode != "sim": return
        for f in m.fps:
            if f.human == pid:
                f.human = None; f.inp = {"mv": (0, 0), "sp": False}; f.acts = []; m.banner("%s LEFT - AI TAKES OVER" % f.name, 2.0)

    def fb_end(self, m):
        if self.sess is not None:
            for _ in range(3): self.sess.broadcast({"t": "fb_end"})

    def _on_fb_input(self, pid, msg):
        m = getattr(self.g, "match", None)
        if m is None or m.mode != "sim": return
        for f in m.fps:
            if f.human == pid:
                mv = msg.get("mv") or [0, 0]
                try: f.inp = {"mv": (max(-1, min(1, float(mv[0]))), max(-1, min(1, float(mv[1])))), "sp": bool(msg.get("sp"))}
                except Exception: pass
                a = msg.get("a")
                if a and isinstance(a, list) and len(a) == 2 and a[1] in ("pass", "shoot", "tackle"):
                    if self._fb_last.get(pid, -1) < a[0]: self._fb_last[pid] = a[0]; f.acts.append(a[1])

    def _on_fb_start(self, pid, msg):
        g = self.g
        if getattr(g, "match", None) is not None: return
        self.close(); g.start_match_view(msg.get("setup") or {})

    def _on_fb_snap(self, pid, msg):
        m = getattr(self.g, "match", None)
        if m is not None and m.mode == "view": m.apply_snapshot(msg.get("s") or {})

    def _on_fb_end(self, pid, msg):
        m = getattr(self.g, "match", None)
        if m is not None and m.mode == "view" and not m.done: m.quit()

    def fb_input(self, mv=None, sp=None, act=None):
        s = self.sess
        if s is None: return
        now = time.time()
        if mv is not None: self._mv = (mv, sp)
        if not hasattr(self, "_mv"): self._mv = ((0, 0), False)
        if act is not None:
            self.fb_seq += 1; self._act = [self.fb_seq, act]
            for _ in range(2): s.to_host({"t": "fbi", "mv": list(self._mv[0]), "sp": bool(self._mv[1]), "a": self._act})
            return
        if now - getattr(self, "_fbi_t", 0) > 0.05:
            self._fbi_t = now
            s.to_host({"t": "fbi", "mv": [round(v, 2) for v in self._mv[0]], "sp": bool(self._mv[1]), "a": getattr(self, "_act", None)})

    # ------------------------------------------------------------ UI
    def open(self, view="main"):
        self.view = view; self.refresh(force=True)

    def close(self):
        if self.lan is not None: self.lan.close(); self.lan = None
        if self.ui is not None:
            if self.g.overlay is self.ui: self.g.overlay = None
            self.ui.destroy(); self.ui = None

    def refresh(self, force=False):
        if self.ui is None and not force: return
        g = self.g
        if self.ui is not None:
            if g.overlay is self.ui: g.overlay = None
            self.ui.destroy()
        self.labels = []
        o = self.ui = DirectFrame(parent=self.app.aspect2d, frameColor=(0, 0, 0, 0.45), frameSize=(-4, 4, -2, 2), state=DGG.NORMAL)
        g.overlay = o
        getattr(self, "view_" + self.view, self.view_main)(o)

    def goto(self, v): self.view = v; self.refresh()

    def _hdr(self, o, sub):
        U.panel(o, -1.05, 1.05, -0.8, 0.8, edge=Y)
        U.text(o, "SFC 27 ONLINE", (0, 0.69), 0.07, fg=Y)
        U.text(o, sub, (0, 0.63), 0.03, fg=(0.85, 0.88, 0.95, 1), font=U.FONT_PLAIN)

    def _btn(self, o, lbl, pos, fn, w=0.28, edge=Y, sc=0.034, h=0.045, hint=None):
        self.labels.append(lbl)
        return U.button(o, lbl, pos, fn, w=w, h=h, scale=sc, edge=edge, hint=hint)

    def view_main(self, o):
        s = self.sess
        self._hdr(o, "Play with friends over the internet - no account, no server, just a code")
        U.text(o, "YOU:  %s" % self.profile["name"], (0, 0.52), 0.036, font=U.FONT_PLAIN)
        y = 0.4
        if s is None:
            self._btn(o, "HOST A SESSION", (-0.36, y), lambda: self.goto("host"), edge=CY_)
            self._btn(o, "JOIN WITH A CODE", (0.36, y), lambda: self.goto("join"), edge=CY_)
            U.text(o, "Change your name and look under TEAMS.", (0, 0.25), 0.028, fg=(0.8, 0.85, 1, 1), font=U.FONT_PLAIN)
        else:
            self._session_box(o, y)
        if s is not None and s.role == "host":
            d = self.g.settings["duration"]
            U.text(o, "Match: %s vs %s  -  %s  (change in TEAMS / SETTINGS; your choice applies to everyone)" % (
                self.g.club_name(self.g.settings["home"]), self.g.club_name(self.g.settings["away"]), "UNLIMITED" if not d else "%d MIN" % d),
                (0, -0.37), 0.024, fg=(0.85, 0.9, 1, 1), font=U.FONT_PLAIN)
            self._btn(o, "ALL OF US VS AI", (-0.36, -0.47), lambda: self.start_match(False), edge=(0.3, 1.0, 0.45, 1))
            self._btn(o, "SPLIT TEAMS", (0.36, -0.47), lambda: self.start_match(True), edge=(0.3, 1.0, 0.45, 1))
        if s is not None:
            self._btn(o, "LEAVE SESSION" if s.role == "join" else "CLOSE SESSION", (-0.36, -0.64), self.leave, edge=RED)
        self._btn(o, "BACK", (0.36 if s is not None else 0, -0.64), self.back, hint="Esc")

    def back(self):
        self.close(); self.g.app.show_menu()

    def _session_box(self, o, y):
        s = self.sess
        if s.role == "host":
            U.text(o, "JOIN CODE:  %s" % (s.code or "finding your internet address..."), (0, y), 0.05, fg=Y)
            U.text(o, "%s   -   UDP port %d%s" % (s.via or s.status, s.port, "   -   password set" if s.password else ""), (0, y - 0.06), 0.026,
                   fg=(0.8, 0.85, 1, 1), font=U.FONT_PLAIN)
            rows = [(0, s.name + " (HOST, YOU)", 0)] + [(pid, p["name"], p.get("ping")) for pid, p in s.peers.items()]
            for k, (pid, nm, ping) in enumerate(rows[:7]):
                yy = y - 0.14 - k * 0.05
                U.text(o, "%s   %s" % (nm, ("%d ms" % ping) if ping is not None else "--"), (-0.3, yy), 0.03, align=TextNode.A_left, font=U.FONT_PLAIN)
                if pid: self._btn(o, "KICK", (0.55, yy + 0.012), lambda pid=pid: self.kick(pid), w=0.07, h=0.025, sc=0.024, edge=RED)
            self._btn(o, "LET A FRIEND IN (REPLY CODE)", (0, -0.27), lambda: self.goto("letin"), w=0.3, h=0.03, sc=0.026, edge=CY_)
        else:
            U.text(o, "SESSION  %s" % (s.code or ""), (0, y), 0.045, fg=Y)
            U.text(o, s.status + (("   -   PING %d ms" % s.ping_ms) if s.ping_ms is not None else ""), (0, y - 0.06), 0.027,
                   fg=(0.8, 0.85, 1, 1), font=U.FONT_PLAIN, wrap=60)
            if s.state == "joining":
                rc = s.reply_code()
                U.text(o, "YOUR REPLY CODE:  %s" % (rc or "(finding your address...)"), (0, y - 0.14), 0.034, fg=CY_)
                U.text(o, "Not connected after a few seconds? Send this to the host - they type it into LET A FRIEND IN.",
                       (0, y - 0.19), 0.024, fg=(0.85, 0.9, 1, 1), font=U.FONT_PLAIN)
                U.text(o, "Last resort only: " + s.forward_hint().lower() + ".", (0, y - 0.23), 0.022, fg=(1, 0.6, 0.5, 1), font=U.FONT_PLAIN)
            else:
                for k, e in enumerate(getattr(s, "roster", [])[:7]):
                    U.text(o, "%s%s   %s" % (e.get("name"), " (HOST)" if e.get("host") else (" (YOU)" if e.get("id") == s.my_id else ""),
                                            ("%d ms" % e["ping"]) if e.get("ping") is not None else "--"), (-0.3, y - 0.14 - k * 0.05), 0.03,
                           align=TextNode.A_left, font=U.FONT_PLAIN)
                U.text(o, "Waiting for the host to start a match...", (0, -0.4), 0.028, fg=CY_, font=U.FONT_PLAIN)

    def _entry(self, o, txt, pos, width=17, scale=0.05, obscured=0, focus=0):
        return DirectEntry(parent=o, initialText=txt, width=width, numLines=1, scale=scale, pos=(pos[0], 0, pos[1]), frameColor=(0.06, 0.08, 0.18, 1),
                           text_fg=(1, 1, 1, 1), entryFont=U.FONT_PLAIN, obscured=obscured, focus=focus)

    def view_host(self, o):
        self._hdr(o, "HOST: friends join with the code you get - share it any way you like")
        U.text(o, "Optional password (friends type it too):", (0, 0.42), 0.032, font=U.FONT_PLAIN)
        pw = self._entry(o, "", (-0.32, 0.32), 14, 0.045, obscured=1); o.ent = pw
        U.text(o, "Your game asks public STUN servers for your internet address and your router (UPnP) to open a port,\n"
                  "then packs both into an SFC27-XXXX-XXXX code. Friends on the same Wi-Fi see you under LAN SESSIONS.", (0, 0.14), 0.026,
               fg=(0.8, 0.85, 1, 1), font=U.FONT_PLAIN)
        self._btn(o, "START HOSTING", (0, -0.08), lambda: (self.host(pw.get().strip()), self.goto("main")), edge=CY_)
        self._btn(o, "BACK", (0, -0.64), lambda: self.goto("main"))

    def view_join(self, o):
        self._hdr(o, "JOIN: type the code your friend sent you")
        U.text(o, "Code:", (-0.62, 0.43), 0.036, align=TextNode.A_left, font=U.FONT_PLAIN)
        ce = self._entry(o, "SFC27-", (-0.45, 0.43), focus=1); o.ent = ce
        U.text(o, "Password:", (-0.62, 0.31), 0.032, align=TextNode.A_left, font=U.FONT_PLAIN)
        pe = self._entry(o, "", (-0.4, 0.31), 14, 0.04, obscured=1)
        def go(addr=None, code=None):
            if self.join(code or ce.get().strip(), pe.get().strip(), addr): self.goto("main")
        self._btn(o, "JOIN", (0, 0.19), go, edge=CY_)
        U.text(o, "LAN SESSIONS (same Wi-Fi):", (0, 0.05), 0.03, fg=CY_, font=U.FONT_PLAIN)
        if self.lan is None: self.lan = N.LanBrowser()
        ss = self.lan.sessions() if self.lan else []
        if not ss: U.text(o, "none found yet - REFRESH in a moment", (0, -0.02), 0.026, fg=(0.7, 0.7, 0.8, 1), font=U.FONT_PLAIN)
        for k, e in enumerate(ss[:4]):
            yy = -0.03 - k * 0.075
            U.text(o, "%s   %d player%s%s" % (e.get("name"), e.get("n", 1), "" if e.get("n", 1) == 1 else "s", "   (password)" if e.get("pw") else ""),
                   (-0.5, yy - 0.01), 0.03, align=TextNode.A_left, font=U.FONT_PLAIN)
            self._btn(o, "JOIN", (0.5, yy), lambda e=e: go(tuple(e["lan_addr"]), e["code"]), w=0.08, h=0.03, sc=0.026, edge=CY_)
        self._btn(o, "REFRESH", (0, -0.42), lambda: self.goto("join"), w=0.12, h=0.03, sc=0.026)
        self._btn(o, "BACK", (0, -0.64), lambda: self.goto("main"))

    def view_letin(self, o):
        self._hdr(o, "LET A FRIEND IN: type the REPLY CODE on your friend's screen - your game calls them, so it gets through")
        ce = self._entry(o, "SFC27-", (-0.45, 0.3), focus=1); o.ent = ce
        def go():
            if self.sess and self.sess.let_in(ce.get().strip()): self.g.toast("Calling your friend for 90 s...", 3.0); self.goto("main")
            else: self.g.toast("That reply code looks wrong", 2.5)
        self._btn(o, "LET THEM IN", (0, 0.15), go, edge=CY_)
        self._btn(o, "BACK", (0, -0.64), lambda: self.goto("main"))

    def destroy(self):
        self.close(); self.leave(quiet=True)
