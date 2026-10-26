"""Choreography v3: spatial synthwave world that gets eaten by ASCII code (hack), spin-blur camera, bass-wub flicker."""
import bisect
import math

import numpy as np

from .choreo2 import (cl, ramp, sstep, lerp, hash01, PINK, CYAN, VIOLET, ORANGE, YELLOW, RED, F, BEATS, KICK_T, KICK_S,
                           POPUP_T, A, beat_flash, look_index, lerp_c, CHOPS, SHATTERS, CAPTIONS, popups,
                           T_INTRO_B, T_PRE, T_BLACK, T_D1, T_MID, T_RISER, T_BLACK2, T_D2, T_OUT, T_END, T_CRT)
from .features import FPS
from .canvas import V
from . import typelayer as TL

# ------------------------------------------------------------------ looks timeline
_d1 = [T_D1 + k * (T_MID - T_D1) / 10.0 for k in range(11)]
D1_B = [_d1[0]] + [F.nearest_beat(x) for x in _d1[1:-1]] + [_d1[-1]]
D1_LOOKS = ["access", "reaper_eq", "spin_warp", "skull_turn", "drive", "eq_wall", "sun_skull", "flood", "overload", "collapse"]
_d2 = np.arange(T_D2, T_OUT, 8 / 3.0)
D2_B = [T_D2] + [F.nearest_beat(x) for x in _d2[1:]] + [T_OUT]
D2_LOOKS = ["override", "override", "spin_warp", "glass", "dancer_ascii", "drive", "skull_turn", "dancer_glitch", "overload",
            "dancer_ascii2", "eq_wall", "skullkal", "collapse"]
SPEEDS = dict(access=8.0, reaper_eq=3.0, spin_warp=14.0, skull_turn=6.0, drive=12.0, eq_wall=5.0, sun_skull=7.0, flood=6.0,
              overload=16.0, collapse=18.0, skullkal=8.0, skullgrid=6.0, hacker=6.0, override=14.0, glass=3.0, dancer_ascii=8.0,
              dancer_glitch=10.0, dancer_ascii2=8.0)


def speed(t):
    if t < T_INTRO_B:
        return lerp(0.7, 1.3, ramp(t, 3, T_INTRO_B))
    if t < 26.0:
        return 1.3
    if t < T_PRE:
        return lerp(1.3, 2.4, ramp(t, 26, 36))
    if t < 43.0:
        return lerp(2.4, 4.5, ramp(t, T_PRE, 43))
    if t < 47.3:
        return lerp(4.5, 13.0, ramp(t, 43, 47.3))
    if t < T_D1:
        return 10.0
    if t < T_MID:
        k, _ = look_index(t, D1_B)
        return SPEEDS[D1_LOOKS[k]]
    if t < T_RISER:
        if t < 103.4:
            return 2.5
        if t < 104.0:
            return lerp(2.5, 11.0, ramp(t, 103.4, 104.0))
        return lerp(11.0, 3.0, ramp(t, 104.0, 108.0))
    if t < T_D2:
        return lerp(3.0, 18.0, ramp(t, T_RISER, T_BLACK2))
    if t < T_OUT:
        if 135.6 < t < 136.5:
            return 0.2
        k, _ = look_index(t, D2_B)
        return SPEEDS[D2_LOOKS[k % len(D2_LOOKS)]] * 1.1
    if t < 157.0:
        return lerp(5.0, 0.6, ramp(t, T_OUT, 157.0))
    return lerp(0.6, 0.25, ramp(t, 157.0, 178.0))


N_FRAMES = int(round(T_END * FPS))
DIST = np.cumsum([speed(i / FPS) / FPS for i in range(N_FRAMES + 1)])


def wdir(t):
    """travel direction of the retro world (+1 = driving towards the camera, -1 = receding). Integrated with the speed -> smooth reversal."""
    if t < 41.0:
        return -1.0
    if t < 45.0:
        return lerp(-1.0, 1.0, sstep(ramp(t, 41.0, 45.0)))
    if t < 104.4:
        return 1.0
    if t < 105.6:
        return lerp(1.0, -1.0, sstep(ramp(t, 104.4, 105.6)))
    if t < T_D2:
        return -1.0
    if t < T_OUT:
        return 1.0
    return -1.0


WDIST = np.cumsum([speed(i / FPS) * wdir(i / FPS) / FPS for i in range(N_FRAMES + 1)])
GT = np.cumsum([(0.5 + 1.3 * float(F.kick[min(i, F.n - 1)]) + 0.7 * float(F.bass_s[min(i, F.n - 1)])) / FPS for i in range(N_FRAMES + 1)])
_strong = [float(t) for t, s in zip(KICK_T, KICK_S) if s >= 0.55]


def kt_since(t):
    j = bisect.bisect_right(_strong, t) - 1
    return (t - _strong[j]) if j >= 0 else 9.0


def bar_snap(t):
    """angle that steps by 90 degrees on the last beat of every bar (camera snaps)"""
    j = int(np.searchsorted(BEATS, t, side="right")) - 1
    j = min(max(j, 0), len(BEATS) - 2)
    frac = (t - BEATS[j]) / (BEATS[j + 1] - BEATS[j])
    bar, pos = divmod(j, 4)
    prog = (pos + frac) / 4.0
    return (math.pi / 2.0) * (bar + sstep(ramp(prog, 0.78, 1.0)))


# ------------------------------------------------------------------ state containers
def _lerp_arr(arr, t):
    x = t * FPS
    i = int(x)
    i = min(max(i, 0), len(arr) - 2)
    return float(arr[i] + (x - i) * (arr[i + 1] - arr[i]))


