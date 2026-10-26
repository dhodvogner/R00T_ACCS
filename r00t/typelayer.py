"""Brutalist type layer: typography as a visual layer (invert masks, knock-out windows, giant cropped / bleeding type),
driven by the real drum hits rather than by the lyric sheet."""
import bisect
import json
import math
import os
import re

import numpy as np

from .choreo2 import (CAPTIONS, CHOPS, KICK_T, KICK_S, SNARE_T, SNARE_S, T_D1, T_MID, T_D2, T_OUT, T_PRE, hash01, cl)
from .paths import asset
from .typo import brutal_sprite

from .canvas import V

H = 1920
INV = (1.0, 0.0, 0.0)     # mask channel R: invert the picture inside the letters
WIN = (0.0, 1.0, 0.0)     # mask channel G: the picture only shows through the letters
EVENTS = []


def E(kind, mode, words, t0, t1, **p):
    ev = dict(kind=kind, mode=mode, words=list(words), t0=float(t0), t1=float(t1), **p)
    ev.setdefault("rev", [t0] * len(words))
    EVENTS.append(ev)
    return ev


# ============================================================================ event authoring
def _clean(w):
    return re.sub(r"[^A-Za-z0-9']", "", w).upper()


def build_captions():
    """lyric lines in the calm sections: giant stacked words that bleed off the frame, revealed word by word"""
    for n, (txt, t0, t1, col) in enumerate(CAPTIONS):
        words = [w for w in (_clean(x) for x in txt.split()) if w]
        step = min(0.22, max(0.08, (t1 - t0) * 0.5 / max(len(words), 1)))
        rev = [t0 + i * step for i in range(len(words))]
        E("stack", "invert" if n % 3 != 1 else "solid", words, t0, t1 + 0.25, rev=rev, fill=1.04, hmax=1250, wordhmax=520, dy=-60 + 60 * (n % 2),
          vib=5.0, alpha=0.92, color=(255, 255, 255), cap_line=True, ann=[f"{t0:06.2f}", f"LINE//{n:02d}"])


def build_chops():
    chops = [c for c in CHOPS if c[3] != "letter" and not (58.0 <= c[1] <= 64.6)]
    for n, (txt, t0, hold, kind) in enumerate(chops):
        end = t0 + (hold if hold is not None else 1.0)
        nxt = chops[n + 1][1] if n + 1 < len(chops) else 1e9
        if hold is None:
            end = min(end, nxt)
        words = txt.replace("!", "").split()
        mode = "invert" if n % 2 == 0 else "window"
        if kind == "echo":
            E("stack", "invert", words, t0, end, fill=1.0, hmax=1500, wordhmax=420, dy=0, vib=6.0, alpha=0.9, grow=0.9)
        elif len(words) == 1:
            E("giant", mode, words, t0, end, cap=1450 + 450 * hash01(t0), x0=(hash01(t0 * 3) - 0.5) * 300, dy=(hash01(t0 * 5) - 0.5) * 240,
              vib=20.0, alpha=1.0, win=0.9, ann=[f"T+{t0:06.2f}"])
        else:
            E("stack", mode, words, t0, end, fill=1.1, hmax=1650, wordhmax=720, dy=0, vib=24.0, alpha=1.0, win=0.9, ann=[f"T+{t0:06.2f}"])


def hit_times(a, b, kmin=0.7, smin=0.9, gap=0.26):
    hits = []
    for t, s in zip(KICK_T, KICK_S):
        if a <= t < b and s >= kmin:
            hits.append((float(t), float(s)))
    for t, s in zip(SNARE_T, SNARE_S):
        if a <= t < b and s >= smin:
            hits.append((float(t), float(s)))
    hits.sort()
    out, last = [], -9.0
    for t, s in hits:
        if t - last >= gap:
            out.append((t, s))
            last = t
    return out


POOL = ["OWN", "NIGHT", "SYSTEM", "FAIL", "NEON", "ROOT", "OVER", "LOAD", "HACK", "GLITCH", "RUN", "KILL", "SUDO", "ERROR", "180",
        "0xFF", "ACCEL", "ERATE", "LOOP", "PANIC"]
STYLES = ["giant_inv", "giant_win", "stack_inv", "outline", "rows_inv", "giant_win", "strip_inv", "stack_win"]


def _busy(t, blocked):
    return any(a - 0.05 <= t <= b + 0.12 for a, b in blocked)


