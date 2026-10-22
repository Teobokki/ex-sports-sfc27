"""Base on-foot character for EX SPORTS SFC 27: transform, walk cycle and arm posing. Bodies are built by xs_avatar."""
import math
from panda3d.core import NodePath


class Person:
    OUT = 1.0

    def __init__(self, game, who="player", x=0.0, y=0.0, h=0.0, ped=False):
        self.g = game; self.app = game.app; self.who = who
        self.x, self.y, self.h = x, y, h; self.vx = self.vy = 0.0
        self.phase = 0.0; self.knock = 0.0; self.in_car = None; self.hidden = False; self.ped = ped
        self.scrub_t = None; self.arm_pose = None; self.anim_lock = False; self.swim = False
        self.np = self.app.render.attach_new_node("person")
        self.build_model()
        self.np.set_pos(x, y, 0.0); self.np.set_h(h)

    def build_model(self):
        self.model = NodePath("empty"); self.model.reparent_to(self.np)
        self.legL = self.legR = self.armR = self.armL = self.foreR = self.foreL = NodePath()

    def walk_anim(self, dt, speed):
        k = min(1.0, speed / 5.5)
        self.phase += dt * (4.5 + speed * 1.35)
        a = math.sin(self.phase) * (22 + 14 * k) * min(1.0, speed / 1.2)
        if not self.legL.is_empty(): self.legL.set_p(a)
        if not self.legR.is_empty(): self.legR.set_p(-a)
        self.model.set_z(abs(math.sin(self.phase)) * 0.035 * min(1.0, speed / 1.5)); self.model.set_p(-k * 6)
        self.model.set_r(math.sin(self.phase) * 1.5 * min(1.0, speed / 2))
        self.swing_arms(a, k, speed)

    def set_arms(self, ar, al, fr=None, fl=None):
        if self.armR.is_empty(): return
        o = self.OUT
        self.armR.set_hpr(0, ar[0], o * ar[1]); self.armL.set_hpr(0, al[0], -o * al[1])
        if not self.foreR.is_empty():
            fr = fr or (0, 0); fl = fl or (0, 0)
            self.foreR.set_hpr(0, fr[0], o * fr[1]); self.foreL.set_hpr(0, fl[0], -o * fl[1])

    def set_grip(self, r, l=False):
        for sd, on in (("R", r), ("L", l)):
            op, cl = getattr(self, "hand_np", {}).get(sd, (NodePath(), NodePath()))
            if op.is_empty() or cl.is_empty(): continue
            if on: op.hide(); cl.show()
            else: op.show(); cl.hide()

    def swing_arms(self, a, k, speed):
        if self.armR.is_empty(): return
        mv = min(1.0, speed / 1.2); sw = a * (0.85 + 0.35 * k); base = -8.0 * k * mv
        breathe = 0.0 if mv > 0.05 else math.sin(self.phase * 0.35) * 1.2
        pr, pl = base + sw + breathe, base - sw + breathe
        er = -10 - 0.45 * max(0.0, -pr) - 70 * k * mv; el = -10 - 0.45 * max(0.0, -pl) - 70 * k * mv
        self.set_arms((pr, 3.0 + 3.0 * k), (pl, 3.0 + 3.0 * k), (er, 0), (el, 0))

    def sync(self, z=0.0):
        self.np.set_pos(self.x, self.y, z + 0.035); self.np.set_h(self.h)

    def destroy(self):
        self.np.remove_node()