def new_state(i, f, t):
    kick, snare, hat, bass_s = f["kick"], f["snare"], f["hat"], f["bass_s"]
    dist = _lerp_arr(DIST, t)
    sc = dict(u_t=t, u_dist=dist, u_bass=f["bass_s"], u_lowmid=f["lowmid"], u_mid=f["mid"], u_high=f["high"], u_rms=f["rms_s"],
              u_kick=kick, u_snare=snare, u_hat=hat, u_wob=bass_s, u_pal=0.0, u_shatter=0.0, u_city=1.0, u_neon=1.0, u_sun=1.0, u_moon=0.0, u_night=0.0, u_dusk=0.0, u_car=(0.0, 1.0, 0.0), u_car2=(0.0, 1.0, 0.0),
              u_hack=0.0, u_zoom=1.0, u_dim=1.0, u_wdist=_lerp_arr(WDIST, t), u_gt=_lerp_arr(GT, t), u_shB=0.0, u_sA=0, u_sB=0, u_mix=0.0, u_aA=(0.0, -1.0, 0.0, 0.0), u_aB=(0.0, 0.0, 0.0, 0.0))
    kal = dict(u_seg=1.0, u_krot=0.0, u_kzoom=1.0, u_kphase=0.0, u_mirx=0.0, u_mirror_y=0.0, u_kc=(0.0, 0.0), u_roll=0.0,
               u_blr=0.0, u_blz=0.0, u_fov=0.0)
    fb = dict(u_decay=0.0, u_fzoom=1.0, u_frot=0.0, u_fhue=0.0, u_fmix=0.5, u_fshift=(0.0, 0.0))
    po = dict(u_t=t, u_bloom=0.9, u_ca=0.002, u_glit=0.0, u_flash=0.0, u_flashcol=(1.0, 1.0, 1.0), u_inv=0.0, u_black=0.0,
              u_fade=1.0, u_scan=0.08, u_grain=0.03, u_vig=0.5, u_pump=0.0, u_crt=0.0, u_dot=0.0, u_expo=1.0, u_sat=1.12,
              u_shake=(0.0, 0.0), u_vhs=0.18, u_pix=0.0, u_roll=0.0, u_tilt=0.0, u_caosc=0.0, u_glit2=0.0)
    asc = dict(u_t=t, u_amt=0.0, u_cell=12.0, u_melt=0.0, u_cm=0.0, u_jit=0.3, u_bright=1.0, u_kt=kt_since(t), u_ringw=0.05,
               u_flick=0.0, u_dir=1.0, u_acol=(0.55, 1.0, 1.0), u_blob=0.8, ring_on=False)
    cm = {"pre0": [], "pre": [], "mid": [], "post": []}
    spd = abs(speed(t))
    kal["u_fov"] = 0.9 * cl((spd - 1.0) / 13.0) + 0.10 * kick * cl((spd - 2.0) / 6.0)       # wide-angle edge stretch with speed
    kal["u_blz"] = 0.05 * cl((spd - 4.0) / 10.0)                                              # + radial zoom blur
    wub = cl((f["bass"] - 0.5) * 2.2)
    return dict(t=t, i=i, f=f, kick=kick, snare=snare, hat=hat, bass_s=bass_s, wub=wub, sc=sc, kal=kal, fb=fb, po=po, asc=asc, cm=cm)


def shake(X, amp):
    k, i = X["kick"], X["i"]
    X["po"]["u_shake"] = (amp * k * (hash01(i * 1.3) - 0.5), amp * k * (hash01(i * 2.7) - 0.5))


def reaper(X, alpha, dis, h=1500, cy=930, name="reaper_hero", tint=(1, 1, 1), sx=1.0):
    k = X["kick"]
    X["cm"]["mid"].append(A(name, V.cx, cy, h * (1.0 + 0.10 * k ** 1.1), alpha=alpha, dissolve=dis, dsz=14, tint=tint, time=X["t"],
                            split=0.004 + 0.01 * X["snare"], sx=sx))


def skull_sprite(X, hook, cx, cy, h, name="skull_hero", tint=(1, 1, 1), alpha=1.0, sx=1.0, k_amp=0.18, dis=0.0):
    k = X["kick"]
    t = X["t"]
    X["cm"][hook].append(A(name, cx + (hash01(math.floor(t * 30) * 1.7) - 0.5) * 22 * k, cy, h * (1.0 + k_amp * k ** 1.1), alpha=alpha,
                           tint=tint, sx=sx, dissolve=dis, dsz=12, time=t, split=0.004 + 0.012 * X["snare"]))


def wall(X, alpha=0.5, th=340):
    t, sn = X["t"], X["snare"]
    scroll = (t * 80.0) % (th * 0.8)
    cw = th * 0.62
    for j in range(int(1920 / th) + 3):
        for i in range(int(V.w / cw) + 2):
            x = i * cw + (cw * 0.5 if j % 2 else 0) - cw * 0.5
            y = j * th * 0.8 - scroll
            fl = hash01(i * 7.7 + j * 3.1 + math.floor(t * 6))
            X["cm"]["pre"].append(A("reaper_hero", x, y, th, alpha=min(alpha * (0.4 + 0.6 * (fl > 0.5)) * (0.7 + 0.8 * sn), 1.0),
                                    flip=bool((i + j) % 2), time=t, tint=(0.9, 1.0, 1.1), ascii_=0.0))


def bigtext(X, lines, t0, t1, color=(255, 40, 70), cy=830, size_cap=380, label=None):
    p = dict(lines=lines, t0=t0, t1=t1, color=color, cy=cy, cap=size_cap, kick=X["kick"], snare=X["snare"])
    if label:
        p["label"] = label
    X["cm"]["post"].append(("bigtext", p))


def popups3(X, rate=1.0):
    """error windows go on the crisp text layer (not turned into ASCII)"""
    tmp = {"mid": []}
    popups(tmp, X["t"], X["f"], rate=rate)
    X["cm"]["post"].extend(tmp["mid"])


# ------------------------------------------------------------------ the looks
def drop_common(X, big=1.0, accent=CYAN):
    t, lt, f = X["t"], X["lt"], X["f"]
    k, s, h, wub = X["kick"], X["snare"], X["hat"], X["wub"]
    po, asc, kal = X["po"], X["asc"], X["kal"]
    po["u_bloom"] = 1.1 + 0.8 * k
    po["u_ca"] = 0.004 + (0.010 * k + 0.008 * s) * big
    po["u_caosc"] = 0.35 * big
    po["u_scan"] = 0.04
    po["u_flash"] = 0.22 * k ** 1.3 * big + 0.35 * math.exp(-lt / 0.08)
    po["u_flashcol"] = tuple(x * 0.7 + 0.3 for x in accent)
    po["u_inv"] = 1.0 if s >= (0.95 if big < 1.2 else 0.85) else 0.0
    po["u_pump"] = 0.075 * k ** 1.1 * big + 0.16 * math.exp(-lt / 0.10)
    po["u_glit"] = 0.02 + 0.22 * s + 0.30 * math.exp(-lt / 0.12)
    po["u_glit2"] = (0.12 + 0.30 * s) * big
    po["u_vhs"] = 0.3 + 0.2 * s
    po["u_pix"] = max(0.0, 0.8 * math.exp(-lt / 0.10))
    po["u_expo"] = 0.80 + 0.55 * wub          # bass wubb flicker
    po["u_tilt"] = 0.02 * big * (hash01(math.floor(t * 4) * 1.7) - 0.5) * s
    po["u_roll"] = 0.010 * big * k * (hash01(math.floor(t * 30)) - 0.5)
    po["u_sat"] = 1.2
    asc["u_kt"] = X["asc"]["u_kt"]
    asc["ring_on"] = asc["u_kt"] < 0.75
    asc["u_cell"] = max(asc["u_cell"], 11.0) * 1.25 * (1.0 + 0.30 * wub)
    asc["u_flick"] = 0.35 * s
    shake(X, 0.03 * big)
    kal["u_kzoom"] *= 1.0 + 0.06 * k * big


