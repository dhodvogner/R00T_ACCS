"""Core helpers for the kinetic-typography renderer: easing, fonts, sprites, compositing."""
import math
from functools import lru_cache

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .paths import load_font

FPS = 30
FD = r"C:\Windows\Fonts"
FONTS = dict(
    impact=FD + r"\impact.ttf",
    georgia_i=FD + r"\georgiai.ttf",
    georgia_bi=FD + r"\georgiaz.ttf",
    mono=FD + r"\consolab.ttf",
    comic=FD + r"\comicbd.ttf",
    sym=FD + r"\seguisym.ttf",
    sans=FD + r"\segoeuib.ttf",
)


def hexbgr(h):
    h = h.lstrip("#")
    return (int(h[4:6], 16), int(h[2:4], 16), int(h[0:2], 16))


def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def lerp(a, b, t):
    return a + (b - a) * t


def ease_out_cubic(t):
    t = clamp(t)
    return 1 - (1 - t) ** 3


def ease_in_cubic(t):
    t = clamp(t)
    return t ** 3


def ease_in_out(t):
    t = clamp(t)
    return t * t * (3 - 2 * t)


def ease_out_quint(t):
    t = clamp(t)
    return 1 - (1 - t) ** 5


def ease_out_back(t, c=1.70158):
    t = clamp(t)
    return 1 + (c + 1) * (t - 1) ** 3 + c * (t - 1) ** 2


def ease_out_bounce(t):
    t = clamp(t)
    n1, d1 = 7.5625, 2.75
    if t < 1 / d1:
        return n1 * t * t
    if t < 2 / d1:
        t -= 1.5 / d1
        return n1 * t * t + 0.75
    if t < 2.5 / d1:
        t -= 2.25 / d1
        return n1 * t * t + 0.9375
    t -= 2.625 / d1
    return n1 * t * t + 0.984375


@lru_cache(maxsize=None)
def pil_font(key, size):
    return load_font(FONTS[key], int(size))


@lru_cache(maxsize=None)
def metrics(key, size, text):
    """(width, cap_height) at integer pixel size."""
    f = pil_font(key, round(size))
    bb = f.getbbox("H", anchor="ls")
    return f.getlength(text), -bb[1]


class Spr:
    __slots__ = ("img", "px", "py", "tw", "cap", "rs")


@lru_cache(maxsize=6000)
def make_sprite(text, fkey, size, color, outline=True, rs=1.15, grad=True, shadow=True):
    """Premultiplied BGRA sprite of one text run, with outline + soft shadow baked in."""
    S = max(8, int(round(size * rs)))
    f = pil_font(fkey, S)
    tw = f.getlength(text)
    asc, desc = f.getmetrics()
    cap = -f.getbbox("H", anchor="ls")[1]
    pad = int(S * 0.30) + 8
    w = int(math.ceil(tw)) + 2 * pad
    h = asc + desc + 2 * pad
    org = (pad, pad + asc)
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).text(org, text, font=f, fill=255, anchor="ls")
    fa = np.asarray(m, dtype=np.float32) / 255.0
    sw = max(2, int(S * 0.035))
    ms = Image.new("L", (w, h), 0)
    ImageDraw.Draw(ms).text(org, text, font=f, fill=255, anchor="ls", stroke_width=sw, stroke_fill=255)
    sa = np.asarray(ms, dtype=np.float32) / 255.0

    rgb = np.zeros((h, w, 3), np.float32)
    a = np.zeros((h, w), np.float32)
    if shadow:
        sh = cv2.GaussianBlur(sa, (0, 0), S * 0.05)
        sh = cv2.warpAffine(sh, np.float32([[1, 0, 0], [0, 1, S * 0.045]]), (w, h)) * 0.8
        a = sh
    if outline:
        dark = np.array([34, 12, 22], np.float32) / 255.0
        a2 = sa * 0.94
        rgb = dark * a2[..., None] + rgb * (1 - a2[..., None])
        a = a2 + a * (1 - a2)
    col = np.array(color, np.float32) / 255.0
    if grad:
        top = col + (1 - col) * 0.42
        g = np.clip((np.arange(h, dtype=np.float32) - (pad + asc - cap)) / max(cap, 1), 0, 1)[:, None, None]
        fc = top * (1 - g) + col * g
    else:
        fc = col
    rgb = fc * fa[..., None] + rgb * (1 - fa[..., None])
    a = fa + a * (1 - fa)
    sp = Spr()
    sp.img = np.dstack([rgb * 255.0, a * 255.0]).clip(0, 255).astype(np.uint8)
    sp.px = pad + tw / 2.0
    sp.py = pad + asc - cap / 2.0
    sp.tw = tw
    sp.cap = cap
    sp.rs = rs
    return sp