def build_hits():
    blocked = [(c[1], c[1] + (c[2] or 0.8)) for c in CHOPS if c[3] != "letter" and not (58.0 <= c[1] <= 64.6)]
    blocked += [(T_D1, T_D1 + 4.6), (T_D2, T_D2 + 4.8), (56.2, 65.2)]       # opening texts + the scripted section
    wins = [(T_D1 + 4.6, T_MID - 0.1), (T_D2 + 4.8, T_OUT - 0.2)]
    for a, b in wins:
        hits = [h for h in hit_times(a, b) if not _busy(h[0], blocked)]
        for i, (t, s) in enumerate(hits):
            nxt = hits[i + 1][0] if i + 1 < len(hits) else t + 0.6
            t1 = min(nxt - 0.02, t + 0.62)
            st = STYLES[int(hash01(t * 1.7) * len(STYLES)) % len(STYLES)]
            w1 = POOL[int(hash01(t * 2.3) * len(POOL)) % len(POOL)]
            w2 = POOL[int(hash01(t * 4.1) * len(POOL)) % len(POOL)]
            ann = [f"T+{t:06.2f}", f"KICK {s:.1f}"]
            common = dict(vib=18.0 + 20 * s, alpha=1.0, win=0.88, ann=ann)
            if st == "giant_inv":
                E("giant", "invert", [w1], t, t1, cap=1500 + 450 * hash01(t), x0=(hash01(t * 3) - 0.5) * 500, dy=(hash01(t * 5) - 0.5) * 300, **common)
            elif st == "giant_win":
                E("giant", "window", [w1], t, t1, cap=1700 + 300 * hash01(t), x0=(hash01(t * 3) - 0.5) * 400, dy=0, **common)
            elif st == "stack_inv":
                E("stack", "invert", [w1, w2], t, t1, fill=1.1, hmax=1700, wordhmax=860, dy=0, **common)
            elif st == "stack_win":
                E("stack", "window", [w1, w2], t, t1, fill=1.12, hmax=1750, wordhmax=900, dy=0, **common)
            elif st == "outline":
                E("giant", "outline", [w1], t, t1, cap=1400 + 400 * hash01(t), x0=(hash01(t * 3) - 0.5) * 300, dy=0, color=(255, 255, 255), **common)
            elif st == "rows_inv":
                E("rows", "invert", [w1], t, t1 + 0.1, n=7, vx=900 + 800 * hash01(t), alpha=0.9, ann=ann, vib=8.0)
            else:
                E("giant", "invert", [w1], t, t1, cap=420, rot=math.pi / 2 * (1 if hash01(t) > 0.5 else -1), strip_x=130 + 820 * hash01(t * 9),
                  x0=0, dy=0, **common)