def look_access(X):
    """THE drop: the world falls apart into falling code, ACCESS GRANTED screams in red, a reaper emerges from the melted characters"""
    t, lt, k = X["t"], X["lt"], X["kick"]
    sc, asc, kal, fb = X["sc"], X["asc"], X["kal"], X["fb"]
    # the world melts away while a terminal equalizer rises underneath it (both end up as code)
    sc.update(u_sA=0, u_hack=1.0, u_sun=1.0, u_aA=(0.0, 1.0, 0.0, 0.0), u_sB=5, u_mix=sstep(ramp(lt, 0.5, 2.0)), u_pal=1.0)
    sc["u_dim"] = lerp(1.0, 0.75, sstep(ramp(lt, 0.2, 1.8)))
    asc.update(u_amt=sstep(ramp(lt, 0.0, 0.8)), u_melt=5.0 * math.exp(-lt / 1.6) + 0.45 + 0.25 * math.sin(t * 2), u_cm=sstep(ramp(lt, 0.2, 2.0)) * 0.9,
               u_cell=16.0, u_acol=(0.65, 1.0, 1.0), u_jit=0.25)
    kal.update(u_roll=0.04 * math.sin(t * 1.3) + 0.35 * math.exp(-lt / 0.5), u_kzoom=1.0 + 0.5 * math.exp(-lt / 0.35))
    fb.update(u_decay=0.45, u_fzoom=1.01, u_fmix=0.6)
    shown = lt < 4.4
    if shown:
        a = 1.0 if lt < 3.8 else 1.0 - ramp(lt, 3.8, 4.4)
        pass                                        # the ACCESS GRANTED block comes from TL.BLOCKS (see frame_state)
    g = sstep(ramp(lt, 0.9, 3.8))
    reaper(X, alpha=0.98 * g, dis=1.0 - sstep(ramp(lt, 0.9, 3.6)), h=1500, cy=930, tint=(1.35, 1.35, 1.35))
    X["acc"] = RED


def look_reaper_eq(X):
    t, lt, k = X["t"], X["lt"], X["kick"]
    sc, asc, kal, fb = X["sc"], X["asc"], X["kal"], X["fb"]
    sc.update(u_sA=5, u_pal=1.0, u_hack=1.0, u_sB=2, u_mix=0.22, u_aB=(0.0, 0.0, 0.0, 0.5), u_dim=0.7)
    asc.update(u_amt=1.0, u_cm=0.55, u_cell=12.0, u_melt=0.12, u_acol=(0.7, 1.0, 1.0))
    kal.update(u_roll=0.14 * math.sin(t * 0.8), u_blr=0.02, u_kzoom=1.0)
    fb.update(u_decay=0.35, u_fzoom=1.006, u_fmix=0.6)
    reaper(X, alpha=0.95, dis=0.0, h=1500 * (1.0 + 0.05 * math.sin(t * 2)), cy=930)
    X["acc"] = CYAN


def look_spin_warp(X):
    t, lt, k = X["t"], X["lt"], X["kick"]
    sc, asc, kal, fb = X["sc"], X["asc"], X["kal"], X["fb"]
    sc.update(u_sA=1, u_aA=(0.0, 0.0, t * 0.3, 0.0), u_pal=0.0, u_sB=6, u_mix=0.45, u_hack=1.0)
    asc.update(u_amt=0.22, u_cm=0.0, u_cell=14.0, u_melt=0.0, u_jit=0.3)
    spin = 2.6 + 1.2 * k
    kal.update(u_roll=t * spin, u_blr=0.22, u_blz=0.04 + 0.1 * k, u_kzoom=1.0 + 0.08 * k)
    fb.update(u_decay=0.35, u_fzoom=1.02, u_fmix=0.6)
    X["acc"] = PINK


def look_skull_turn(X):
    t, lt, k = X["t"], X["lt"], X["kick"]
    sc, asc, kal, fb = X["sc"], X["asc"], X["kal"], X["fb"]
    sc.update(u_sA=2, u_pal=1.0, u_aA=(0.0, 0.0, 0.0, 0.55), u_hack=1.0, u_sB=0, u_mix=0.2)
    asc.update(u_amt=0.78, u_cm=0.7, u_cell=11.0, u_melt=0.25, u_acol=(0.8, 1.0, 1.0))
    kal.update(u_roll=0.05 * math.sin(t), u_kzoom=1.0 + 0.04 * lt / 5.0)
    fb.update(u_decay=0.3, u_fzoom=1.008, u_fmix=0.6)
    turn = math.cos(t * 2.1)
    skull_sprite(X, "mid", V.cx, 880, 1150, "skull_hero", tint=(1.0, 1.0, 1.0) if turn > 0 else (0.6, 0.8, 1.0), sx=turn, k_amp=0.12)
    X["acc"] = CYAN


def look_drive(X):
    t, lt, k = X["t"], X["lt"], X["kick"]
    sc, asc, kal, fb = X["sc"], X["asc"], X["kal"], X["fb"]
    sc.update(u_sA=0, u_hack=0.75, u_sun=1.0, u_aA=(0.0, 1.0, 0.0, 0.0), u_neon=0.9)
    asc.update(u_amt=0.28, u_cm=0.0, u_cell=10.0, u_jit=0.5)
    kal.update(u_roll=0.30 * math.sin(t * 1.7) + bar_snap(t) * 0.0, u_blr=0.06, u_blz=0.05 + 0.08 * k, u_kzoom=1.0 + 0.10 * k)
    fb.update(u_decay=0.4, u_fzoom=1.012, u_fmix=0.6)
    X["acc"] = PINK


