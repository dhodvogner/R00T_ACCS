"""Choreography v2: a clean synthwave world that gets hacked by the drops (ASCII skulls, reapers, popups, explosions)."""
import bisect
import math

import numpy as np

from .features import Feat, FPS
from .canvas import V


def cl(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def ramp(t, a, b):
    return cl((t - a) / (b - a))


def sstep(x):
    x = cl(x)
    return x * x * (3 - 2 * x)


def lerp(a, b, x):
    return a + (b - a) * x


def hash01(x):
    return (math.sin(x * 127.1 + 311.7) * 43758.5453) % 1.0


def hexrgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


PINK, CYAN, VIOLET, ORANGE, YELLOW, RED = (hexrgb(c) for c in ("#ff2d95", "#00e5ff", "#8a2bff", "#ff8c26", "#ffe14a", "#ff2040"))

# ------------------------------------------------------------------ song map
T_INTRO_B, T_PRE, T_BLACK, T_D1 = 11.5, 36.5, 48.0, 48.68
T_MID, T_RISER, T_BLACK2, T_D2, T_OUT, T_END, T_CRT = 101.8, 112.3, 118.1, 118.85, 151.2, 180.0, 179.25

F = Feat()
BEATS = F.beat_t
_d1 = [T_D1, 59.35, 70.0, 80.7, 91.35, T_MID]
D1_B = [_d1[0]] + [F.nearest_beat(x) for x in _d1[1:-1]] + [_d1[-1]]
_d2 = np.arange(T_D2, T_OUT, 8 / 3.0)
D2_B = [T_D2] + [F.nearest_beat(x) for x in _d2[1:]] + [T_OUT]
D1_TYPES = ["skull", "tunnel", "wall", "world", "overload"]
D2_TYPES = ["skullkal", "tunnel", "wall", "eq", "matrix", "world", "skullgrid", "objkal", "hacker", "skullkal",
            "tunnel", "eq", "wall"]

OBJ = ["vhs", "cassette", "crt", "floppy", "handheld", "boombox", "headphones", "joystick", "sunglasses", "phone",
       "skate", "bust", "car_front", "heart", "star", "bolt", "martini", "palm_neon"]


def speed(t):
    if t < T_INTRO_B:
        return lerp(0.7, 1.2, ramp(t, 3, T_INTRO_B))
    if t < 26.0:
        return 1.2
    if t < T_PRE:
        return lerp(1.2, 2.2, ramp(t, 26, 36))
    if t < 43.0:
        return lerp(2.2, 4.0, ramp(t, T_PRE, 43))
    if t < 47.3:
        return lerp(4.0, 12.0, ramp(t, 43, 47.3))
    if t < T_D1:
        return 10.0
    if t < T_MID:
        return 6.5 + 1.5 * math.sin(t * 0.7)
    if t < T_RISER:
        if t < 103.4:
            return 2.0
        if t < 104.0:
            return lerp(2.0, 9.0, ramp(t, 103.4, 104.0))
        return lerp(9.0, 3.0, ramp(t, 104.0, 108.0))
    if t < T_D2:
        return lerp(3.0, 16.0, ramp(t, T_RISER, T_BLACK2))
    if t < T_OUT:
        return 0.2 if 135.6 < t < 136.5 else 9.0
    if t < 157.0:
        return lerp(5.0, 0.6, ramp(t, T_OUT, 157.0))
    return lerp(0.6, 0.25, ramp(t, 157.0, 178.0))


N_FRAMES = int(round(T_END * FPS))
DIST = np.cumsum([speed(i / FPS) / FPS for i in range(N_FRAMES + 1)])

# ------------------------------------------------------------------ events: kick bursts + snare popups
KICK_T, KICK_S = F.kick_t, F.kick_str
SNARE_T, SNARE_S = F.snare_t, F.snare_str


def _bursts():
    out = []
    for t, s in zip(KICK_T, KICK_S):
        if s < 0.40:
            continue
        if (43.0 <= t < 48.0) or (T_D1 <= t < T_MID) or (T_RISER + 3 <= t < T_BLACK2) or (T_D2 <= t < T_OUT):
            out.append((float(t), float(s)))
    out2, last = [], -9
    for t, s in out:
        if t - last > 0.20:
            out2.append((t, s))
            last = t
    return out2


BURSTS = _bursts()
BURST_T = [b[0] for b in BURSTS]


def _popups():
    out, last = [], -9
    for t, s in zip(SNARE_T, SNARE_S):
        if s < 0.45 or t - last < 0.30:
            continue
        ok = (37.5 <= t < 48.0) or (T_D1 <= t < T_MID) or (T_RISER + 2 <= t < T_BLACK2) or (T_D2 <= t < T_OUT)
        if ok:
            out.append(float(t))
            last = t
    return out


POPUPS = _popups()
POPUP_T = POPUPS

from .data import CHOPS, SHATTERS, CAPTIONS  # noqa: E402,F401


def A(name, x, y, h, **kw):
    return ("atlas", dict(name=name, cx=x, cy=y, height=h, **kw))


def beat_flash(t, m=1):
    j = int(np.searchsorted(BEATS, t, side="right")) - 1
    j = min(max(j, 0), len(BEATS) - 2)
    per = BEATS[j + 1] - BEATS[j]
    frac = ((t - BEATS[j]) / per * m) % 1.0
    return math.exp(-(frac * per / m) / 0.045)


def look_index(t, bounds):
    for k in range(len(bounds) - 1):
        if bounds[k] <= t < bounds[k + 1]:
            return k, t - bounds[k]
    return len(bounds) - 2, 0.0


# ------------------------------------------------------------------ sprite building blocks
def world_props(cm, t, f, hack, objs=0.0, rage=0.0):
    k, b = f["kick"], f["bass_s"]
    amp = 0.03 + 0.14 * rage
    dis = cl(hack - 0.45) * 0.75
    cm["mid"].append(A("palm1", 150 + 6 * math.sin(t * 41) * b * (1 + 4 * rage), 1010, 1500, rot=amp * math.sin(t * (0.9 + 2.5 * rage)),
                       dissolve=dis * (0.4 + 0.6 * hash01(math.floor(t * 6))), dsz=14, slice_=0.05 * hack * hash01(math.floor(t * 9))))
    cm["mid"].append(A("palm2", 935 - 6 * math.sin(t * 37) * b * (1 + 4 * rage), 1060, 1400, flip=True,
                       rot=-amp * math.sin(t * (0.7 + 2.5 * rage) + 1), dissolve=dis * (0.4 + 0.6 * hash01(math.floor(t * 6) + 3)), dsz=14,
                       slice_=0.05 * hack * hash01(math.floor(t * 9) + 2)))
    slots = [("cassette", 190, 520, 210, 5.0), ("vhs", 900, 470, 200, 7.0), ("headphones", 110, 860, 190, 9.0),
             ("boombox", 960, 880, 230, 11.0), ("handheld", 330, 250, 170, 13.0), ("crt", 780, 240, 200, 15.0)]
    for i, (nm, x, y, h, t0) in enumerate(slots):
        al = sstep(ramp(t, t0, t0 + 2.5)) * objs
        if al <= 0.01:
            continue
        bob = 18 * math.sin(t * 0.9 + i * 1.7)
        pulse = 1.0 + (0.10 + 0.25 * hack) * k
        dxj = (hash01(i * 3.3 + math.floor(t * 20)) - 0.5) * 30 * hack * k
        cm["mid"].append(A(nm, x + dxj, y + bob, h * pulse, rot=0.10 * math.sin(t * 0.7 + i * 2.0) + 0.3 * hack * hash01(math.floor(t * 8) + i) * (1 if i % 2 else -1),
                           alpha=al, dissolve=cl(hack - 0.3) * 0.6 * hash01(math.floor(t * 7) + i * 5), dsz=12, split=0.004 + 0.02 * hack * f["snare"]))


def skull(cm, hook, t, f, cx, cy, h, which="skull_hero", tint=(1, 1, 1), cell=(14, 24), ascii_=1.0, k_amp=0.22, alpha=1.0, extra_rot=0.0):
    k, s = f["kick"], f["snare"]
    sc = 1.0 + k_amp * k ** 1.1
    jx = (hash01(math.floor(t * 30) * 1.7) - 0.5) * 2 * 12 * k
    jy = (hash01(math.floor(t * 30) * 2.9) - 0.5) * 2 * 12 * k
    tint = tuple(x * 1.35 for x in tint)
    cm[hook].append(A(which, cx + jx, cy + jy, h * sc, rot=0.02 * math.sin(t * 3.0) + 0.03 * (hash01(math.floor(t * 12)) - 0.5) * s + extra_rot,
                      alpha=alpha, tint=tint, ascii_=ascii_, cell=cell, split=0.003 + 0.012 * s + 0.004 * k, jit=0.25 + 0.5 * k,
                      slice_=0.05 * max(0.0, s - 0.55), time=t))


def wallpaper(cm, hook, t, f, alpha=0.38, which="reaper_hero", th=300, cell=(7, 12), tint=(1, 1, 1)):
    sn = f["snare"]
    scroll = (t * 70.0) % (th * 0.8)
    cols = int(V.w / (th * 0.62)) + 2
    rows = int(1920 / th) + 3
    cw = th * 0.62
    for j in range(rows):
        for i in range(cols):
            x = i * cw + (cw * 0.5 if j % 2 else 0) - cw * 0.5
            y = j * th * 0.8 - scroll
            fl = hash01(i * 7.7 + j * 3.1 + math.floor(t * 6))
            a = alpha * (0.35 + 0.65 * (fl > 0.5)) * (0.7 + 0.8 * sn)
            cm[hook].append(A(which, x, y, th, alpha=min(a, 1.0), tint=tint, ascii_=1.0, cell=cell, time=t, jit=0.2,
                              flip=bool((i + j) % 2)))


def bursts(cm, t, strength=1.0, size=250):
    j = bisect.bisect_right(BURST_T, t)
    for b in range(max(0, j - 7), j):
        tb, sb = BURSTS[b]
        a = t - tb
        life = 1.15
        if a < 0 or a > life:
            continue
        n = 4 + (1 if sb > 0.8 else 0)
        for q in range(n):
            hh = hash01(tb * 7.1 + q * 13.3)
            ang = hash01(tb * 3.3 + q * 5.1) * 6.2831
            spd = 520 + 1200 * hh
            r = spd * (1.0 - math.exp(-a * 3.2)) / 3.2
            u = a / life
            sc = (0.25 + 1.9 * u ** 0.8) * (0.8 + 0.5 * sb) * strength
            name = OBJ[int(hash01(tb * 1.7 + q * 9.9) * len(OBJ)) % len(OBJ)]
            cm["pre"].append(A(name, V.cx + math.cos(ang) * r, 780 + math.sin(ang) * r, size * sc, rot=(hh - 0.5) * 9.0 * a,
                               alpha=(1 - u ** 2) * 0.95, split=0.02 * (1 - u), dissolve=0.0))


def tunnel_objects(cm, t, f, count=12, size=240, speed_=0.35):
    for i in range(count):
        ph = (i / count + t * speed_ + hash01(i * 2.3) * 0.0) % 1.0
        ang = hash01(i * 4.7) * 6.2831 + t * 0.15
        r = 30 + 1100 * ph ** 2.2
        sc = 0.10 + 1.6 * ph ** 1.7
        name = OBJ[(i * 5 + 1) % len(OBJ)]
        cm["pre"].append(A(name, V.cx + math.cos(ang) * r, 780 + math.sin(ang) * r * 1.25, size * sc * (1 + 0.2 * f["kick"]),
                           rot=t * (0.4 + 0.3 * hash01(i)) * (1 if i % 2 else -1), alpha=cl(ph * 5.0) * (1 - cl((ph - 0.9) * 10.0)) * 0.95,
                           split=0.012 * ph))


def popups(cm, t, f, rate=1.0, hack=1.0):
    j = bisect.bisect_right(POPUP_T, t)
    for b in range(max(0, j - 6), j):
        te = POPUP_T[b]
        a = t - te
        life = 0.55 + 0.5 * hash01(te * 3.1)
        if a < 0 or a > life:
            continue
        if hash01(te * 11.1) > rate:
            continue
        kind = int(hash01(te * 5.7) * 8) % 8
        x = 160 + hash01(te * 1.3) * (V.w - 320)
        y = 260 + hash01(te * 2.9) * 1100
        pop = 1.0 + 0.5 * math.exp(-a / 0.05)
        flick = 1.0 if (a < 0.1 or hash01(math.floor(t * 40) + te) > 0.25) else 0.2
        cm["mid"].append(("popup", dict(kind=kind, cx=x, cy=y, scale=pop * 1.05, rot=(hash01(te) - 0.5) * 0.14,
                                        alpha=flick * (1 - cl((a - life + 0.12) / 0.12)), split=0.012)))


def side_terminals(cm, t, alpha=0.35):
    cm["mid"].append(("term", dict(cx=95, cy=960, scroll=(t * 90.0), alpha=alpha, side=0)))
    cm["mid"].append(("term", dict(cx=V.w - 95, cy=960, scroll=(-t * 70.0 + 400), alpha=alpha, side=1)))


# ------------------------------------------------------------------ the frame
def frame_state(i):
    t = i / FPS
    f = F.at(i)
    kick, snare, hat, bass_s, rms = f["kick"], f["snare"], f["hat"], f["bass_s"], f["rms"]
    dist = float(DIST[min(i, N_FRAMES)])
    cm = {"pre0": [], "pre": [], "mid": [], "post": []}

    sc = dict(u_t=t, u_dist=dist, u_bass=f["bass_s"], u_lowmid=f["lowmid"], u_mid=f["mid"], u_high=f["high"], u_rms=f["rms_s"],
              u_kick=kick, u_snare=snare, u_hat=hat, u_wob=bass_s, u_pal=0.0, u_shatter=0.0, u_city=1.0, u_neon=1.0, u_sun=1.0,
              u_hack=0.0, u_zoom=1.0, u_sA=0, u_sB=0, u_mix=0.0, u_aA=(0.0, -1.0, 0.0, 0.0), u_aB=(0.0, 0.0, 0.0, 0.0))
    kal = dict(u_seg=1.0, u_krot=0.0, u_kzoom=1.0, u_kphase=0.0, u_mirx=0.0, u_mirror_y=0.0, u_kc=(0.0, 0.0))
    fb = dict(u_decay=0.0, u_fzoom=1.0, u_frot=0.0, u_fhue=0.0, u_fmix=0.5, u_fshift=(0.0, 0.0))
    po = dict(u_t=t, u_bloom=0.9, u_ca=0.002, u_glit=0.0, u_flash=0.0, u_flashcol=(1.0, 1.0, 1.0), u_inv=0.0, u_black=0.0,
              u_fade=1.0, u_scan=0.08, u_grain=0.03, u_vig=0.5, u_pump=0.0, u_crt=0.0, u_dot=0.0, u_expo=1.0, u_sat=1.12,
              u_shake=(0.0, 0.0), u_vhs=0.18, u_pix=0.0, u_roll=0.0, u_tilt=0.0)
    accent = CYAN

    def shake(amp):
        po["u_shake"] = (amp * kick * (hash01(i * 1.3) - 0.5), amp * kick * (hash01(i * 2.7) - 0.5))

    def mixw(c, k=0.5):
        return tuple(x * (1 - k) + k for x in c)

    # ============================================================ INTRO / VERSES / PRE-CHORUS
    if t < T_D1:
        sc["u_sun"] = sstep(ramp(t, 0.5, 14.0))
        hack = 0.12 * ramp(t, 28.0, T_PRE) + 0.88 * sstep(ramp(t, T_PRE, 47.0))
        sc["u_hack"] = hack
        dirv = -1.0 if t < 41 else lerp(-1.0, 1.0, ramp(t, 41, 45))
        sc["u_aA"] = (0.0, dirv, 0.0, 0.0)
        sc["u_zoom"] = 1.0 + 2.4 * sstep(ramp(t, 43.0, 47.3))
        fb.update(u_decay=0.35 + 0.35 * hack, u_fzoom=1.0 + 0.012 * hack, u_fmix=0.6)
        po.update(u_vhs=0.18 + 0.7 * hack, u_bloom=0.9 + 0.4 * kick + 0.5 * hack, u_ca=0.002 + 0.004 * kick + 0.012 * hack + 0.02 * kick * hack)
        po["u_pump"] = (0.012 + 0.04 * hack) * kick
        po["u_flash"] = (0.05 + 0.1 * hack) * kick
        po["u_glit"] = 0.5 * hack * (0.3 + snare) * (1 if t > 36.5 else 0.0)
        shake(0.004 + 0.02 * hack)
        accent = lerp_c(PINK, CYAN, hack)
        world_props(cm, t, f, hack, objs=1.0 - 0.5 * hack, rage=0.5 * hack)
        if t >= 26.0 and t < T_PRE:
            sc["u_neon"] = 1.1
            po["u_pump"] += 0.015 * kick
        if t >= T_PRE:
            mm = sstep(ramp(t, 40.5, 46.5))
            sc.update(u_sB=2, u_aB=(0.0, 0.0, 0.0, 0.0), u_mix=0.55 * mm, u_pal=1.0)
            popups(cm, t, f, rate=0.8)
            bursts(cm, t, strength=0.7)
            if t > 45.0:
                mdiv = 1 if t < 46.0 else (2 if t < 47.0 else 4)
                po["u_flash"] = max(po["u_flash"], 0.5 * beat_flash(t, mdiv) * ramp(t, 45.0, 47.4))
                po["u_flashcol"] = mixw(CYAN, 0.55)
            g = sstep(ramp(t, 45.3, 47.9))
            if g > 0:
                skull(cm, "pre", t, f, V.cx, 780, 900, tint=(0.6, 0.9, 1.0), alpha=0.8 * g, k_amp=0.1)
            po["u_pix"] = 0.5 * max(0.0, hash01(math.floor(t * 8)) - 0.7) * hack
        if t >= T_BLACK:
            po["u_black"] = 1.0
            po["u_dot"] = sstep(ramp(t, T_BLACK, T_D1)) * 0.9
            fb["u_decay"] = 0.0
            cm = {"pre0": [], "pre": [], "mid": [], "post": []}
            cm["post"].append(("term_type", dict(t=t, t0=T_BLACK + 0.05, text="> ACCESS_GRANTED", cx=V.cx, cy=900)))
        elif t >= 47.3:
            po["u_flash"] = max(po["u_flash"], 0.7 * math.exp(-(t - 47.3) / 0.12))

    # ============================================================ DROP 1  (the hack takes over)
    elif t < T_MID:
        k_, lt = look_index(t, D1_B)
        typ = D1_TYPES[k_]
        drop_look(typ, t, lt, f, cm, sc, kal, fb, po, shake)
        accent = RED if typ == "overload" else (PINK if typ in ("tunnel", "wall") else CYAN)
        common_drop(t, lt, f, po, accent, big=1.0)
        if typ == "world":     # the bright pink world needs less light so the skull in the sun stays readable
            po["u_bloom"] *= 0.65
            po["u_flash"] *= 0.45
            po["u_expo"] = 0.82
            sc["u_neon"] = 0.75
        if t < T_D1 + 0.5:
            e = math.exp(-(t - T_D1) / 0.18)
            po["u_flash"] += 1.3 * e
            po["u_pump"] += 0.3 * e
            po["u_ca"] += 0.06 * e
            po["u_pix"] = max(po["u_pix"], 0.9 * e)

    # ============================================================ MID-SECTION (retro drive, glitching)
    elif t < T_D2:
        hk = 0.55 if t < 104.6 else lerp(0.55, 0.15, ramp(t, 104.6, 108.0))
        if t >= T_RISER:
            hk = lerp(0.15, 1.0, ramp(t, T_RISER, 117.0))
        sc["u_hack"] = hk
        sc["u_aA"] = (0.0, 1.0 if t < 104.6 else -1.0, 0.0, 0.0)
        sc["u_sun"] = 1.0 if t < 104.6 else lerp(1.0, 0.25, ramp(t, 104.6, 108.5))
        sc["u_city"] = 1.0 if t < 104.6 else lerp(1.0, 0.1, ramp(t, 104.6, 107.5))
        fb.update(u_decay=0.45, u_fzoom=1.0, u_fmix=0.6)
        po.update(u_vhs=0.4 + 0.5 * hk, u_bloom=1.0 + 0.6 * kick, u_ca=0.004 + 0.016 * kick)
        po["u_pump"] = 0.05 * kick
        po["u_flash"] = 0.15 * kick
        shake(0.012)
        accent = lerp_c(PINK, CYAN, hk)
        world_props(cm, t, f, hk, objs=1.0 if t < 104.6 else 0.3, rage=0.6 if t < 104.6 else 0.2)
        if 104.7 <= t < 107.3:   # "leave the shadows in the past": black silhouettes rush past
            for q in range(5):
                ph = (t * 0.9 + q * 0.2) % 1.0
                nm = ("car_side", "palm1", "palm3", "cactus", "palms2")[q]
                x = 1300 - ph * 1700
                cm["mid"].append(A(nm, x, 1180 + 90 * hash01(q), 520 + 160 * hash01(q + 3), alpha=0.95))
        if 107.2 < t < 112.4:
            ph = 0.0
            for te in (107.36, 109.2, 111.0):
                if te <= t < te + 0.5:
                    ph = max(ph, math.exp(-(t - te) / 0.16))
            fb.update(u_decay=0.62, u_fzoom=0.955, u_fhue=0.0)
            po["u_inv"] = 1.0 if ph > 0.75 else 0.0
            po["u_flash"] += 0.3 * ph
            po["u_pump"] += 0.06 * ph
            po["u_expo"] = 0.85
        if t >= T_RISER:
            m = ramp(t, T_RISER, 117.6)
            sc.update(u_sB=1, u_aB=(0.0, 0.0, t * 0.5, 0.0), u_mix=sstep(m) * 0.9, u_zoom=1.0 + 0.9 * m * m)
            sc["u_neon"] = 1.0 - 0.45 * m
            sc["u_sun"] = 1.0 - 0.7 * m if t >= 104.6 else sc["u_sun"] * (1.0 - 0.7 * m)
            fb.update(u_decay=0.50 + 0.2 * m, u_fzoom=1.0 + 0.03 * m, u_frot=0.012 * m)
            po["u_bloom"] = 0.9 + 0.4 * m
            po["u_expo"] = 1.0 - 0.3 * m
            po["u_glit"] = 0.1 + 0.5 * m + 0.3 * snare
            po["u_ca"] = 0.005 + 0.02 * m
            mdiv = 1 if t < 114.0 else (2 if t < 116.0 else (4 if t < 117.5 else 8))
            po["u_flash"] = 0.7 * beat_flash(t, mdiv) * ramp(t, 113.0, 114.0)
            po["u_flashcol"] = mixw(CYAN, 0.55)
            shake(0.012 + 0.012 * m)
            popups(cm, t, f, rate=0.9)
            bursts(cm, t, strength=0.8)
            g = ramp(t, 115.5, T_BLACK2)
            if g > 0:
                skull(cm, "pre", t, f, V.cx, 780, 900, tint=(0.7, 0.9, 1.0), alpha=0.5 * g, k_amp=0.12)
        if t >= T_BLACK2:
            po["u_black"] = 1.0
            po["u_dot"] = sstep(ramp(t, T_BLACK2, T_D2)) * 0.9
            fb["u_decay"] = 0.0
            cm = {"pre0": [], "pre": [], "mid": [], "post": []}
            cm["post"].append(("term_type", dict(t=t, t0=T_BLACK2 + 0.05, text="> OVERRIDE_", cx=V.cx, cy=900)))

    # ============================================================ DROP 2 (maximum overload)
    elif t < T_OUT:
        k_, lt = look_index(t, D2_B)
        typ = D2_TYPES[k_ % len(D2_TYPES)]
        drop_look(typ, t, lt, f, cm, sc, kal, fb, po, shake, seed=k_, d2=True)
        accent = (PINK, CYAN, RED, YELLOW)[k_ % 4]
        common_drop(t, lt, f, po, accent, big=1.45)
        esc = ramp(t, 139.0, 150.5)
        if esc > 0:
            if int(np.searchsorted(BEATS, t, side="right")) % 2:
                kal["u_seg"] = kal["u_seg"] * 2 if kal["u_seg"] > 1.5 else kal["u_seg"]
            po["u_glit"] += 0.25 * esc
            po["u_ca"] += 0.012 * esc
            po["u_flash"] += 0.22 * esc * hat
        if T_D2 <= t < T_D2 + 0.5:
            e = math.exp(-(t - T_D2) / 0.18)
            po["u_flash"] += 1.5 * e
            po["u_pump"] += 0.35 * e
            po["u_ca"] += 0.07 * e
            po["u_pix"] = max(po["u_pix"], 0.9 * e)
        if 135.6 <= t < 136.55:     # HOLD ON
            h = ramp(t, 135.6, 136.0)
            po["u_pump"] += 0.12 * h
            po["u_ca"] += 0.025 * h
        if 136.55 <= t < 136.9:
            po["u_flash"] += 1.2 * math.exp(-(t - 136.55) / 0.12)
            po["u_pix"] = max(po["u_pix"], 0.8 * math.exp(-(t - 136.55) / 0.1))

    # ============================================================ OUTRO (cooling, the world rebuilds)
    else:
        o = ramp(t, T_OUT, 165.0)
        hk = lerp(1.0, 0.0, sstep(o))
        sc["u_hack"] = hk
        sc["u_sun"] = lerp(0.2, 0.55, ramp(t, 156, 176))
        sc["u_aA"] = (0.0, -1.0, 0.0, 0.0)
        sc["u_city"] = lerp(0.5, 1.0, ramp(t, 156, 164))
        flick = 0.55 + 0.45 * math.sin(t * 37.0) * math.sin(t * 11.0)
        sc["u_neon"] = lerp(1.0, 0.35 + 0.35 * max(0.0, flick), ramp(t, 154, 158)) * lerp(1.0, 0.7, ramp(t, 160, 176))
        fb.update(u_decay=0.55, u_fmix=0.6)
        po.update(u_vhs=lerp(0.9, 0.25, o), u_bloom=1.0 + 0.4 * kick, u_ca=lerp(0.012, 0.002, o), u_sat=lerp(1.2, 0.95, o))
        po["u_pump"] = 0.02 * kick
        po["u_expo"] = lerp(1.0, 0.85, ramp(t, 160, 176))
        world_props(cm, t, f, hk, objs=0.7 * (1 - hk * 0.5), rage=0.3 * hk)
        accent = lerp_c(CYAN, PINK, o)
        if t < T_OUT + 8.0:      # ascii skull fades away like a dying process
            g = 1.0 - ramp(t, T_OUT + 0.3, T_OUT + 8.0)
            skull(cm, "pre", t, f, V.cx, 780, 880, tint=(0.7, 0.95, 1.0), alpha=0.9 * g, k_amp=0.1 * g)
            popups(cm, t, f, rate=0.5 * g)
        if t < T_OUT + 0.4:
            po["u_flash"] = 0.8 * math.exp(-(t - T_OUT) / 0.1)
            po["u_pix"] = 0.8 * math.exp(-(t - T_OUT) / 0.12)
        po["u_fade"] = lerp(1.0, 0.55, ramp(t, 174.0, 179.2))
        if t >= T_CRT:
            c = ramp(t, T_CRT, T_END - 0.02)
            po["u_crt"] = c
            po["u_fade"] = 1.0
            po["u_flash"] = 0.9 * math.exp(-(t - T_CRT) / 0.08)

    po["u_fade"] = po["u_fade"] * sstep(ramp(t, 0.0, 3.2))
    if t > T_END - 0.05:
        po["u_fade"] = 0.0
    sh = 0.0
    for (te, amp) in SHATTERS:
        if te <= t < te + 1.6:
            sh = max(sh, amp * math.exp(-(t - te) / 0.45))
    sc["u_shatter"] = sh
    if sh > 0.05:
        po["u_ca"] += 0.014 * sh
        po["u_flash"] += 0.15 * sh
    return dict(spec=f["spec"], scene=sc, kal=kal, fb=fb, post=po, bloom_thr=1.0, accent=accent, t=t, cmds=cm)


def lerp_c(a, b, x):
    return tuple(a[j] + (b[j] - a[j]) * x for j in range(3))


def common_drop(t, lt, f, po, accent, big=1.0):
    kick, snare, hat = f["kick"], f["snare"], f["hat"]
    po["u_bloom"] = 1.2 + 0.9 * kick
    po["u_ca"] = 0.008 + (0.026 * kick + 0.02 * snare) * big
    po["u_flash"] = (0.30 * kick ** 1.3) * big + 0.35 * math.exp(-lt / 0.08)
    po["u_flashcol"] = tuple(x * 0.7 + 0.3 for x in accent)
    po["u_inv"] = 1.0 if snare >= (0.95 if big < 1.2 else 0.85) else 0.0
    po["u_pump"] = 0.085 * kick ** 1.1 * big + 0.18 * math.exp(-lt / 0.10)
    po["u_glit"] = 0.03 + 0.30 * snare + 0.35 * math.exp(-lt / 0.12)
    po["u_vhs"] = 0.45 + 0.25 * snare
    po["u_pix"] = max(0.0, 0.85 * math.exp(-lt / 0.10))
    po["u_tilt"] = 0.03 * big * (hash01(math.floor(f["snare"] * 5) * 1.7 + math.floor(t * 4)) - 0.5) * snare
    po["u_roll"] = 0.012 * big * kick * (hash01(math.floor(t * 30)) - 0.5)
    po["u_sat"] = 1.2


def drop_look(typ, t, lt, f, cm, sc, kal, fb, po, shake, seed=0, d2=False):
    kick, snare = f["kick"], f["snare"]
    sc["u_hack"] = 1.0
    sc["u_sun"] = 1.0
    shake(0.03 if not d2 else 0.045)
    if typ == "skull":
        sc.update(u_sA=2, u_pal=1.0, u_sB=0, u_mix=0.28, u_zoom=1.0 + 0.06 * kick, u_aA=(0.0, 0.0, 0.0, 0.5))
        fb.update(u_decay=0.32, u_fzoom=1.008 + 0.01 * kick, u_frot=0.003, u_fmix=0.6)
        bursts(cm, t, 0.55)
        skull(cm, "pre", t, f, V.cx, 790, 1060, "skull_hero", tint=(1.0, 1.0, 1.0), cell=(9, 15))
        skull(cm, "pre", t, f, V.cx, 790, 1060, "skull_hero", tint=(1.0, 0.18, 0.58), cell=(9, 15), alpha=0.55 * snare, k_amp=0.3)
        popups(cm, t, f, rate=0.35)
        side_terminals(cm, t, 0.28)
        world_props(cm, t, f, 1.0, objs=0.0, rage=1.0)
    elif typ == "tunnel":
        sc.update(u_sA=1, u_aA=(0.0, 0.0, t * 0.25, 0.0), u_pal=0.0)
        fb.update(u_decay=0.45, u_fzoom=1.03 + 0.02 * kick, u_frot=0.006, u_fmix=0.6)
        tunnel_objects(cm, t, f, 12, 240, 0.33)
        bursts(cm, t, 0.8)
        popups(cm, t, f, rate=0.5)
    elif typ == "wall":
        sc.update(u_sA=3, u_pal=0.0, u_zoom=1.0 + 0.06 * kick, u_aA=(0.0, 0.0, 0.0, 0.55))
        fb.update(u_decay=0.40, u_fzoom=1.014, u_frot=0.004, u_fmix=0.6)
        wallpaper(cm, "pre", t, f, alpha=0.65, th=340, cell=(8, 13))
        bursts(cm, t, 0.6)
        skull(cm, "mid", t, f, V.cx, 800, 960, "reaper_hero2", tint=(1.0, 1.0, 1.0), cell=(10, 17), k_amp=0.16)
        popups(cm, t, f, rate=0.45)
    elif typ == "world":
        sc.update(u_sA=0, u_aA=(0.0, 1.0, 0.0, 0.0), u_zoom=1.0 + 0.12 * kick + (0.2 if d2 else 0.0))
        fb.update(u_decay=0.45, u_fzoom=1.01, u_fmix=0.6)
        world_props(cm, t, f, 1.0, objs=1.0, rage=1.0)
        skull(cm, "mid", t, f, V.cx, 730, 640, "skull_hero2", tint=(1.0, 0.72, 0.28), cell=(10, 17), k_amp=0.3)
        bursts(cm, t, 0.8)
        popups(cm, t, f, rate=0.5)
    elif typ == "overload":
        sc.update(u_sA=2, u_pal=2.0, u_sB=4, u_mix=0.3)
        fb.update(u_decay=0.55, u_fzoom=1.02 + 0.02 * kick, u_frot=0.01, u_fmix=0.6)
        po["u_flashcol"] = RED
        for q in range(9):
            r, c = divmod(q, 3)
            x = 220 + c * 320 + (hash01(q + math.floor(t * 12)) - 0.5) * 30 * kick
            y = 480 + r * 420
            on = (math.floor(t * 6) + q) % 3 != 0
            skull(cm, "pre", t, f, x, y, 360, "skull_hero" if q % 2 == 0 else "skull_hero2", tint=(1.0, 0.25, 0.3) if (q + math.floor(t * 4)) % 2 else (1.0, 1.0, 1.0),
                  cell=(8, 14), alpha=1.0 if on else 0.25, k_amp=0.18)
        bursts(cm, t, 0.7)
        popups(cm, t, f, rate=1.0)
        side_terminals(cm, t, 0.5)
    elif typ == "skullkal":
        sc.update(u_sA=4, u_pal=0.0)
        kal.update(u_seg=6.0, u_krot=t * 0.35 + 0.3 * kick, u_kzoom=1.0 + 0.08 * kick, u_kphase=0.3 * math.sin(t))
        fb.update(u_decay=0.62, u_fzoom=1.02 + 0.02 * kick, u_frot=0.012 * (1 if seed % 2 else -1), u_fmix=0.6)
        skull(cm, "pre0", t, f, V.cx + 170, 760 - 90, 600, "skull_hero", tint=(1.0, 1.0, 1.0), cell=(10, 16), k_amp=0.15)
        cm["pre0"].append(A("reaper_hero2", V.cx - 220, 900, 520, ascii_=1.0, cell=(9, 15), rot=0.4, alpha=0.9, time=t))
        bursts(cm, t, 0.7)
    elif typ == "matrix":
        sc.update(u_sA=2, u_pal=0.0, u_sB=3, u_mix=0.35)
        fb.update(u_decay=0.55, u_fzoom=1.015, u_frot=0.0, u_fmix=0.6)
        skull(cm, "mid", t, f, V.cx, 790, 760, "skull_hero", tint=(1.0, 1.0, 1.0), cell=(12, 20), alpha=0.9)
        popups(cm, t, f, rate=1.0)
        side_terminals(cm, t, 0.5)
        bursts(cm, t, 0.7)
    elif typ == "eq":
        sc.update(u_sA=3, u_pal=0.0, u_sB=2, u_mix=0.35)
        kal.update(u_seg=2.0, u_krot=t * 0.2)
        fb.update(u_decay=0.55, u_fzoom=1.02 + 0.015 * kick, u_frot=0.008, u_fmix=0.6)
        skull(cm, "mid", t, f, V.cx, 790, 700, "skull_hero2", tint=(0.6, 1.0, 1.0), cell=(11, 18))
        bursts(cm, t, 0.8)
    elif typ == "skullgrid":
        sc.update(u_sA=2, u_pal=1.0, u_sB=4, u_mix=0.3)
        fb.update(u_decay=0.5, u_fzoom=1.02, u_fmix=0.6)
        for q in range(9):
            r, c = divmod(q, 3)
            x = 200 + c * 340
            y = 420 + r * 440
            on = (math.floor(t * 8) + q * 2) % 4 != 0
            skull(cm, "pre", t, f, x, y, 400, "skull_hero" if q % 3 else "skull_hero2",
                  tint=(1.0, 0.18, 0.58) if (q + math.floor(t * 5)) % 2 else (0.0, 0.9, 1.0), cell=(8, 14),
                  alpha=1.0 if on else 0.2, k_amp=0.2)
        bursts(cm, t, 0.7)
    elif typ == "objkal":
        sc.update(u_sA=4, u_pal=0.0)
        kal.update(u_seg=8.0, u_krot=-t * 0.3 + 0.3 * kick, u_kzoom=1.0 + 0.1 * kick)
        fb.update(u_decay=0.6, u_fzoom=1.022, u_frot=-0.01, u_fmix=0.6)
        for q, nm in enumerate(("vhs", "cassette", "crt", "boombox", "headphones", "bust")):
            ang = q * 1.047 + t * 0.4
            cm["pre0"].append(A(nm, V.cx + math.cos(ang) * 260, 760 + math.sin(ang) * 260, 260 * (1 + 0.25 * kick), rot=ang * 0.5))
        bursts(cm, t, 0.6)
    elif typ == "hacker":
        sc.update(u_sA=2, u_pal=1.0, u_sB=3, u_mix=0.3)
        fb.update(u_decay=0.55, u_fzoom=1.018, u_frot=0.005, u_fmix=0.6)
        skull(cm, "pre", t, f, V.cx, 840, 1100, "hacker", tint=(1.0, 1.0, 1.0), cell=(12, 20), k_amp=0.16)
        cm["mid"].append(A("eye_a", V.cx, 560, 240 * (1 + 0.3 * kick), alpha=0.9, ascii_=0.0, add=True))
        popups(cm, t, f, rate=1.0)
        bursts(cm, t, 0.7)
    else:
        sc.update(u_sA=4)
