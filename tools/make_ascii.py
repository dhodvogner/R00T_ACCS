"""Builds tools/ascii_skull.txt and tools/ascii_reaper.txt (text art for the download page) from the sprite atlas in assets/.

    python tools/make_ascii.py
"""
import json
import os

import cv2
import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAMP = " .:-=+*#%@"


def sprite_lum(name):
    atlas = np.asarray(Image.open(os.path.join(ROOT, "assets", "atlas.png")).convert("RGBA"))
    x, y, w, h = json.load(open(os.path.join(ROOT, "assets", "atlas.json")))[name]
    return atlas[y:y + h, x:x + w, 3]                      # luminance is stored in alpha (white art on transparent)


def to_ascii(name, cols, char_aspect=0.5):
    g = sprite_lum(name)
    ys, xs = np.nonzero(g > 30)
    g = g[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    mask = cv2.morphologyEx((g > 18).astype(np.uint8), cv2.MORPH_CLOSE, np.ones((25, 25), np.uint8))
    mask = cv2.GaussianBlur(cv2.erode(mask, np.ones((5, 5), np.uint8)).astype(np.float32), (0, 0), 3)
    g = (cv2.createCLAHE(clipLimit=3.0, tileGridSize=(6, 6)).apply(g).astype(np.float32) * mask)
    rows = int(round(g.shape[0] / g.shape[1] * cols * char_aspect))
    sm = cv2.resize(g, (cols, rows), interpolation=cv2.INTER_AREA) / 255.0
    sm = np.clip(sm / (np.percentile(sm[sm > 0.03], 97) + 1e-6), 0, 1) ** 0.6
    lines = ["".join(RAMP[min(len(RAMP) - 1, int(v * (len(RAMP) - 1) + 0.5))] if v > 0.06 else " " for v in row).rstrip() for row in sm]
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines)


for name, out, cols in (("skull_hero", "ascii_skull.txt", 64), ("reaper_hero", "ascii_reaper.txt", 50)):
    art = to_ascii(name, cols)
    with open(os.path.join(ROOT, "tools", out), "w", encoding="utf-8", newline="\n") as f:
        f.write(art + "\n")
    print(out, len(art.split("\n")), "rows x", cols, "cols")