def look_eq_wall(X):
    t, lt, k = X["t"], X["lt"], X["kick"]
    sc, asc, kal, fb = X["sc"], X["asc"], X["kal"], X["fb"]
    sc.update(u_sA=3, u_pal=0.0, u_aA=(0.0, 0.0, 0.0, 0.6), u_hack=1.0, u_dim=0.8)
    asc.update(u_amt=0.55, u_cm=0.3, u_cell=11.0, u_melt=0.1)
    kal.update(u_roll=-t * 0.5, u_blr=0.04, u_kzoom=1.0 + 0.05 * k)
    fb.update(u_decay=0.4, u_fzoom=1.012, u_fmix=0.6)
    wall(X, alpha=0.55)
    X["acc"] = PINK


def look_sun_skull(X):
    t, lt, k = X["t"], X["lt"], X["kick"]
    sc, asc, kal, fb = X["sc"], X["asc"], X["kal"], X["fb"]
    sc.update(u_sA=0, u_hack=0.6, u_sun=1.0, u_aA=(0.0, 1.0, 0.0, 0.0), u_neon=0.8)
    asc.update(u_amt=0.5, u_cm=0.0, u_cell=10.0, u_melt=0.3)
    kal.update(u_roll=0.05 * math.sin(t * 2.0), u_kzoom=1.0 + 0.14 * k, u_blz=0.04)
    fb.update(u_decay=0.4, u_fzoom=1.01, u_fmix=0.6)
    skull_sprite(X, "mid", V.cx, 740, 760, "skull_hero2", tint=(1.0, 0.75, 0.3), k_amp=0.25)
    X["acc"] = ORANGE


def look_flood(X):
    t, lt, k = X["t"], X["lt"], X["kick"]
    sc, asc, kal, fb = X["sc"], X["asc"], X["kal"], X["fb"]
    sc.update(u_sA=2, u_pal=2.0, u_sB=4, u_mix=0.25, u_hack=1.0)
    asc.update(u_amt=1.0, u_cm=0.8, u_cell=14.0, u_melt=1.3, u_acol=(1.0, 0.22, 0.30), u_jit=0.7)
    kal.update(u_roll=0.10 * math.sin(t * 3.0), u_kzoom=1.0 + 0.05 * k)
    fb.update(u_decay=0.4, u_fzoom=1.01, u_fmix=0.6)
    X["po"]["u_flashcol"] = RED
    skull_sprite(X, "mid", V.cx, 880, 1000, "skull_hero", tint=(1.0, 0.45, 0.5), alpha=0.9, k_amp=0.2)
    X["acc"] = RED


def look_overload(X):
    t, lt, k, s = X["t"], X["lt"], X["kick"], X["snare"]
    sc, asc, kal, fb = X["sc"], X["asc"], X["kal"], X["fb"]
    sc.update(u_sA=6, u_pal=2.0, u_sB=3, u_aB=(0.0, 0.0, 0.0, 0.5), u_mix=0.4, u_hack=1.0)
    asc.update(u_amt=0.6, u_cm=0.5, u_cell=12.0, u_melt=0.4, u_acol=(1.0, 0.3, 0.35), u_jit=0.6)
    kal.update(u_roll=t * 3.4, u_blr=0.26, u_blz=0.05, u_kzoom=1.0 + 0.08 * k)
    fb.update(u_decay=0.45, u_fzoom=1.02, u_fmix=0.6)
    X["po"]["u_flashcol"] = RED
    skull_sprite(X, "mid", V.cx, 840, 1100, "skull_hero", tint=(1.0, 0.35, 0.4) if math.floor(t * 8) % 2 else (1.0, 1.0, 1.0), k_amp=0.3)
    popups3(X, 1.0)
    X["acc"] = RED


def look_collapse(X):
    t, lt, k = X["t"], X["lt"], X["kick"]
    sc, asc, kal, fb = X["sc"], X["asc"], X["kal"], X["fb"]
    sc.update(u_sA=1, u_aA=(0.0, 0.0, t * 0.4, 0.0), u_pal=0.0, u_hack=1.0, u_sB=6, u_mix=0.5)
    p = X["look_u"]
    asc.update(u_amt=0.4 + 0.6 * p, u_cm=0.4 * p, u_cell=12.0, u_melt=0.2 + 2.2 * p * p)
    kal.update(u_roll=t * (2.0 + 2.0 * p), u_blr=0.15 + 0.15 * p, u_blz=0.06, u_kzoom=1.0 + 0.1 * k)
    fb.update(u_decay=0.5, u_fzoom=1.025, u_fmix=0.6)
    X["acc"] = PINK


def look_skullkal(X):
    t, lt, k = X["t"], X["lt"], X["kick"]
    sc, asc, kal, fb = X["sc"], X["asc"], X["kal"], X["fb"]
    sc.update(u_sA=4, u_pal=0.0, u_hack=1.0)
    asc.update(u_amt=0.55, u_cm=0.6, u_cell=11.0, u_melt=0.2)
    kal.update(u_seg=6.0, u_krot=t * 0.4 + 0.3 * k, u_roll=-t * 0.8, u_blr=0.1, u_kzoom=1.0 + 0.08 * k, u_kphase=0.3 * math.sin(t))
    fb.update(u_decay=0.55, u_fzoom=1.02 + 0.02 * k, u_frot=0.012, u_fmix=0.6)
    skull_sprite(X, "pre0", V.cx + 170, 760 - 90, 640, "skull_hero", k_amp=0.12)
    X["cm"]["pre0"].append(A("reaper_hero2", V.cx - 220, 900, 560, rot=0.4, alpha=0.9, time=t))
    X["acc"] = CYAN


def look_skullgrid(X):
    t, lt, k = X["t"], X["lt"], X["kick"]
    sc, asc, kal, fb = X["sc"], X["asc"], X["kal"], X["fb"]
    sc.update(u_sA=2, u_pal=1.0, u_sB=4, u_mix=0.3, u_hack=1.0)
    asc.update(u_amt=0.8, u_cm=0.6, u_cell=9.0, u_melt=0.4)
    kal.update(u_roll=0.2 * math.sin(t * 2.3), u_kzoom=1.0 + 0.06 * k)
    fb.update(u_decay=0.45, u_fzoom=1.02, u_fmix=0.6)
    for q in range(9):
        r, c = divmod(q, 3)
        on = (math.floor(t * 8) + q * 2) % 4 != 0
        skull_sprite(X, "mid", 200 + c * 340, 420 + r * 440, 400, "skull_hero" if q % 3 else "skull_hero2",
                     tint=(1.0, 0.18, 0.58) if (q + math.floor(t * 5)) % 2 else (0.0, 0.9, 1.0), alpha=1.0 if on else 0.2, k_amp=0.2)
    X["acc"] = PINK


