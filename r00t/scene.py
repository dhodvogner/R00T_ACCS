"""Per-frame scene assembly: choreography -> uniforms + draw hooks (sprites, popups, brutalist type layer)."""
import numpy as np
from PIL import Image, ImageDraw

from . import choreo3 as C
from . import typelayer as TL
from .paths import load_font

FD = r"C:\Windows\Fonts"

POPUP_SPEC = [
    dict(title="FATAL_ERROR.EXE", lines=["0xDEADBEEF", "SYSTEM FAILURE"], col=(255, 32, 64)),
    dict(title="ACCESS_DENIED", lines=["> retry? [Y/N]", "> _"], col=(255, 45, 149)),
    dict(title="ROOT@NIGHT:~#", lines=["> own --the-night", "ACCESS GRANTED"], col=(0, 229, 255)),
    dict(title="SYSTEM_OVERLOAD", lines=["CPU 99%  MEM 99%", "#####################.."], col=(255, 225, 74)),
    dict(title="WARNING", lines=["GRAVITY.SYS", "NOT FOUND"], col=(255, 140, 38)),
    dict(title="HEX_DUMP", lines=["3F A9 0C D1 7E 22", "B4 00 FF 19 C3 6A", "5D E8 41 9B 07 AA"], col=(0, 229, 255)),
    dict(title="BREACH_DETECTED", lines=["firewall: DOWN", "trace: 100%"], col=(255, 32, 64)),
    dict(title="VHS_PLAYER.EXE", lines=["tracking lost...", "REWIND >> >> >>"], col=(138, 43, 255)),
]