def build_script_56_65():
    """0:56-1:05: breakbeat + stuttering vocal loop (no words). Type locked to the real hits: snare roll 57.45/57.62/57.78, kicks 59.00 59.50 60.35 60.85 61.70 62.20 63.05 64.38."""
    E("giant", "invert", ["OWN"], 56.80, 57.40, cap=1750, x0=-40, dy=-40, vib=26.0, alpha=1.0, ann=["T+56.80"])
    E("giant", "window", ["THE"], 57.45, 57.61, cap=1850, x0=0, dy=0, vib=30.0, win=0.92, alpha=1.0)
    E("giant", "invert", ["NIGHT"], 57.62, 57.77, cap=1550, x0=260, dy=40, vib=30.0, alpha=1.0)
    E("stack", "invert", ["OWN", "THE", "NIGHT"], 57.78, 58.12, fill=1.1, hmax=1800, wordhmax=900, dy=0, vib=40.0, alpha=1.0, ann=["T+57.78", "OWN THE NIGHT"])
    E("rows", "invert", ["ACCELERATE"], 58.13, 58.98, n=8, vx=1400, alpha=0.55, vib=0.0)
    E("giant", "invert", ["ACCEL"], 59.00, 59.48, cap=1900, x0=0, dy=0, vib=34.0, alpha=1.0, ann=["T+59.00", "ACCEL"])
    E("giant", "window", ["ERATE"], 59.50, 60.30, cap=1900, x0=0, dy=0, vib=28.0, win=0.95, alpha=1.0, ann=["T+59.50", "ERATE"])
    E("giant", "outline", ["ERATE"], 59.50, 60.30, cap=1900, x0=0, dy=0, vib=28.0, alpha=1.0, color=(255, 255, 255))
    E("stack", "invert", ["180", "BPM"], 60.35, 60.82, fill=1.1, hmax=1750, wordhmax=1000, dy=0, vib=34.0, alpha=1.0, ann=["T+60.35"])
    E("stack", "window", ["SYSTEM", "FAIL"], 60.85, 61.65, fill=1.12, hmax=1750, wordhmax=900, dy=0, vib=30.0, win=0.92, alpha=1.0, ann=["T+60.85", "SYSTEM FAILURE"])
    E("giant", "invert", ["FAIL"], 61.70, 62.15, cap=1850, x0=-120, dy=0, vib=34.0, alpha=1.0)
    E("stack", "invert", ["OVER", "LOAD"], 62.20, 63.00, fill=1.1, hmax=1800, wordhmax=900, dy=0, vib=36.0, alpha=1.0, ann=["T+62.20"])
    E("giant", "window", ["0xFF"], 63.05, 63.17, cap=1700, x0=0, dy=0, vib=30.0, win=0.92, alpha=1.0)
    E("giant", "invert", ["FF"], 63.18, 63.52, cap=1900, x0=0, dy=0, vib=40.0, alpha=1.0)
    E("rows", "window", ["OVERLOAD"], 63.53, 64.35, n=7, vx=1700, win=0.8, alpha=1.0, vib=0.0)
    E("stack", "invert", ["ACCEL", "ERATE"], 64.38, 64.95, fill=1.15, hmax=1850, wordhmax=950, dy=0, vib=46.0, alpha=1.0, ann=["T+64.38", "ACCELERATE"])
    E("stack", "outline", ["ACCEL", "ERATE"], 64.38, 64.95, fill=1.15, hmax=1850, wordhmax=950, dy=0, vib=46.0, alpha=1.0, color=(255, 255, 255))


build_captions()
build_chops()
build_hits()
build_script_56_65()

# flat full-bleed "ACCESS GRANTED" / "SYSTEM OVERRIDE" blocks (drawn by choreo3 through draw_bigtext)
BLOCKS = [dict(lines=["ACCESS", "GRANTED"], t0=T_D1, t1=T_D1 + 4.4, color=(255, 40, 70), cy=840),
          dict(lines=["SYSTEM", "OVERRIDE"], t0=T_D2, t1=T_D2 + 4.4, color=(0, 235, 255), cy=840)]


def _load_fixed():
    """assets/type_events.json is the hand-fixed timing of every type event (exported from the editor project);
    when present it replaces the procedurally generated list above."""
    path = asset("type_events.json")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    EVENTS[:] = []
    for e in d["events"]:
        e = dict(e)
        e["color"] = tuple(e.get("color", (255, 255, 255)))
        e.setdefault("rev", [e["t0"]] * len(e["words"]))
        EVENTS.append(e)
    BLOCKS[:] = [dict(b, color=tuple(b["color"])) for b in d.get("blocks", [])]


_load_fixed()
EVENTS.sort(key=lambda e: e["t0"])
_T0 = [e["t0"] for e in EVENTS]
_MAXLEN = max(e["t1"] - e["t0"] for e in EVENTS)


def active(t):
    j = bisect.bisect_right(_T0, t)
    lo = bisect.bisect_left(_T0, t - _MAXLEN - 0.5)
    return [e for e in EVENTS[lo:j] if e["t0"] - 0.005 <= t <= e["t1"]]


def win_amount(t):
    w = 0.0
    for e in active(t):
        if e["mode"] == "window":
            w = max(w, e.get("win", 0.9))
    return w


# ============================================================================ drawing
def wkey(eng, text, font="cond", style="fill"):
    k = ("bw", text, font, style)
    if k not in eng.sprites:
        return eng.tex_from_rgba(k, brutal_sprite(text, font, 300, style=style, stroke=3))
    return eng.sprites[k]


def _route(eng, fm, ft, ev):
    m = ev["mode"]
    if m == "invert":
        return fm, INV
    if m == "window":
        return fm, WIN
    col = tuple(c / 255.0 for c in ev.get("color", (255, 255, 255)))
    return ft, col


def _word(eng, fbo, tint, key, cx, cy, scale, alpha, rot=0.0):
    eng.draw_sprite(fbo, key, cx, cy, scale=scale, rot=rot, alpha=alpha, tint=tint)