def look_hacker(X):
    t, lt, k = X["t"], X["lt"], X["kick"]
    sc, asc, kal, fb = X["sc"], X["asc"], X["kal"], X["fb"]
    sc.update(u_sA=2, u_pal=1.0, u_sB=5, u_mix=0.3, u_hack=1.0)
    asc.update(u_amt=0.7, u_cm=0.6, u_cell=10.0, u_melt=0.5)
    kal.update(u_roll=0.08 * math.sin(t * 2.0), u_kzoom=1.0 + 0.08 * k)
    fb.update(u_decay=0.45, u_fzoom=1.018, u_fmix=0.6)
    skull_sprite(X, "mid", V.cx, 860, 1150, "hacker", k_amp=0.16)
    popups3(X, 1.0)
    X["acc"] = CYAN


def vid_idx(X, rate=1.0, hold_beat=True):
    t, k = X["t"], X["kick"]
    n = 120
    i = int(t * 24.0 * rate + 5.0 * k) % (2 * n)
    return i if i < n else 2 * n - 1 - i


def video(X, hook, name, cx, cy, h, **kw):
    X["cm"][hook].append(("video", dict(name=name, idx=vid_idx(X), cx=cx, cy=cy, height=h * (1.0 + 0.07 * X["kick"] ** 1.1), time=X["t"], **kw)))


def look_override(X):
    """DROP 2 opening, the same beat structure as the first drop: world -> code, huge vibrating text, a dancing skeleton emerges from the melted characters"""
    t, k = X["t"], X["kick"]
    lt = t - T_D2
    sc, asc, kal, fb = X["sc"], X["asc"], X["kal"], X["fb"]
    sc.update(u_sA=0, u_hack=1.0, u_sun=1.0, u_sB=5, u_mix=sstep(ramp(lt, 0.5, 2.0)), u_pal=1.0, u_dim=lerp(1.0, 0.7, sstep(ramp(lt, 0.2, 1.8))))
    asc.update(u_amt=lerp(sstep(ramp(lt, 0.0, 0.7)), 0.7, ramp(lt, 5.0, 7.0)), u_melt=5.0 * math.exp(-lt / 1.6) + 0.45 + 0.25 * math.sin(t * 2),
               u_cm=sstep(ramp(lt, 0.2, 2.0)) * 0.9, u_cell=16.0, u_acol=(0.6, 1.0, 1.0), u_jit=0.25)
    kal.update(u_roll=0.35 * math.exp(-lt / 0.5) + 0.3 * math.sin(t * 1.9) * ramp(lt, 3.0, 5.0) + t * 0.8 * ramp(lt, 4.5, 6.0),
               u_kzoom=1.0 + 0.5 * math.exp(-lt / 0.35), u_blr=0.12 * ramp(lt, 4.5, 6.0))
    fb.update(u_decay=0.45, u_fzoom=1.01, u_fmix=0.6)
    if lt < 4.4:
        pass                                        # the SYSTEM OVERRIDE block comes from TL.BLOCKS (see frame_state)
    g = sstep(ramp(lt, 0.9, 3.8))
    video(X, "mid", "dance_skel", V.cx, 960, 1750, alpha=0.98 * g, dissolve=1.0 - sstep(ramp(lt, 0.9, 3.6)), tint=(1.2, 1.3, 1.45), dsz=14, split=0.004 + 0.01 * X["snare"])
    X["acc"] = CYAN


def look_glass(X):
    """pristine crystal glass cathedral (raymarched) that shatters on 'GLASS!'"""
    t, k = X["t"], X["kick"]
    lt = X["lt"]
    sc, asc, kal, fb = X["sc"], X["asc"], X["kal"], X["fb"]
    brk = 128.28
    sc.update(u_sA=7, u_pal=0.0, u_aA=(sc["u_gt"], -1.1 * k, 0.0, 0.06 * k), u_hack=0.8, u_sB=0, u_mix=sstep(ramp(t, brk, brk + 0.7)), u_shB=1.0)
    X["po"].update(u_glit2=0.0, u_glit=0.0, u_vhs=0.12, u_caosc=0.0)
    asc.update(u_amt=0.0)
    kal.update(u_roll=0.06 * math.sin(t * 1.2) + 0.08 * k * (hash01(math.floor(t * 20)) - 0.5), u_kzoom=1.0 + 0.10 * k)
    fb.update(u_decay=0.18, u_fzoom=1.0, u_fmix=0.6)
    X["acc"] = CYAN


def look_dancer_ascii(X):
    """six-way kaleidoscope of the dancing skeleton, turned into code"""
    t, k = X["t"], X["kick"]
    sc, asc, kal, fb = X["sc"], X["asc"], X["kal"], X["fb"]
    sc.update(u_sA=3, u_pal=0.0, u_aA=(0.0, 0.0, 0.0, 0.5), u_hack=1.0, u_dim=0.5, u_sB=2, u_mix=0.3)
    asc.update(u_amt=0.7, u_cm=0.4, u_cell=11.0, u_melt=0.15, u_jit=0.2)
    kal.update(u_seg=6.0, u_krot=t * 0.4 + 0.3 * k, u_roll=0.1 * math.sin(t * 1.4), u_blr=0.05, u_kzoom=1.0 + 0.08 * k, u_kphase=0.3 * math.sin(t))
    fb.update(u_decay=0.5, u_fzoom=1.02, u_frot=0.01, u_fmix=0.6)
    video(X, "pre0", "dance_skel", V.cx + 130, 880, 1100, tint=(1.3, 1.4, 1.5), alpha=1.0)
    X["acc"] = PINK


