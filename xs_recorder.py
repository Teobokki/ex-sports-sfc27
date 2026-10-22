"""EX SPORTS RECORDER (v1.0.0.2): records KICK OFF / ARENA / online matches to YouTube-ready MP4 files.

  * F9  start / stop recording           * F10 SAVE MOMENT: the last 30 seconds
  * MP4: H.264 High (yuv420p, constant frame rate, +faststart) + AAC 48 kHz stereo
  * QUALITY 720p30 (8 Mbps, default) / 1080p30 (12 Mbps) / 1080p60 (18 Mbps); optional small EX SPORTS watermark (off by default)
  * clips go straight to your Downloads folder (Windows known folder), e.g. "EX SPORTS SFC 27 - ARENA - 2026-10-22 22-19-05.mp4"
  * nothing is uploaded anywhere

How it works: during a match, frames are copied from the window (triggered copy to RAM) and piped to a bundled ffmpeg,
which encodes 2-second H.264 Matroska segments into a temp folder (a rolling buffer, 1 keyframe per second). A clip is the
segments that cover the wanted time, joined without re-encoding, plus an audio track mixed from the game's own sound
events (every game sound is one of our WAV files). The red REC indicator is hidden on every captured frame, so it never
appears in the video."""
import os, sys, time, json, shutil, threading, subprocess, queue, wave, glob
import numpy as np
from panda3d.core import Texture, GraphicsOutput, Filename
from direct.gui.DirectGui import DirectFrame, DGG
import xs_ui as U

QUALITY = {"720p30": (1280, 720, 30, 8), "1080p30": (1920, 1080, 30, 12), "1080p60": (1920, 1080, 60, 18)}
MOMENT_SECS = 30.0
SEG_SECS = 2
AUDIO_SR = 48000
NO_WINDOW = 0x08000000 if os.name == "nt" else 0


def downloads_dir():
    """the real Downloads folder (FOLDERID_Downloads via SHGetKnownFolderPath), else %USERPROFILE%\\Downloads"""
    if os.name == "nt":
        try:
            import ctypes, uuid
            from ctypes import wintypes
            class GUID(ctypes.Structure):
                _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD), ("Data3", wintypes.WORD), ("Data4", ctypes.c_ubyte * 8)]
            u = uuid.UUID("{374DE290-123F-4565-9164-39C4925E467B}"); g = GUID()
            g.Data1, g.Data2, g.Data3 = u.fields[0], u.fields[1], u.fields[2]
            for i, b in enumerate(u.bytes[8:]): g.Data4[i] = b
            p = ctypes.c_wchar_p()
            if ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(g), 0, None, ctypes.byref(p)) == 0:
                path = p.value; ctypes.windll.ole32.CoTaskMemFree(p)
                if path: return path
        except Exception:
            pass
    return os.path.join(os.environ.get("USERPROFILE") or os.path.expanduser("~"), "Downloads")


def clean_env():
    env = {k: v for k, v in os.environ.items() if not (k.upper().startswith("_PYI") or k.upper().startswith("_MEIPASS"))}
    env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
    return env


def ffmpeg_exe(base):
    for p in glob.glob(os.path.join(base, "ffmpeg", "ffmpeg*.exe")) + glob.glob(os.path.join(base, "ffmpeg", "ffmpeg")):
        return p
    try:
        import imageio_ffmpeg; return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return shutil.which("ffmpeg")


def _run(args, **kw):
    return subprocess.run(args, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=NO_WINDOW,
                          env=clean_env(), **kw)