def draw_event(eng, fm, ft, t, ev, kick):
    mode = ev["mode"]
    style = "outline" if mode == "outline" else "fill"
    fbo, tint = _route(eng, fm, ft, ev)
    kind = ev["kind"]
    dt = t - ev["t0"]
    fr = math.floor(t * 60)
    amp = ev.get("vib", 10.0) * (0.35 + kick)
    jx = (hash01(fr * 0.73 + ev["t0"]) - 0.5) * 2 * amp
    jy = (hash01(fr * 1.31 + ev["t0"]) - 0.5) * 2 * amp * 0.7
    alpha = ev.get("alpha", 1.0) * (1.0 if (dt > 0.06 or hash01(fr + ev["t0"]) > 0.25) else 0.35)
    fade = cl((ev["t1"] - t) / 0.12) if ev["t1"] - ev["t0"] > 0.5 else 1.0
    alpha *= fade
    pop = 1.0 + 0.30 * math.exp(-dt / 0.05)
    if kind == "stack" and V.w / H > 1.25 and len(ev["words"]) >= 3:
        # landscape: set the line as full-width justified rows of one uniform height (2-3 rows)
        words = ev["words"]
        keys = [wkey(eng, w, "cond", style) for w in words]
        asp = [k[1] / float(k[2]) for k in keys]
        nrows = 2 if len(words) <= 5 else 3
        tot = sum(asp)
        rows, acc = [[]], 0.0
        for i, a_ in enumerate(asp):
            if acc >= tot / nrows * len(rows) - 1e-6 and len(rows) < nrows:
                rows.append([])
            rows[-1].append(i)
            acc += a_
        hrs = []
        for r in rows:
            hrs.append(min(ev.get("wordhmax", 900) * 1.2, V.w * (min(ev.get("fill", 1.06), 0.86) if ev.get("cap_line") else ev.get("fill", 1.06)) / (sum(asp[i] for i in r) + 0.24 * (len(r) - 1))))
        gap_y = -0.04 * sum(hrs) / len(hrs)
        total = sum(hrs) + gap_y * (len(rows) - 1)
        f = min(1.0, ev.get("hmax", 1700) / total)
        hrs = [h_ * f for h_ in hrs]
        total *= f
        y = 960 + ev.get("dy", 0) - total / 2.0
        for r, hr in zip(rows, hrs):
            gap = 0.24 * hr
            wrow = sum(asp[i] * hr for i in r) + gap * (len(r) - 1)
            x = V.cx - wrow / 2.0 + jx
            cy = y + hr / 2.0 + jy
            y += hr + gap_y * f
            for i in r:
                wpx = asp[i] * hr
                if t >= ev["rev"][i] - 0.005:
                    d_i = t - ev["rev"][i]
                    pp = 1.0 + 0.30 * math.exp(-d_i / 0.05)
                    _word(eng, fbo, tint, keys[i], x + wpx / 2.0, cy, hr / keys[i][2] * pp, alpha)
                x += wpx + gap
    elif kind == "stack":
        words = ev["words"]
        keys = [wkey(eng, w, "cond", style) for w in words]
        scales = []
        for k in keys:
            s = V.w * ev.get("fill", 1.06) / k[1]
            s = min(s, ev.get("wordhmax", 900) / k[2])
            scales.append(s)
        gap = -0.04 * (sum(k[2] * s for k, s in zip(keys, scales)) / len(keys))
        total = sum(k[2] * s for k, s in zip(keys, scales)) + gap * (len(keys) - 1)
        if total > ev.get("hmax", 1700):
            f = ev.get("hmax", 1700) / total
            scales = [s * f for s in scales]
            total *= f
            gap *= f
        grow = 1.0 + ev.get("grow", 0.0) * dt
        y = 960 + ev.get("dy", 0) - total / 2.0
        for i, (k, s) in enumerate(zip(keys, scales)):
            hp = k[2] * s
            cy = y + hp / 2.0
            y += hp + gap
            if t < ev["rev"][i] - 0.005:
                continue
            d_i = t - ev["rev"][i]
            pp = 1.0 + 0.30 * math.exp(-d_i / 0.05)
            _word(eng, fbo, tint, k, V.cx + jx, cy + jy, s * pp * grow, alpha)
    elif kind == "giant":
        k = wkey(eng, ev["words"][0], "cond", style)
        rot = ev.get("rot", 0.0)
        s = min(ev.get("cap", 1500) / k[2], ev.get("maxw", 1.75 * V.w) / k[1])
        x = V.cx + ev.get("x0", 0) + ev.get("vx", 0) * dt + jx
        y = 960 + ev.get("dy", 0) + jy
        if rot != 0.0:
            x = ev.get("strip_x", V.cx) + jx
            y = 960 + jy
        _word(eng, fbo, tint, k, x, y, s * pop, alpha, rot)
    elif kind == "rows":
        k = wkey(eng, ev["words"][0], "cond", "fill")
        n = ev.get("n", 6)
        rowh = H / n
        s = rowh / k[2] * 0.92
        wpx = k[1] * s
        period = wpx + 0.1 * wpx
        for r in range(n):
            off = (dt * ev.get("vx", 900) * (1 if r % 2 else -1) + r * period * 0.37) % period
            c = -1
            while c * period + off - wpx / 2 < V.w + wpx:
                _word(eng, fbo, tint, k, c * period + off + wpx * 0.5 - period * 0.5 + V.w * 0.0, rowh * (r + 0.5), s, alpha)
                c += 1
    # tiny mono annotations (text layer): timecodes / labels in the corners
    for ai, a in enumerate(ev.get("ann", [])):
        key = eng.sprite(a, "mono", 30, (255, 255, 255), grad=False)
        px = 70 + (hash01(ev["t0"] * 7.1 + ai) * 0.9) * 600
        py = 70 + ai * 44 + (1700 if ai % 2 else 0) * hash01(ev["t0"] * 3.3)
        eng.draw_sprite(ft, key, px + key[1] / 2.0, py, scale=1.0, alpha=0.9 * fade, tint=(1.2, 1.2, 1.2))


