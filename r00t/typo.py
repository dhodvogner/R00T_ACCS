"""Neon-HUD typography: Bahnschrift condensed, tracked-out, slanted, 80s chrome gradient + neon outline. Returns premultiplied RGBA."""
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .paths import load_font

FONT = r"C:\Windows\Fonts\bahnschrift.ttf"
_fonts = {}


def font(size, variation=b"Bold Condensed"):
    k = (size, variation)
    if k not in _fonts:
        f = load_font(FONT, size, variation)
        _fonts[k] = f
    return _fonts[k]


def mixc(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def chrome_gradient(h, col, hot=1.0):
    """vertical 80s chrome: bright top, horizon band, saturated bottom."""
    y = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    white = np.array([255, 255, 255], np.float32)
    c = np.array(col, np.float32)
    stops = [(0.00, mixc(white, c, 0.10)), (0.38, mixc(white, c, 0.45)), (0.47, mixc(c, (255, 255, 255), 0.35)),
             (0.50, tuple(np.array(c) * 0.18)), (0.54, tuple(np.array(c) * 1.0)), (1.00, tuple(np.array(c) * 0.62))]
    out = np.zeros((h, 3), np.float32)
    xs = np.array([s[0] for s in stops])
    for ch in range(3):
        out[:, ch] = np.interp(y[:, 0], xs, [s[1][ch] for s in stops])
    return out[:, None, :] * hot


def neon_sprite(text, size, col, style="chrome", tracking=0.10, shear=0.20, variation=b"Bold Condensed", stroke=0.06):
    f = font(int(size), variation)
    chars = list(text)
    adv = [f.getlength(c) for c in chars]
    trk = tracking * size
    asc, desc = f.getmetrics()
    cap = -f.getbbox("H", anchor="ls")[1]
    pad = int(size * 0.35) + 10
    wtxt = int(sum(adv) + trk * (len(chars) - 1)) + 1
    w, h = wtxt + 2 * pad, asc + desc + 2 * pad
    m = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(m)
    x = pad
    for c, a in zip(chars, adv):
        d.text((x, pad + asc), c, font=f, fill=255, anchor="ls")
        x += a + trk
    fa = np.asarray(m, np.float32) / 255.0
    if shear:
        M = np.float32([[1, -shear, shear * (pad + asc - cap / 2)], [0, 1, 0]])
        fa = cv2.warpAffine(fa, M, (w, h), flags=cv2.INTER_LINEAR)
    sw = max(2, int(size * stroke))
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * sw + 1, 2 * sw + 1))
    outer = cv2.dilate(fa, k)
    mid = cv2.dilate(fa, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * max(1, sw // 2) + 1,) * 2))
    rgb = np.zeros((h, w, 3), np.float32)
    al = np.zeros((h, w), np.float32)
    c = np.array(col, np.float32)
    if style == "chrome":
        # neon stroke (accent), dark inner keyline, chrome fill
        a1 = outer
        rgb = c * a1[..., None]
        al = a1.copy()
        dark = np.array([20, 8, 40], np.float32)
        a2 = mid
        rgb = dark * a2[..., None] + rgb * (1 - a2[..., None])
        al = a2 + al * (1 - a2)
        grad = chrome_gradient(h, col)
        rgb = grad * fa[..., None] + rgb * (1 - fa[..., None])
        al = fa + al * (1 - fa)
    elif style == "hollow":
        ring = np.clip(outer - fa, 0, 1)
        inner = np.array([16, 6, 34], np.float32) * 0.7
        rgb = c * ring[..., None] * 1.0 + inner * fa[..., None] * 0.8
        al = np.clip(ring + fa * 0.8, 0, 1)
        rgb = np.where(ring[..., None] > 0.2, rgb, inner * fa[..., None] * 0.8)
        # bright core line on the stroke
        core = np.clip(ring - cv2.erode(ring, np.ones((3, 3), np.uint8)), 0, 1)
        rgb += np.array([255, 255, 255], np.float32) * core[..., None] * 0.7
    else:  # "solid": flat neon fill with a lighter top edge (captions)
        a1 = cv2.dilate(fa, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
        dark = np.array([12, 4, 28], np.float32)
        rgb = dark * a1[..., None]
        al = a1.copy()
        fill = np.array(col, np.float32)
        y = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
        fillg = fill * (1 - 0.35 * y) + 255 * 0.35 * (1 - y)
        rgb = fillg * fa[..., None] + rgb * (1 - fa[..., None])
        al = fa + al * (1 - fa)
    out = np.dstack([np.clip(rgb, 0, 255), np.clip(al, 0, 1) * 255]).astype(np.uint8)
    return out


# ---------------------------------------------------------------------------- brutalist type (masks / flat fills)
_BFONTS = {"cond": (r"C:\Windows\Fonts\bahnschrift.ttf", b"Bold Condensed"), "bold": (r"C:\Windows\Fonts\bahnschrift.ttf", b"Bold"),
           "black": (r"C:\Windows\Fonts\ariblk.ttf", None), "mono": (r"C:\Windows\Fonts\consolab.ttf", None)}


def brutal_sprite(text, font="cond", size=300, tracking=-0.02, style="fill", stroke=3):
    """tight-cropped white glyph run. style 'fill' -> solid coverage, 'outline' -> thin hollow stroke. Premultiplied RGBA."""
    path, var = _BFONTS[font]
    f = load_font(path, int(size), var)
    chars = list(text)
    adv = [f.getlength(c) for c in chars]
    trk = tracking * size
    asc, desc = f.getmetrics()
    pad = 12
    w = int(sum(adv) + trk * (len(chars) - 1)) + 2 * pad + 4
    h = asc + desc + 2 * pad
    m = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(m)
    x = pad
    for c, a in zip(chars, adv):
        d.text((x, pad + asc), c, font=f, fill=255, anchor="ls")
        x += a + trk
    a = np.asarray(m, np.float32) / 255.0
    if style == "outline":
        k = cv2.getStructuringElement(cv2.MORPH_RECT, (2 * stroke + 1, 2 * stroke + 1))
        a = np.clip(cv2.dilate(a, k) - a, 0, 1)
    ys, xs = np.nonzero(a > 0.04)
    if len(xs) == 0:
        a = np.zeros((4, 4), np.float32)
    else:
        a = a[max(0, ys.min() - 2):ys.max() + 3, max(0, xs.min() - 2):xs.max() + 3]
    rgb = np.repeat(a[..., None] * 255.0, 3, axis=2)
    return np.dstack([rgb, a * 255.0]).clip(0, 255).astype(np.uint8)