class Recorder:
    def __init__(self, app):
        self.app = app; self.ff = ffmpeg_exe(app.BASE); self.proc = None; self.sess = None; self.recording = None
        self.events = []; self.wavs = {}; self.busy = 0; self.saved = []; self.last_error = None
        root = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        self.tmp_root = os.path.join(root, "EX SPORTS SFC 27", "recorder_tmp")
        shutil.rmtree(self.tmp_root, ignore_errors=True)                 # leftovers of a previous run
        self.ind = None; self._build_indicator()

    # ------------------------------------------------------------------ settings
    def quality(self):
        q = self.app.settings.get("rec_quality", "720p30"); return q if q in QUALITY else "720p30"

    def out_dir(self):
        d = downloads_dir(); os.makedirs(d, exist_ok=True); return d

    # ------------------------------------------------------------------ indicator (top-right, never in the video)
    def _build_indicator(self):
        a = self.app; o = self.ind = DirectFrame(parent=a.a2dTopRight, frameColor=(0, 0, 0, 0.55), frameSize=(-0.34, -0.03, -0.1, -0.03),
                                                   state=DGG.DISABLED)
        DirectFrame(parent=o, frameColor=(0.9, 0.05, 0.05, 1), frameSize=(-0.315, -0.285, -0.08, -0.05), state=DGG.DISABLED)
        self.ind_txt = U.text(o, "REC 0:00", (-0.155, -0.077), 0.032, fg=(1, 0.2, 0.2, 1), font=U.FONT_PLAIN)
        o.hide()

    # ------------------------------------------------------------------ session (one per match)
    def begin(self, label):
        """called when a match starts: start the rolling buffer encoder"""
        self.end()
        if not self.ff: self.last_error = "ffmpeg not found"; return False
        a = self.app; W, H, fps, mbps = QUALITY[self.quality()]
        d = os.path.join(self.tmp_root, "s%d" % int(time.time() * 1000)); os.makedirs(d, exist_ok=True)
        tex = Texture("exs-rec"); a.win.add_render_texture(tex, GraphicsOutput.RTM_triggered_copy_ram)
        self.sess = {"dir": d, "label": label, "tex": tex, "fps": fps, "W": W, "H": H, "mbps": mbps, "t0": None, "n": 0, "frame": None,
                     "fmt": None, "size": None, "pending": False, "last_cap": 0.0, "q": queue.Queue(maxsize=6), "writer": None,
                     "wm": bool(a.settings.get("rec_watermark", False))}
        self.events = []
        a.task_mgr.add(self._task, "exs-recorder", sort=45)
        return True

    def _start_ffmpeg(self, w, h, ncomp):
        s = self.sess; W, H, fps, mbps = s["W"], s["H"], s["fps"], s["mbps"]
        pix = "bgra" if ncomp == 4 else "bgr24"
        vf = "vflip,crop=%d:%d:0:%d,scale=%d:%d:force_original_aspect_ratio=decrease:flags=bicubic,pad=%d:%d:(ow-iw)/2:(oh-ih)/2,setsar=1,format=yuv420p" % (
            s["win"][0], s["win"][1], h - s["win"][1], W, H, W, H)
        args = [self.ff, "-hide_banner", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", pix, "-s", "%dx%d" % (w, h), "-framerate", str(fps), "-i", "-"]
        if s["wm"]:
            logo = os.path.join(self.app.BASE, "assets", "intro_logo.png")
            args += ["-i", logo, "-filter_complex", "[0:v]%s[b];[1:v]scale=-1:%d,format=rgba,colorchannelmixer=aa=0.8[l];[b][l]overlay=W-w-%d:H-h-%d,format=yuv420p[v]"
                     % (vf, H // 10, H // 30, H // 30), "-map", "[v]"]
        else:
            args += ["-vf", vf]
        args += ["-c:v", "libx264", "-preset", "veryfast", "-profile:v", "high", "-bf", "0", "-pix_fmt", "yuv420p", "-b:v", "%dM" % mbps, "-maxrate", "%dM" % mbps,
                 "-bufsize", "%dM" % (2 * mbps), "-g", str(fps), "-keyint_min", str(fps), "-sc_threshold", "0",
                 "-force_key_frames", "expr:gte(t,n_forced*1)", "-f", "segment", "-segment_time", str(SEG_SECS), "-segment_format", "matroska",
                 "-segment_list", os.path.join(s["dir"], "segs.csv"), "-segment_list_type", "csv", "-reset_timestamps", "1",
                 os.path.join(s["dir"], "seg_%05d.mkv")]
        self.proc = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=open(os.path.join(s["dir"], "ffmpeg.log"), "wb"),
                                     creationflags=NO_WINDOW, env=clean_env(), cwd=s["dir"])
        q = s["q"]; proc = self.proc
        def writer():
            while True:
                b = q.get()
                if b is None: break
                try: proc.stdin.write(b)
                except Exception: break
            try: proc.stdin.close()
            except Exception: pass
        s["writer"] = threading.Thread(target=writer, daemon=True); s["writer"].start()

    def _task(self, task):
        s = self.sess
        if s is None: return task.done
        now = time.time(); tex = s["tex"]
        if s["pending"] and tex.has_ram_image():                         # the frame copied at the end of the last render
            img = tex.get_ram_image(); w, h, nc = tex.get_x_size(), tex.get_y_size(), tex.get_num_components()
            if s["size"] is None:
                s["size"] = (w, h, nc); s["win"] = (min(w, self.app.win.get_x_size()), min(h, self.app.win.get_y_size()))
                s["win"] = (s["win"][0] // 2 * 2, s["win"][1] // 2 * 2)
                self._start_ffmpeg(w, h, nc); s["t0"] = now
            if (w, h, nc) == s["size"]: s["frame"] = img.get_data()
        s["pending"] = False
        if s["frame"] is not None and s["t0"] is not None:              # constant frame rate: one frame per slot (repeat if needed)
            due = int((now - s["t0"]) * s["fps"]) + 1
            if due - s["n"] > s["fps"]: s["n"] = due - s["fps"]            # after a long stall, don't flood the encoder
            while s["n"] < due:
                try: s["q"].put_nowait(s["frame"])
                except queue.Full: pass
                s["n"] += 1
        # capture this frame? keep up with the frame rate; while the REC indicator shows, skip every other frame so it stays visible
        need = (now - s["last_cap"]) >= (1.0 / s["fps"]) * 0.9
        alt = self.recording is not None and s.get("cap_prev", False)
        if need and not alt:
            self.app.win.trigger_copy(); s["pending"] = True; s["last_cap"] = now; s["cap_prev"] = True
            self.ind.hide()                                              # never in the video
        else:
            s["cap_prev"] = False
            if self.recording is not None: self.ind.show()
        if self.recording is not None:
            e = int(self.t() - self.recording); self.ind_txt.setText("REC %d:%02d" % (e // 60, e % 60))
        if int(now) % 2 == 0 and int(now) != s.get("pruned"): s["pruned"] = int(now); self._prune()
        return task.cont

    def t(self):
        """seconds on the video timeline (frame slot clock)"""
        s = self.sess
        if s is None or s["t0"] is None: return 0.0
        return s["n"] / float(s["fps"])

    def segments(self, s=None):
        s = s or self.sess; out = []
        if s is None: return out
        try:
            for line in open(os.path.join(s["dir"], "segs.csv"), encoding="utf-8"):
                p = line.strip().split(",")
                if len(p) >= 3: out.append((os.path.join(s["dir"], p[0]), float(p[1]), float(p[2])))
        except Exception: pass
        return out

    def _prune(self):
        keep_from = self.t() - MOMENT_SECS - 3 * SEG_SECS
        if self.recording is not None: keep_from = min(keep_from, self.recording - SEG_SECS)
        for p, a, b in self.segments():
            if b < keep_from and os.path.exists(p):
                try: os.remove(p)
                except OSError: pass

    def end(self):
        """called when a match ends: a running recording is saved, then the encoder stops"""
        s = self.sess
        if s is None: return
        if self.recording is not None: self.toggle()
        self.app.task_mgr.remove("exs-recorder"); self.ind.hide()
        try: self.app.win.clear_render_textures()
        except Exception: pass
        self.sess = None
        proc = self.proc
        def stop():
            try: s["q"].put(None, timeout=2)                              # close the encoder: it writes the last segment
            except Exception: pass
            if proc is not None:
                try: proc.wait(timeout=15)
                except Exception:
                    try: proc.kill()
                    except Exception: pass
            s["closed"] = True
            while self.busy: time.sleep(0.1)                              # let pending saves finish with these segments
            if not os.environ.get("EXS_REC_KEEP"): shutil.rmtree(s["dir"], ignore_errors=True)
        threading.Thread(target=stop, daemon=True).start(); self.proc = None

    # ------------------------------------------------------------------ audio events (the game's own sounds)
    def note_sound(self, name, vol):
        if self.sess is not None and self.sess["t0"] is not None: self.events.append((self.t(), name, float(vol)))

    def _wav(self, name):
        if name in self.wavs: return self.wavs[name]
        x = None
        try:
            with wave.open(os.path.join(self.app.BASE, "assets", "sfx", name + ".wav")) as r:
                sr, ch, sw = r.getframerate(), r.getnchannels(), r.getsampwidth(); raw = r.readframes(r.getnframes())
            a = np.frombuffer(raw, "<i2" if sw == 2 else np.uint8).astype(np.float32)
            a = a / 32768.0 if sw == 2 else (a - 128) / 128.0
            a = a.reshape(-1, ch).mean(axis=1)
            if sr != AUDIO_SR: a = np.interp(np.arange(0, a.size, sr / AUDIO_SR), np.arange(a.size), a).astype(np.float32)
            x = a
        except Exception: pass
        self.wavs[name] = x; return x

    def _mix(self, t0, dur, path):
        n = int(dur * AUDIO_SR) + 1; buf = np.zeros(n, np.float32)
        for (t, name, vol) in list(self.events):
            if t < t0 - 10 or t > t0 + dur: continue
            x = self._wav(name)
            if x is None: continue
            i = int((t - t0) * AUDIO_SR); a0 = max(0, -i); i = max(0, i); m = min(x.size - a0, n - i)
            if m > 0: buf[i:i + m] += x[a0:a0 + m] * vol
        buf = np.clip(buf, -1, 1); st = np.repeat((buf * 32767).astype("<i2")[:, None], 2, axis=1)
        with wave.open(path, "wb") as w:
            w.setnchannels(2); w.setsampwidth(2); w.setframerate(AUDIO_SR); w.writeframes(st.tobytes())

    # ------------------------------------------------------------------ F9 / F10
    def toggle(self):
        """F9: start / stop recording"""
        if self.sess is None or self.sess["t0"] is None: self.app.game.toast("EX SPORTS RECORDER works during matches."); return None
        if self.recording is None:
            self.recording = self.t(); self.ind.show(); self.app.game.toast("EX SPORTS RECORDER: recording (F9 to stop)", 1.8); return "started"
        a = self.recording; self.recording = None; self.ind.hide()
        return self._save(a, self.t(), "Recording")

    def save_moment(self):
        """F10: save the last 30 seconds"""
        if self.sess is None or self.sess["t0"] is None: self.app.game.toast("EX SPORTS RECORDER works during matches."); return None
        b = self.t(); return self._save(max(0.0, b - MOMENT_SECS), b, "Moment")

    def _save(self, a, b, what):
        s = self.sess; label = s["label"]; self.busy += 1
        name = "EX SPORTS SFC 27 - %s - %s.mp4" % (label, time.strftime("%Y-%m-%d %H-%M-%S"))
        out = os.path.join(self.out_dir(), name); k = 2
        while os.path.exists(out): out = os.path.join(self.out_dir(), name[:-4] + " (%d).mp4" % k); k += 1
        self.app.game.toast("EX SPORTS RECORDER: saving %s..." % what.lower(), 1.5)
        res = {"path": out, "ok": None}
        def work():
            try:
                deadline = time.time() + SEG_SECS * 2 + 3                   # wait for the segment holding the end to close
                while time.time() < deadline:
                    segs = self.segments(s)
                    if (segs and segs[-1][2] >= b - 0.05) or s.get("closed"): break
                    time.sleep(0.2)
                segs = [x for x in self.segments(s) if x[2] > a and x[1] < b + 0.01 and os.path.exists(x[0])]
                if not segs: raise RuntimeError("no video yet")
                start = max(a, segs[0][1]); start = segs[0][1] + int(start - segs[0][1])     # on a keyframe (1 per second)
                end = min(b, segs[-1][2]); dur = max(0.5, end - start)
                lst = os.path.join(s["dir"], "list_%d.txt" % int(time.time() * 1000)); wav = lst[:-4] + ".wav"
                with open(lst, "w", encoding="utf-8") as f:
                    for p, _a, _b in segs: f.write("file '%s'\n" % p.replace("\\", "/").replace("'", "'\\''"))
                self._mix(start, dur, wav)
                fps = s["fps"]                                               # exact constant frame rate: timestamps on a 1/fps grid
                retime = "setts=ts=N*1000:time_base=1/%d" % (fps * 1000)          # no B-frames, so packet n = frame n
                args = [self.ff, "-hide_banner", "-loglevel", "error", "-y", "-ss", "%.3f" % (start - segs[0][1]), "-f", "concat", "-safe", "0",
                        "-i", lst, "-i", wav, "-t", "%.3f" % dur, "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-bsf:v", retime,
                        "-video_track_timescale", str(fps * 1000), "-avoid_negative_ts", "make_zero", "-c:a", "aac", "-b:a", "192k",
                        "-ar", str(AUDIO_SR), "-ac", "2", "-movflags", "+faststart", "-metadata", "title=%s" % name[:-4],
                        "-metadata", "comment=Recorded with EX SPORTS RECORDER", out]
                if os.environ.get("EXS_REC_KEEP"): print("REC ARGS", args, flush=True)
                r = _run(args, timeout=120)
                for tmp in (lst, wav):
                    try: os.remove(tmp)
                    except OSError: pass
                if r.returncode != 0 or not os.path.exists(out): raise RuntimeError("ffmpeg %s: %s" % (r.returncode, r.stderr.decode("utf-8", "replace")[-200:].strip()))
                res["ok"] = True; self.saved.append(out)
            except Exception as e:
                res["ok"] = False; self.last_error = str(e)
            finally:
                self.busy -= 1
        threading.Thread(target=work, daemon=True).start()
        def done(task):
            if res["ok"] is None: return task.cont
            if res["ok"]: self.app.game.toast("Saved to Downloads: %s" % os.path.basename(out), 3.5)
            else: self.app.game.toast("EX SPORTS RECORDER: could not save (%s)" % (self.last_error or "?")[:60], 4.0)
            return task.done
        self.app.task_mgr.add(done, "exs-rec-saved-%d" % id(res))
        return res

    # ------------------------------------------------------------------ RECORDINGS
    def clips(self):
        d = downloads_dir()
        fs = glob.glob(os.path.join(d, "EX SPORTS SFC 27 - *.mp4"))
        return sorted(fs, key=lambda p: -os.path.getmtime(p))


def open_path(p):
    try:
        if os.name == "nt": os.startfile(p)
        else: subprocess.Popen(["xdg-open", p], env=clean_env())
    except Exception as e:
        print("open failed", e, flush=True)