def mask_pass(eng, fm, ft, t, kick):
    for ev in active(t):
        if ev["mode"] in ("invert", "window"):
            draw_event(eng, fm, ft, t, ev, kick)


def text_pass(eng, fm, ft, t, kick):
    for ev in active(t):
        if ev["mode"] in ("outline", "solid"):
            draw_event(eng, fm, ft, t, ev, kick)


def draw_bigtext(eng, ft, p, t):
    """ACCESS GRANTED / SYSTEM OVERRIDE: flat, full-bleed, vibrating block type"""
    if not (p["t0"] - 0.02 <= t <= p["t1"] + 0.1):
        return
    dt = t - p["t0"]
    k = p["kick"]
    fade = cl((p["t1"] - t) / 0.5) if t > p["t1"] - 0.5 else 1.0
    col = tuple(c / 255.0 for c in p["color"])
    keys = [wkey(eng, ln, "cond") for ln in p["lines"]]
    scales = [min(V.w * 1.0 / kk[1], 700 / kk[2]) for kk in keys]
    gap = -0.03 * scales[0] * keys[0][2]
    total = sum(kk[2] * s for kk, s in zip(keys, scales)) + gap * (len(keys) - 1)
    y = p["cy"] - total / 2.0
    amp = 10.0 + 38.0 * k
    for i, (kk, s) in enumerate(zip(keys, scales)):
        hp = kk[2] * s
        cy = y + hp / 2.0
        y += hp + gap
        n1 = hash01(math.floor(t * 60) * 0.73 + i * 3.1)
        n2 = hash01(math.floor(t * 60) * 1.31 + i * 7.7)
        sc = s * (1.0 + 0.04 * k + 0.9 * math.exp(-dt / 0.07))
        flick = 1.0 if (dt < 0.2 or hash01(math.floor(t * 40) + i) > 0.10) else 0.3
        eng.draw_sprite(ft, kk, V.cx + (n1 - 0.5) * 2 * amp, cy + (n2 - 0.5) * 2 * amp * 0.7, scale=sc, rot=(n1 - 0.5) * 0.03 * (0.4 + k),
                        alpha=fade * flick, split=14.0 + 40.0 * k, tint=col)
    lab = eng.sprite(p.get("label", "ROOT@NIGHT:~#  PRIVILEGE ESCALATION COMPLETE"), "mono", 34, (255, 255, 255), grad=False)
    eng.draw_sprite(ft, lab, V.cx, p["cy"] + total / 2.0 + 60, alpha=0.9 * fade, tint=(1.2, 1.2, 1.2))