def look_dancer_glitch(X):
    """the hooded dancer, tripled and sliced, in a hyperspace warp"""
    t, k, s = X["t"], X["kick"], X["snare"]
    sc, asc, kal, fb = X["sc"], X["asc"], X["kal"], X["fb"]
    sc.update(u_sA=6, u_pal=2.0, u_sB=1, u_aB=(0.0, 0.0, t * 0.3, 0.0), u_mix=0.4, u_hack=1.0)
    asc.update(u_amt=0.45, u_cm=0.2, u_cell=10.0, u_melt=0.3, u_jit=0.3, u_acol=(1.0, 0.4, 0.8))
    kal.update(u_roll=t * 0.6 + 0.2 * math.sin(t * 3), u_blr=0.10, u_kzoom=1.0 + 0.10 * k)
    fb.update(u_decay=0.45, u_fzoom=1.02, u_fmix=0.6)
    kw = dict(gamma=0.55, gain=3.8)
    video(X, "mid", "dance_hood", V.cx, 960, 1800, tint=(1.4, 1.4, 1.5), alpha=1.0, slice_=0.07 * s, split=0.006 + 0.02 * k, **kw)
    for sgn, col in ((-1, (1.0, 0.25, 0.7)), (1, (0.2, 0.9, 1.0))):
        video(X, "mid", "dance_hood", V.cx + sgn * (200 + 120 * k), 960, 1700, tint=col, alpha=0.7, add=True, slice_=0.1 * s,
              dissolve=0.25 * (hash01(math.floor(t * 8) + sgn) > 0.6), dsz=12, **kw)
    X["acc"] = PINK


def look_dancer_ascii2(X):
    """mirrored skeleton twins stomping to the kick, pure code"""
    t, k = X["t"], X["kick"]
    sc, asc, kal, fb = X["sc"], X["asc"], X["kal"], X["fb"]
    sc.update(u_sA=1, u_aA=(0.0, 0.0, t * 0.35, 0.0), u_pal=0.0, u_hack=1.0, u_sB=5, u_mix=0.35, u_dim=0.7)
    asc.update(u_amt=0.65, u_cm=0.5, u_cell=10.0, u_melt=0.25, u_jit=0.2, u_acol=(0.7, 1.0, 1.0))
    kal.update(u_roll=0.15 * math.sin(t * 2.2), u_kzoom=1.0 + 0.1 * k, u_blr=0.03)
    fb.update(u_decay=0.4, u_fzoom=1.015, u_fmix=0.6)
    for sgn in (-1, 1):
        video(X, "mid", "dance_skel", V.cx + sgn * 250, 960, 1500, tint=(1.3, 1.4, 1.5), flip=(sgn > 0), alpha=1.0, ascii_=0.0)
    X["acc"] = CYAN


LOOKS = dict(access=look_access, reaper_eq=look_reaper_eq, spin_warp=look_spin_warp, skull_turn=look_skull_turn, drive=look_drive,
             eq_wall=look_eq_wall, sun_skull=look_sun_skull, flood=look_flood, overload=look_overload, collapse=look_collapse, override=look_override, glass=look_glass, dancer_ascii=look_dancer_ascii,
             dancer_glitch=look_dancer_glitch, dancer_ascii2=look_dancer_ascii2,
             skullkal=look_skullkal, skullgrid=look_skullgrid, hacker=look_hacker)


def lerp_acc(a, b, x):
    return lerp_c(a, b, x)