def blit(dst, spr, cx, cy, sx=1.0, sy=1.0, rot=0.0, alpha=1.0, scale=1.0, mode="over", gain=1.0):
    """Draw premultiplied sprite with pivot (text centre) at (cx, cy)."""
    if alpha <= 0.003 or sx == 0 or sy == 0:
        return
    k = 1.0 / spr.rs
    c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    l00, l01 = c * sx * k, -s * sy * k
    l10, l11 = s * sx * k, c * sy * k
    tx = cx - (l00 * spr.px + l01 * spr.py)
    ty = cy - (l10 * spr.px + l11 * spr.py)
    M = np.float32([[l00, l01, tx], [l10, l11, ty]]) * scale
    h, w = spr.img.shape[:2]
    xs = [0, w, w, 0]
    ys = [0, 0, h, h]
    px_ = [M[0, 0] * x + M[0, 1] * y + M[0, 2] for x, y in zip(xs, ys)]
    py_ = [M[1, 0] * x + M[1, 1] * y + M[1, 2] for x, y in zip(xs, ys)]
    DH, DW = dst.shape[:2]
    x0 = max(int(math.floor(min(px_))), 0)
    y0 = max(int(math.floor(min(py_))), 0)
    x1 = min(int(math.ceil(max(px_))), DW)
    y1 = min(int(math.ceil(max(py_))), DH)
    if x1 <= x0 or y1 <= y0:
        return
    M[0, 2] -= x0
    M[1, 2] -= y0
    wp = cv2.warpAffine(spr.img, M, (x1 - x0, y1 - y0), flags=cv2.INTER_LINEAR,
                        borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
    roi = dst[y0:y1, x0:x1]
    if dst.dtype == np.uint8:
        p = wp[..., :3].astype(np.float32) * alpha
        if mode == "over":
            a = wp[..., 3:4].astype(np.float32) * (alpha / 255.0)
            out = roi.astype(np.float32) * (1.0 - a) + p
        else:
            out = roi.astype(np.float32) + p * gain
        roi[:] = np.clip(out, 0, 255).astype(np.uint8)
    else:
        roi += wp[..., :3].astype(np.float32) * (alpha * gain)


def blit_plain(dst, img, x, y, alpha=1.0, mode="over"):
    """Blit premultiplied BGRA array at integer top-left (x, y) with clipping."""
    h, w = img.shape[:2]
    DH, DW = dst.shape[:2]
    x0, y0 = max(x, 0), max(y, 0)
    x1, y1 = min(x + w, DW), min(y + h, DH)
    if x1 <= x0 or y1 <= y0:
        return
    sub = img[y0 - y:y1 - y, x0 - x:x1 - x]
    roi = dst[y0:y1, x0:x1]
    p = sub[..., :3].astype(np.float32) * alpha
    if mode == "over":
        a = sub[..., 3:4].astype(np.float32) * (alpha / 255.0)
        out = roi.astype(np.float32) * (1.0 - a) + p
    else:
        out = roi.astype(np.float32) + p
    roi[:] = np.clip(out, 0, 255).astype(np.uint8)