def make_popup(kind):
    sp = POPUP_SPEC[kind]
    w_, h_ = 560, 300
    img = Image.new("RGBA", (w_, h_), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    col = sp["col"]
    d.rectangle((0, 0, w_ - 1, h_ - 1), fill=(10, 4, 26, 235), outline=col + (255,), width=5)
    d.rectangle((0, 0, w_ - 1, 50), fill=col + (255,))
    ft = load_font(FD + r"\consolab.ttf", 28)
    fb = load_font(FD + r"\consolab.ttf", 33)
    d.text((16, 9), sp["title"], font=ft, fill=(0, 0, 0, 255))
    d.rectangle((w_ - 48, 8, w_ - 12, 42), fill=(10, 4, 26, 255))
    d.text((w_ - 41, 8), "X", font=ft, fill=col + (255,))
    for i, ln in enumerate(sp["lines"]):
        d.text((22, 78 + i * 52), ln, font=fb, fill=(235, 250, 255, 255) if i else col + (255,))
    d.rectangle((22, h_ - 46, w_ - 22, h_ - 22), outline=col + (255,), width=3)
    d.rectangle((26, h_ - 42, 26 + int((w_ - 56) * (0.55 + 0.4 * (kind % 3) / 2.0)), h_ - 26), fill=col + (255,))
    a = np.asarray(img, np.float32)
    al = a[..., 3:4] / 255.0
    return np.dstack([a[..., :3] * al, a[..., 3:4]]).clip(0, 255).astype(np.uint8)


def make_term(side):
    rng = np.random.RandomState(5 + side)
    w_, h_ = 190, 2200
    img = Image.new("RGBA", (w_, h_), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    f = load_font(FD + r"\consolab.ttf", 24)
    for i in range(h_ // 30):
        s = " ".join("%02X" % rng.randint(0, 256) for _ in range(5))
        d.text((6, i * 30), s, font=f, fill=(0, 229, 255, 255) if rng.rand() > 0.15 else (255, 45, 149, 255))
    a = np.asarray(img, np.float32)
    al = a[..., 3:4] / 255.0
    return np.dstack([a[..., :3] * al, a[..., 3:4]]).clip(0, 255).astype(np.uint8)


def run_cmds(eng, fbo, cmds, t):
    for kind, p in cmds:
        if kind == "bigtext":
            TL.draw_bigtext(eng, fbo, p, t)
        elif kind == "video":
            eng.draw_video(fbo, **p)
        elif kind == "atlas":
            q = dict(p)
            q.setdefault("time", t)
            eng.draw_atlas(fbo, **q)
        elif kind == "popup":
            k = ("popup", p["kind"])
            key = eng.tex_from_rgba(k, make_popup(p["kind"])) if k not in eng.sprites else eng.sprites[k]
            eng.draw_sprite(fbo, key, p["cx"], p["cy"], scale=p["scale"], rot=p["rot"], alpha=p["alpha"], split=p["split"] * 560)
        elif kind == "term":
            k = ("term", p["side"])
            key = eng.tex_from_rgba(k, make_term(p["side"])) if k not in eng.sprites else eng.sprites[k]
            hh = 2200
            off = p["scroll"] % hh
            for n in (-1, 0, 1):
                eng.draw_sprite(fbo, key, p["cx"], 960 - off + n * hh + hh / 2, alpha=p["alpha"])
        elif kind == "term_type":
            n = int(max(0.0, (t - p["t0"])) * 20)
            cur = "_" if int(t * 4) % 2 == 0 else " "
            key = eng.sprite(p["text"][:n] + cur, "mono", 64, (255, 229, 0), grad=False)
            eng.draw_sprite(fbo, key, p["cx"], p["cy"], alpha=1.0, tint=(1.2, 1.2, 1.2))


def make_hooks(t, S):
    cm = S["cmds"]
    kick = S["scene"]["u_kick"]

    def pre0(eng, fbo):
        run_cmds(eng, fbo, cm["pre0"], t)

    def pre(eng, fbo):
        run_cmds(eng, fbo, cm["pre"], t)

    def mid(eng, fbo):
        run_cmds(eng, fbo, cm["mid"], t)

    def post(eng, fbo):
        TL.text_pass(eng, None, fbo, t, kick)          # solid / outline type + tiny mono annotations
        run_cmds(eng, fbo, cm["post"], t)

    def mask(eng, fbo):
        TL.mask_pass(eng, fbo, eng.f_text, t, kick)    # invert-mask / knock-out-window type

    return dict(pre0=pre0, pre=pre, mid=mid, post=post, mask=mask)


def render(eng, t, to_screen=None):
    """render the demo at time t (seconds)"""
    i = int(t * C.FPS)
    S = C.frame_state(i, t)
    S["post"]["u_capdim"] = 0.0
    S["post"]["u_win"] = TL.win_amount(t)
    eng.render(S, make_hooks(t, S), to_screen)


def warm_caches(eng, progress=None):
    """build every text sprite / popup texture up front so nothing hitches during playback"""
    jobs = []
    seen = set()

    def add(fn, key):
        if key not in seen:
            seen.add(key)
            jobs.append(fn)

    for ev in TL.EVENTS:
        style = "outline" if ev["mode"] == "outline" else "fill"
        for w in ev["words"]:
            add(lambda w=w, st=style: TL.wkey(eng, w, "cond", st), ("w", w, style))
            add(lambda w=w: TL.wkey(eng, w, "cond", "fill"), ("w", w, "fill"))
        for a in ev.get("ann", []):
            add(lambda a=a: eng.sprite(a, "mono", 30, (255, 255, 255), grad=False), ("a", a))
    for w in ("ACCESS", "GRANTED", "SYSTEM", "OVERRIDE"):
        add(lambda w=w: TL.wkey(eng, w, "cond", "fill"), ("w", w, "fill"))
    add(lambda: eng.sprite("ROOT@NIGHT:~#  PRIVILEGE ESCALATION COMPLETE", "mono", 34, (255, 255, 255), grad=False), ("lab",))
    for text in ("> ACCESS_", "> OVERRIDE_", "> ACCESS_GRANTED"):
        for n in range(len(text) + 1):
            for cur in ("_", " "):
                add(lambda s=text[:n] + cur: eng.sprite(s, "mono", 64, (255, 229, 0), grad=False), ("tt", text, n, cur))
    for k in range(len(POPUP_SPEC)):
        add(lambda k=k: eng.tex_from_rgba(("popup", k), make_popup(k)), ("popup", k))
    for sd in (0, 1):
        add(lambda sd=sd: eng.tex_from_rgba(("term", sd), make_term(sd)), ("term", sd))
    n = len(jobs)
    for i, fn in enumerate(jobs):
        fn()
        if progress and (i % 40 == 0 or i == n - 1):
            progress((i + 1) / float(n))
