"""Real-time pipeline:
scene -> [pre0] -> camera (roll / blur / kaleido / FOV stretch) -> [pre] -> feedback -> [mid] -> ASCII pass -> bloom
      -> post (+ text layer + invert/knock-out masks) -> screen.
All layout inputs are virtual-canvas units (see canvas.py); the engine converts them to real pixels with V.s.
"""
import json
import math

import cv2
import moderngl
import numpy as np
from PIL import Image

from . import shaders3 as SH
from .canvas import V
from .kt_core import make_sprite
from .paths import asset

PRESENT_F = """
#version 330
uniform sampler2D u_tex;
in vec2 uv; out vec4 fragColor;
void main(){ fragColor = vec4(texture(u_tex, uv).rgb, 1.0); }
"""

VIDEO_GAMMA = {"dance_skel": (0.7, 2.6), "dance_hood": (0.55, 3.8)}


class Engine:
    def __init__(self, ctx, width, height):
        self.ctx = ctx
        self.quad = ctx.buffer(np.array([-1, -1, 1, -1, -1, 1, 1, 1], "f4").tobytes())
        self.P = {}
        for name, frag in (("scene", SH.SCENE3), ("kal", SH.KAL3), ("fb", SH.FB), ("ascii", SH.ASCII), ("bright", SH.BRIGHT),
                           ("blur", SH.BLUR), ("post", SH.POST3), ("present", PRESENT_F)):
            self.P[name] = ctx.program(vertex_shader=SH.VERT, fragment_shader=frag)
        self.P["text"] = ctx.program(vertex_shader=SH.TEXT_V, fragment_shader=SH.TEXT_F)
        self.P["sprite"] = ctx.program(vertex_shader=SH.SPRITE_V, fragment_shader=SH.SPRITE_F)
        self.vao = {k: ctx.simple_vertex_array(p, self.quad, "pos") for k, p in self.P.items()}
        self._tex = []
        self._fbo = []
        self.W = self.H = 0
        self.alloc(width, height)
        # constant textures
        self.t_spec = ctx.texture((64, 1), 1, dtype="f4")
        self.t_spec.filter = (moderngl.LINEAR, moderngl.LINEAR)
        self.t_spec.repeat_x = False
        atl = np.asarray(Image.open(asset("atlas.png")).convert("RGBA"))
        self.t_atlas = ctx.texture((atl.shape[1], atl.shape[0]), 4, atl.tobytes())
        self.t_atlas.filter = (moderngl.LINEAR, moderngl.LINEAR)
        self.t_atlas.repeat_x = self.t_atlas.repeat_y = False
        self.atlas_size = (float(atl.shape[1]), float(atl.shape[0]))
        self.meta = json.load(open(asset("atlas.json")))
        gm = json.load(open(asset("glyph.json")))
        self.ramp_n, self.rain_n = gm["ramp_n"], gm["rain_n"]
        self.t_ramp = self._gray_tex(asset("glyph_ramp.png"))
        self.t_rain = self._gray_tex(asset("glyph_rain.png"))
        self.sprites = {}
        self.vid = {}

    # ------------------------------------------------------------------ render targets
    def _mk(self, w, h, comps=4, dtype="f2"):
        t = self.ctx.texture((w, h), comps, dtype=dtype)
        t.filter = (moderngl.LINEAR, moderngl.LINEAR)
        t.repeat_x = t.repeat_y = False
        self._tex.append(t)
        return t

    def _fb(self, tex):
        f = self.ctx.framebuffer([tex])
        self._fbo.append(f)
        return f

    def alloc(self, width, height):
        for f in self._fbo:
            f.release()
        for t in self._tex:
            t.release()
        self._tex, self._fbo = [], []
        self.W, self.H = int(width), int(height)
        V.setup(self.W, self.H)
        W, H = self.W, self.H
        self.t_scene, self.t_kal = self._mk(W, H), self._mk(W, H)
        self.t_fb = [self._mk(W, H), self._mk(W, H)]
        self.t_ascii = self._mk(W, H)
        self.t_text = self._mk(W, H)
        self.t_mask = self._mk(W, H)
        self.fb_i = 0
        self.f_scene, self.f_kal = self._fb(self.t_scene), self._fb(self.t_kal)
        self.f_fb = [self._fb(t) for t in self.t_fb]
        self.f_ascii, self.f_text, self.f_mask = self._fb(self.t_ascii), self._fb(self.t_text), self._fb(self.t_mask)
        self.bl = []
        for lv in range(4):
            w, h = max(2, W >> (lv + 1)), max(2, H >> (lv + 1))
            a, b = self._mk(w, h), self._mk(w, h)
            self.bl.append((w, h, a, b, self._fb(a), self._fb(b)))
        self.t_out = self._mk(W, H, 3, "f1")
        self.f_out = self._fb(self.t_out)
        self.clear_all()

    def _gray_tex(self, path):
        g = np.asarray(Image.open(path).convert("L"))
        t = self.ctx.texture((g.shape[1], g.shape[0]), 1, g.tobytes())
        t.filter = (moderngl.LINEAR, moderngl.LINEAR)
        t.repeat_x = t.repeat_y = False
        return t

    def clear_all(self):
        for f in self.f_fb + [self.f_scene, self.f_kal, self.f_out, self.f_text, self.f_ascii, self.f_mask]:
            f.use()
            f.clear(0, 0, 0, 1)

    def setu(self, name, **kw):
        p = self.P[name]
        for k, v in kw.items():
            if k in p:
                p[k].value = v

    # ------------------------------------------------------------------ sprites (virtual units in, pixels out)
    def sprite(self, text, fkey, size, color, grad=True):
        key = (text, fkey, int(size), color, grad)
        if key not in self.sprites:
            sp = make_sprite(text, fkey, int(size), color, outline=True, rs=1.0, shadow=False, grad=grad)
            img = sp.img[:, :, [2, 1, 0, 3]].copy()
            t = self.ctx.texture((img.shape[1], img.shape[0]), 4, img.tobytes())
            t.filter = (moderngl.LINEAR, moderngl.LINEAR)
            t.repeat_x = t.repeat_y = False
            self.sprites[key] = (t, img.shape[1], img.shape[0], sp)
        return self.sprites[key]

    def tex_from_rgba(self, key, img):
        if key not in self.sprites:
            t = self.ctx.texture((img.shape[1], img.shape[0]), 4, img.tobytes())
            t.filter = (moderngl.LINEAR, moderngl.LINEAR)
            t.repeat_x = t.repeat_y = False
            self.sprites[key] = (t, img.shape[1], img.shape[0], None)
        return self.sprites[key]

    def draw_sprite(self, fbo, key, cx, cy, scale=1.0, rot=0.0, alpha=1.0, split=0.0, tint=(1, 1, 1), sx=None):
        t, w, h, _ = key
        s = V.s
        fbo.use()
        ctx = self.ctx
        ctx.enable(moderngl.BLEND)
        ctx.blend_func = (moderngl.ONE, moderngl.ONE_MINUS_SRC_ALPHA)
        t.use(0)
        self.setu("text", u_res=(self.W, self.H), u_center=(cx * s, cy * s),
                  u_size=(w * scale * (1.0 if sx is None else sx) * s, h * scale * s), u_rot=rot,
                  u_alpha=alpha, u_split=split, u_tint=tint, u_tex=0)
        self.vao["text"].render(moderngl.TRIANGLE_STRIP)
        ctx.disable(moderngl.BLEND)

    def _sprite_call(self, fbo, tex, rect, asz, cx, cy, wpx, height, flip, rot, alpha, split, tint, ascii_, cell, dissolve, slice_,
                     time, jit, dsz, add):
        s = V.s
        ctx = self.ctx
        fbo.use()
        ctx.enable(moderngl.BLEND)
        ctx.blend_func = (moderngl.ONE, moderngl.ONE) if add else (moderngl.ONE, moderngl.ONE_MINUS_SRC_ALPHA)
        tex.use(0)
        self.t_ramp.use(1)
        cell_px = (max(cell[0] * s, 7.0), max(cell[1] * s, 12.0))      # keep glyphs legible on small screens
        self.setu("sprite", u_res=(self.W, self.H), u_center=(cx * s, cy * s), u_size=(-wpx * s if flip else wpx * s, height * s),
                  u_rot=rot, u_alpha=alpha, u_split=split, u_tint=tint, u_atlas=0, u_glyph=1, u_rect=rect, u_asz=asz,
                  u_ascii=ascii_, u_cell=cell_px, u_dissolve=dissolve, u_slice=slice_, u_time=time, u_jit=jit,
                  u_glyphN=float(self.ramp_n), u_dsz=dsz * s)
        self.vao["sprite"].render(moderngl.TRIANGLE_STRIP)
        ctx.disable(moderngl.BLEND)

    def draw_atlas(self, fbo, name, cx, cy, height, rot=0.0, alpha=1.0, tint=(1, 1, 1), ascii_=0.0, split=0.0, dissolve=0.0,
                   slice_=0.0, flip=False, add=False, cell=(12, 20), jit=0.4, time=0.0, dsz=10.0, width=None, sx=1.0):
        x, y, w, h = self.meta[name]
        wpx = (width if width is not None else height * w / h) * sx
        self._sprite_call(fbo, self.t_atlas, (x, y, w, h), self.atlas_size, cx, cy, wpx, height, flip, rot, alpha, split, tint,
                          ascii_, cell, dissolve, slice_, time, jit, dsz, add)

    # ------------------------------------------------------------------ video loops (uploaded once as a frame-grid atlas)
    def load_video(self, name, path, scale_h=640):
        cap = cv2.VideoCapture(path)
        frames = []
        while True:
            ok, f = cap.read()
            if not ok:
                break
            h, w = f.shape[:2]
            frames.append(cv2.resize(f, (int(w * scale_h / h), scale_h), interpolation=cv2.INTER_AREA))
        cap.release()
        n = len(frames)
        h, w = frames[0].shape[:2]
        cols = int(math.ceil(math.sqrt(n * h / float(w))))
        rows = int(math.ceil(n / float(cols)))
        gamma, gain = VIDEO_GAMMA.get(name, (0.7, 2.6))
        atlas = np.zeros((rows * h, cols * w, 4), np.uint8)
        for i, fr in enumerate(frames):
            f = fr.astype(np.float32) / 255.0
            lum = np.clip(f.max(axis=2, keepdims=True) ** gamma * gain, 0, 1)
            rgb = (f[:, :, ::-1] ** gamma) * lum
            tile = (np.clip(np.concatenate([rgb, lum], axis=2), 0, 1) * 255).astype(np.uint8)
            r, c = divmod(i, cols)
            atlas[r * h:(r + 1) * h, c * w:(c + 1) * w] = tile
        tex = self.ctx.texture((atlas.shape[1], atlas.shape[0]), 4, atlas.tobytes())
        tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
        tex.repeat_x = tex.repeat_y = False
        self.vid[name] = dict(tex=tex, w=w, h=h, cols=cols, n=n, asz=(float(atlas.shape[1]), float(atlas.shape[0])))

    def draw_video(self, fbo, name, idx, cx, cy, height, rot=0.0, alpha=1.0, tint=(1, 1, 1), ascii_=0.0, split=0.0, dissolve=0.0,
                   slice_=0.0, flip=False, add=False, cell=(12, 20), jit=0.4, time=0.0, dsz=10.0, gamma=None, gain=None, sx=1.0):
        v = self.vid[name]
        idx = int(idx) % v["n"]
        r, c = divmod(idx, v["cols"])
        wpx = height * v["w"] / v["h"] * sx
        self._sprite_call(fbo, v["tex"], (c * v["w"], r * v["h"], v["w"], v["h"]), v["asz"], cx, cy, wpx, height, flip, rot, alpha,
                          split, tint, ascii_, cell, dissolve, slice_, time, jit, dsz, add)

    # ------------------------------------------------------------------ one frame
    def render(self, S, hooks, to_screen=None):
        ctx = self.ctx
        s = V.s
        self.f_scene.use()
        self.t_spec.write(np.asarray(S["spec"], "f4").tobytes())
        self.t_spec.use(1)
        self.t_rain.use(2)
        self.t_atlas.use(3)
        pr = [self.meta[k] for k in ("palm1", "palm2", "palm3")]
        self.setu("scene", u_res=(self.W, self.H), u_spec=1, u_rain=2, u_atlas=3, u_rainN=float(self.rain_n),
                  u_palm0=tuple(pr[0]), u_palm1=tuple(pr[1]), u_palm2=tuple(pr[2]), **S["scene"])
        self.vao["scene"].render(moderngl.TRIANGLE_STRIP)
        if hooks.get("pre0"):
            hooks["pre0"](self, self.f_scene)
        self.f_kal.use()
        self.t_scene.use(0)
        self.setu("kal", u_res=(self.W, self.H), u_tex=0, **S["kal"])
        self.vao["kal"].render(moderngl.TRIANGLE_STRIP)
        if hooks.get("pre"):
            hooks["pre"](self, self.f_kal)
        cur = self.fb_i ^ 1
        self.f_fb[cur].use()
        self.t_kal.use(0)
        self.t_fb[self.fb_i].use(1)
        self.setu("fb", u_res=(self.W, self.H), u_new=0, u_prev=1, **S["fb"])
        self.vao["fb"].render(moderngl.TRIANGLE_STRIP)
        if hooks.get("mid"):
            hooks["mid"](self, self.f_fb[cur])
        comp = self.t_fb[cur]
        A = dict(S["ascii"])
        if A["u_amt"] > 0.002 or A.get("ring_on", False):
            A.pop("ring_on", None)
            A["u_cell"] = max(A["u_cell"] * s, 10.0)
            self.f_ascii.use()
            comp.use(0)
            self.t_ramp.use(1)
            self.setu("ascii", u_res=(self.W, self.H), u_src=0, u_glyph=1, u_glyphN=float(self.ramp_n), **A)
            self.vao["ascii"].render(moderngl.TRIANGLE_STRIP)
            comp = self.t_ascii
        self.f_text.use()
        self.f_text.clear(0, 0, 0, 0)
        if hooks.get("post"):
            hooks["post"](self, self.f_text)
        self.f_mask.use()
        self.f_mask.clear(0, 0, 0, 0)
        if hooks.get("mask"):
            hooks["mask"](self, self.f_mask)
        src = comp
        for lv, (w, h, a, b, fa, fb) in enumerate(self.bl):
            fa.use()
            src.use(0)
            if lv == 0:
                self.setu("bright", u_tex=0, u_thr=S["bloom_thr"])
                self.vao["bright"].render(moderngl.TRIANGLE_STRIP)
                a.use(0)
                fb.use()
                self.setu("blur", u_tex=0, u_dir=(1.0 / w, 0.0))
                self.vao["blur"].render(moderngl.TRIANGLE_STRIP)
                b.use(0)
                fa.use()
                self.setu("blur", u_tex=0, u_dir=(0.0, 1.0 / h))
                self.vao["blur"].render(moderngl.TRIANGLE_STRIP)
            else:
                fb.use()
                src.use(0)
                self.setu("blur", u_tex=0, u_dir=(1.0 / w, 0.0))
                self.vao["blur"].render(moderngl.TRIANGLE_STRIP)
                b.use(0)
                fa.use()
                self.setu("blur", u_tex=0, u_dir=(0.0, 1.0 / h))
                self.vao["blur"].render(moderngl.TRIANGLE_STRIP)
            src = a
        self.f_out.use()
        comp.use(0)
        for k in range(4):
            self.bl[k][2].use(1 + k)
        self.t_text.use(5)
        self.t_mask.use(6)
        self.setu("post", u_res=(self.W, self.H), u_comp=0, u_b1=1, u_b2=2, u_b3=3, u_b4=4, u_text=5, u_mask=6, u_s=s, **S["post"])
        self.vao["post"].render(moderngl.TRIANGLE_STRIP)
        self.fb_i = cur
        if to_screen is not None:
            self.present(*to_screen)

    def present(self, win_w, win_h):
        """stretch the internal render target over the whole window (internal aspect == window aspect, so no distortion)"""
        scr = self.ctx.screen
        scr.use()
        self.ctx.viewport = (0, 0, int(win_w), int(win_h))
        self.t_out.use(0)
        self.t_out.filter = (moderngl.LINEAR, moderngl.LINEAR)
        self.setu("present", u_tex=0)
        self.vao["present"].render(moderngl.TRIANGLE_STRIP)

    def read_frame(self):
        """RGB uint8 (top-down) of the last rendered frame, for screenshots"""
        raw = self.f_out.read(components=3)
        return np.frombuffer(raw, np.uint8).reshape(self.H, self.W, 3)[::-1].copy()