# ------------------------------------------------------------------ the frame
def frame_state(i, t=None):
    if t is None:
        t = i / FPS
    f = F.at(i)
    X = new_state(i, f, t)
    sc, kal, fb, po, asc, cm = X["sc"], X["kal"], X["fb"], X["po"], X["asc"], X["cm"]
    kick, snare, hat, bass_s, wub = X["kick"], X["snare"], X["hat"], X["bass_s"], X["wub"]
    accent = CYAN

    # ============================================================ INTRO / VERSES / PRE-CHORUS : a clean 3D synthwave drive that starts to rot
    if t < T_D1:
        sc["u_sun"] = sstep(ramp(t, 0.5, 14.0))
        hack = 0.12 * ramp(t, 28.0, T_PRE) + 0.88 * sstep(ramp(t, T_PRE, 47.0))
        sc["u_hack"] = hack
        sc["u_aA"] = (0.0, 1.0, 0.0, 0.0)
        # camera: slow sway + bass bob, growing shake, then a spin that accelerates into the drop
        roll = 0.018 * math.sin(t * 0.45) + 0.010 * math.sin(t * 1.1) + (0.03 + 0.2 * hack) * math.sin(t * (1.0 + 4 * hack)) * hack
        spin = sstep(ramp(t, 44.0, 47.8))
        kal.update(u_roll=roll + spin * spin * 9.0, u_kzoom=1.0 + 0.9 * sstep(ramp(t, 43.0, 47.3)) + 0.012 * kick,
                   u_blr=0.28 * spin, u_blz=0.08 * spin)
        fb.update(u_decay=0.35 + 0.35 * hack, u_fzoom=1.0 + 0.012 * hack, u_fmix=0.6)
        po.update(u_vhs=0.18 + 0.6 * hack, u_bloom=0.9 + 0.4 * kick + 0.5 * hack, u_ca=0.002 + 0.004 * kick + 0.012 * hack + 0.02 * kick * hack)
        po["u_pump"] = (0.012 + 0.05 * hack) * kick
        po["u_flash"] = (0.05 + 0.1 * hack) * kick
        po["u_glit"] = 0.4 * hack * (0.3 + snare) * (1 if t > 36.5 else 0.0)
        po["u_glit2"] = 0.5 * hack * (1 if t > 38 else 0.0)
        po["u_caosc"] = 0.6 * hack
        shake(X, 0.004 + 0.02 * hack)
        accent = lerp_c(PINK, CYAN, hack)
        if t >= T_PRE:
            a_ = sstep(ramp(t, 39.0, 47.3))
            asc.update(u_amt=0.40 * a_, u_cell=20.0, u_cm=0.35, u_melt=0.12 * a_, u_jit=0.12, u_acol=(0.55, 1.0, 1.0))
            asc["ring_on"] = asc["u_kt"] < 0.75 and t > 42
            sc.update(u_sB=2, u_aB=(0.0, 0.0, 0.0, 0.0), u_mix=0.5 * sstep(ramp(t, 40.5, 46.5)), u_pal=1.0)
            popups3(X, 0.7)
            if t > 45.0:
                mdiv = 1 if t < 46.0 else (2 if t < 47.0 else 4)
                po["u_flash"] = max(po["u_flash"], 0.5 * beat_flash(t, mdiv) * ramp(t, 45.0, 47.4))
                po["u_flashcol"] = tuple(x * 0.45 + 0.55 for x in CYAN)
            g = sstep(ramp(t, 45.3, 47.9))
            if g > 0:
                skull_sprite(X, "mid", V.cx, 840, 1000, "skull_hero", alpha=0.85 * g, k_amp=0.08, dis=1.0 - g)
        if t >= T_BLACK:
            po["u_black"] = 1.0
            po["u_dot"] = sstep(ramp(t, T_BLACK, T_D1)) * 0.9
            fb["u_decay"] = 0.0
            asc["u_amt"] = 0.0
            cm["pre0"], cm["pre"], cm["mid"], cm["post"] = [], [], [], []
            cm["post"].append(("term_type", dict(t=t, t0=T_BLACK + 0.05, text="> ACCESS_", cx=V.cx, cy=900)))
        elif t >= 47.3:
            po["u_flash"] = max(po["u_flash"], 0.7 * math.exp(-(t - 47.3) / 0.12))

    # ============================================================ DROP 1
    elif t < T_MID:
        k_, lt = look_index(t, D1_B)
        X["lt"] = lt
        X["look_u"] = lt / max(D1_B[k_ + 1] - D1_B[k_], 0.1)
        name = D1_LOOKS[k_]
        LOOKS[name](X)
        accent = X.get("acc", CYAN)
        drop_common(X, big=1.0, accent=accent)
        if t < T_D1 + 0.5:
            e = math.exp(-(t - T_D1) / 0.18)
            po["u_flash"] += 1.3 * e
            po["u_pump"] += 0.3 * e
            po["u_ca"] += 0.06 * e
            po["u_pix"] = max(po["u_pix"], 0.9 * e)

    # ============================================================ MID-SECTION
    elif t < T_D2:
        hk = 0.55 if t < 104.6 else lerp(0.55, 0.15, ramp(t, 104.6, 108.0))
        if t >= T_RISER:
            hk = lerp(0.15, 1.0, ramp(t, T_RISER, 117.0))
        sc["u_hack"] = hk
        sc["u_aA"] = (0.0, 1.0 if t < 104.6 else -1.0, 0.0, 0.0)
        sc["u_sun"] = 1.0 if t < 104.6 else lerp(1.0, 0.25, ramp(t, 104.6, 108.5))
        sc["u_city"] = 1.0 if t < 104.6 else lerp(1.0, 0.1, ramp(t, 104.6, 107.5))
        kal.update(u_roll=0.05 * math.sin(t * 1.6) + 0.1 * kick * (hash01(math.floor(t * 20)) - 0.5), u_kzoom=1.0 + 0.05 * kick,
                   u_blz=0.04 if 103.4 < t < 107 else 0.0)
        fb.update(u_decay=0.45, u_fzoom=1.0, u_fmix=0.6)
        if t < 103.4:       # pristine glass cathedral -> shatters on GLASS! -> the world behind it
            sc.update(u_sA=7, u_pal=0.0, u_aA=(sc["u_gt"], -1.1 * kick, 0.0, 0.06 * kick), u_sB=0, u_shB=1.0,
                      u_mix=sstep(ramp(t, 102.62, 103.3)))
            fb.update(u_decay=0.18)
            po.update(u_glit2=0.0, u_glit=0.0, u_vhs=0.12, u_ca=0.003 + 0.004 * kick, u_caosc=0.0, u_expo=1.0)
        po.update(u_vhs=0.4 + 0.5 * hk, u_bloom=1.0 + 0.6 * kick, u_ca=0.004 + 0.016 * kick, u_caosc=0.4, u_glit2=0.2 * hk)
        po["u_pump"] = 0.05 * kick
        po["u_flash"] = 0.15 * kick
        shake(X, 0.012)
        accent = lerp_c(PINK, CYAN, hk)
        # "leave the shadows in the past": two neon cars (real objects inside the world shader) drive away from the camera
        for ci, (ta, tb, lane, pw, z0) in enumerate(((104.5, 108.8, -0.40, 1.6, 0.40), (105.2, 108.8, 0.44, 1.45, 0.34))):
            tt = ramp(t, ta, tb)
            if 0.0 < tt < 1.0:
                zc = z0 + 4.2 * tt ** pw
                al = sstep(ramp(tt, 0.0, 0.05)) * (1.0 - sstep(ramp(tt, 0.86, 1.0)))
                sc["u_car" if ci == 0 else "u_car2"] = (al, zc, lane)
        if 107.2 < t < 112.4:
            ph = 0.0
            for te in (107.36, 109.2, 111.0):
                if te <= t < te + 0.5:
                    ph = max(ph, math.exp(-(t - te) / 0.16))
            fb.update(u_decay=0.62, u_fzoom=0.955)
            po["u_inv"] = 1.0 if ph > 0.75 else 0.0
            po["u_flash"] += 0.3 * ph
            po["u_pump"] += 0.06 * ph
            po["u_expo"] = 0.85
        if t >= T_RISER:
            m = ramp(t, T_RISER, 117.6)
            sc.update(u_sA=0, u_sB=6, u_aB=(0.0, 0.0, 0.0, 0.0), u_mix=sstep(m) * 0.85, u_pal=0.0, u_neon=1.0 - 0.45 * m)
            sc["u_sun"] = sc["u_sun"] * (1.0 - 0.7 * m)
            spin = m * m
            kal.update(u_roll=kal["u_roll"] + spin * 14.0, u_blr=0.3 * spin, u_blz=0.1 * spin, u_kzoom=1.0 + 0.7 * m * m)
            fb.update(u_decay=0.50 + 0.2 * m, u_fzoom=1.0 + 0.03 * m, u_frot=0.012 * m)
            asc.update(u_amt=0.6 * sstep(ramp(t, 113.0, 117.8)), u_cell=14.0, u_cm=0.0, u_melt=0.15, ring_on=asc["u_kt"] < 0.75)
            po["u_bloom"] = 0.9 + 0.4 * m
            po["u_expo"] = 1.0 - 0.3 * m
            po["u_glit"] = 0.1 + 0.5 * m + 0.3 * snare
            po["u_glit2"] = 0.3 + 0.5 * m
            po["u_ca"] = 0.005 + 0.02 * m
            mdiv = 1 if t < 114.0 else (2 if t < 116.0 else (4 if t < 117.5 else 8))
            po["u_flash"] = 0.7 * beat_flash(t, mdiv) * ramp(t, 113.0, 114.0)
            po["u_flashcol"] = tuple(x * 0.45 + 0.55 for x in CYAN)
            shake(X, 0.012 + 0.012 * m)
            popups3(X, 0.9)
            g = ramp(t, 115.5, T_BLACK2)
            if g > 0:
                skull_sprite(X, "mid", V.cx, 840, 1000, "skull_hero", alpha=0.6 * g, k_amp=0.1)
        if t >= T_BLACK2:
            po["u_black"] = 1.0
            po["u_dot"] = sstep(ramp(t, T_BLACK2, T_D2)) * 0.9
            fb["u_decay"] = 0.0
            asc["u_amt"] = 0.0
            cm["pre0"], cm["pre"], cm["mid"], cm["post"] = [], [], [], []
            cm["post"].append(("term_type", dict(t=t, t0=T_BLACK2 + 0.05, text="> OVERRIDE_", cx=V.cx, cy=900)))

    # ============================================================ DROP 2
    elif t < T_OUT:
        k_, lt = look_index(t, D2_B)
        X["lt"] = lt
        X["look_u"] = lt / max(D2_B[min(k_ + 1, len(D2_B) - 1)] - D2_B[k_], 0.1)
        name = D2_LOOKS[k_ % len(D2_LOOKS)]
        LOOKS[name](X)
        accent = (PINK, CYAN, RED, YELLOW)[k_ % 4]
        drop_common(X, big=1.45, accent=accent)
        if name == "glass" and t < 128.28:   # keep the pristine glass calm until it breaks
            po.update(u_glit2=0.0, u_glit=0.0, u_vhs=0.12, u_caosc=0.0, u_inv=0.0, u_ca=0.003 + 0.005 * kick, u_expo=1.0, u_pix=0.0)
            fb["u_decay"] = 0.18
        esc = ramp(t, 139.0, 150.5)
        if esc > 0:
            if int(np.searchsorted(BEATS, t, side="right")) % 2 and kal["u_seg"] > 1.5:
                kal["u_seg"] = kal["u_seg"] * 2
            po["u_glit"] += 0.25 * esc
            po["u_ca"] += 0.012 * esc
            po["u_flash"] += 0.22 * esc * hat
            asc["u_amt"] = min(1.0, asc["u_amt"] + 0.3 * esc)
        if T_D2 <= t < T_D2 + 0.5:
            e = math.exp(-(t - T_D2) / 0.18)
            po["u_flash"] += 1.5 * e
            po["u_pump"] += 0.35 * e
            po["u_ca"] += 0.07 * e
            po["u_pix"] = max(po["u_pix"], 0.9 * e)
            asc["u_amt"] = max(asc["u_amt"], 1.0 * e)
            asc["u_melt"] = max(asc["u_melt"], 3.0 * e)
        if 135.6 <= t < 136.55:
            h_ = ramp(t, 135.6, 136.0)
            po["u_pump"] += 0.12 * h_
            po["u_ca"] += 0.025 * h_
        if 136.55 <= t < 136.9:
            po["u_flash"] += 1.2 * math.exp(-(t - 136.55) / 0.12)
            po["u_pix"] = max(po["u_pix"], 0.8 * math.exp(-(t - 136.55) / 0.1))

    # ============================================================ OUTRO: the code turns back into the world
    else:
        o = ramp(t, T_OUT, 165.0)
        hk = lerp(1.0, 0.0, sstep(o))
        sc["u_hack"] = hk
        # dusk -> night: the sun sinks, the sky goes dark, the moon rises
        sc["u_sun"] = 1.0 - sstep(ramp(t, 156.0, 169.0))
        sc["u_dusk"] = sstep(ramp(t, 156.0, 163.0)) * (1.0 - sstep(ramp(t, 166.0, 173.0)))
        sc["u_night"] = sstep(ramp(t, 160.0, 173.0))
        sc["u_moon"] = sstep(ramp(t, 163.0, 178.5))
        sc["u_aA"] = (0.0, -1.0, 0.0, 0.0)
        sc["u_city"] = lerp(0.5, 1.0, ramp(t, 156, 164))
        flick = 0.55 + 0.45 * math.sin(t * 37.0) * math.sin(t * 11.0)
        sc["u_neon"] = lerp(lerp(1.0, 0.35 + 0.35 * max(0.0, flick), ramp(t, 154, 157)), 0.9, ramp(t, 158, 163))
        kal.update(u_roll=0.02 * math.sin(t * 0.5), u_kzoom=1.0)
        fb.update(u_decay=0.5, u_fmix=0.6)
        asc.update(u_amt=1.0 - sstep(ramp(t, T_OUT + 0.5, 163.0)), u_cell=12.0, u_cm=0.5 * (1 - o), u_melt=lerp(0.6, 0.0, o), u_dir=-1.0,
                   u_acol=(0.7, 1.0, 1.0))
        po.update(u_vhs=lerp(0.9, 0.25, o), u_bloom=1.0 + 0.4 * kick, u_ca=lerp(0.012, 0.002, o), u_sat=lerp(1.2, 0.95, o))
        po["u_pump"] = 0.02 * kick
        po["u_expo"] = 1.0
        po["u_glit2"] = 0.3 * hk
        accent = lerp_c(CYAN, PINK, o)
        if t < T_OUT + 7.0:
            g = 1.0 - ramp(t, T_OUT + 0.3, T_OUT + 7.0)
            reaper(X, alpha=0.8 * g, dis=ramp(t, T_OUT + 2.0, T_OUT + 7.0), h=1400, cy=930)
        if t < T_OUT + 0.4:
            po["u_flash"] = 0.8 * math.exp(-(t - T_OUT) / 0.1)
            po["u_pix"] = 0.8 * math.exp(-(t - T_OUT) / 0.12)
        # the TV switches off: the picture dims, snaps back at T_CRT (a white flash), then collapses to a line and a dot
        if t < T_CRT:
            po["u_fade"] = lerp(1.0, 0.55, ramp(t, 175.5, T_CRT))
        else:
            po["u_fade"] = 1.0
            po["u_crt"] = ramp(t, T_CRT, T_END - 0.02)
            po["u_flash"] = 0.9 * math.exp(-(t - T_CRT) / 0.08)

    if po["u_black"] < 0.5:
        for b in TL.BLOCKS:                      # ACCESS GRANTED / SYSTEM OVERRIDE (timings from assets/type_events.json)
            if b["t0"] - 0.02 <= t <= b["t1"] + 0.1:
                bigtext(X, b["lines"], b["t0"], b["t1"], color=tuple(b["color"]), cy=b["cy"], label=b.get("label"))
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
    asc["u_t"] = t
    return dict(spec=f["spec"], scene=sc, kal=kal, fb=fb, post=po, ascii=asc, bloom_thr=1.0, accent=accent, t=t, cmds=cm)
