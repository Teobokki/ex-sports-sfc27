import os, traceback
from panda3d.core import Filename
OUT = "/tmp/exs_store"; os.makedirs(OUT, exist_ok=True)
def shot(n): app.graphicsEngine.render_frame(); app.graphicsEngine.render_frame(); app.win.save_screenshot(Filename.from_os_specific(os.path.join(OUT, n + ".png"))); print("SHOT", n, flush=True)
seq = [(2.5, lambda: shot("title")), (0.3, lambda: app.show_menu()), (1.0, lambda: shot("menu")),
       (0.3, lambda: (app.clear_screen(), app.game.quick_match(autoplay=True))), (12.0, lambda: shot("match1")), (9.0, lambda: shot("match2")), (9.0, lambda: shot("match3")),
       (0.3, lambda: app.game.match.end_match()), (1.0, lambda: shot("result")), (0.3, lambda: app.game.match.quit()),
       (0.3, lambda: app.show_teams()), (0.6, lambda: shot("teams")),
       (0.3, lambda: (app.clear_screen(), app.game.online.open(), app.game.online.host(""))), (5.0, lambda: shot("online")), (0.3, lambda: app.userExit())]
st = {"i": 0, "t": 0.0}
def run(task):
    try:
        st["t"] += globalClock.get_dt()
        if st["i"] >= len(seq): return task.done
        if st["t"] >= seq[st["i"]][0]: st["t"] = 0; f = seq[st["i"]][1]; st["i"] += 1; f()
    except Exception: print("TESTERR", traceback.format_exc(), flush=True); st["i"] += 1
    return task.cont
app.task_mgr.add(run, "shots")
