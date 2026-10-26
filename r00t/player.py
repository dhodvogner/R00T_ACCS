"""R00T_ACCS player: window + audio clock + hotkeys. The audio is the master clock; every frame is computed live from t."""
import argparse
import json
import os
import sys
import time
import traceback

import numpy as np

from . import __version__
from .paths import asset, user_dir

DEMO_LEN = 180.0
SCALES = [0.5, 0.67, 0.75, 1.0, 1.25]

CREDITS = [
    ("R00T_ACCS", 120, (0, 229, 255)),
    ("a real-time demo for the track", 40, (200, 210, 230)),
    ('"WE OWN THE NIGHT"', 64, (255, 45, 149)),
    ("", 30, (0, 0, 0)),
    ("music ........ hodiloves  (made with Suno)", 34, (230, 235, 245)),
    ("code ......... hodiloves + Claude", 34, (230, 235, 245)),
    ("engine ....... Python / moderngl / GLSL", 34, (230, 235, 245)),
    ("sprites ...... generated with fal.ai", 34, (230, 235, 245)),
    ("dancers ...... generated with fal.ai (FLUX)", 34, (230, 235, 245)),
    ("", 30, (0, 0, 0)),
    ("everything you saw was computed live,", 34, (255, 225, 74)),
    ("in a pixel shader, on your GPU.", 34, (255, 225, 74)),
    ("", 30, (0, 0, 0)),
    ("find me", 40, (255, 45, 149)),
    ("[1]  instagram.com/hodiloves", 34, (230, 235, 245)),
    ("[2]  tiktok.com/@hodiloves", 34, (230, 235, 245)),
    ("[3]  youtube.com/@hodilovestoo", 34, (230, 235, 245)),
    ("[4]  suno.com/@hodiloves", 34, (230, 235, 245)),
    ("press 1-4 to open", 28, (150, 160, 185)),
    ("", 30, (0, 0, 0)),
    ("[R] replay    [ESC] quit", 34, (0, 229, 255)),
]

LINKS = {
    "1": "https://www.instagram.com/hodiloves/",
    "2": "https://www.tiktok.com/@hodiloves",
    "3": "https://www.youtube.com/@hodilovestoo",
    "4": "https://suno.com/@hodiloves",
}


def log(msg):
    try:
        with open(os.path.join(user_dir(), "r00t_log.txt"), "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception:
        pass


def parse(argv):
    ap = argparse.ArgumentParser(prog="R00T_ACCS", description="real-time synthwave-gets-hacked demo")
    ap.add_argument("--windowed", action="store_true", help="run in a window instead of fullscreen")
    ap.add_argument("--res", default="1280x720", help="window size for --windowed (default 1280x720)")
    ap.add_argument("--scale", type=float, default=1.0, help="internal render scale (0.5 .. 1.5); lower = faster")
    ap.add_argument("--start", type=float, default=0.0, help="start playback at this many seconds")
    ap.add_argument("--mute", action="store_true", help="run without audio (free-running clock)")
    ap.add_argument("--no-vsync", action="store_true")
    ap.add_argument("--export", default="", metavar="FILE.mp4", help="render the demo offline to a video file (needs ffmpeg on PATH); size from --res")
    ap.add_argument("--fps", type=int, default=60, help="frame rate for --export (default 60)")
    ap.add_argument("--export-range", default="0,180", metavar="A,B", help="seconds to export (default the whole demo)")
    ap.add_argument("--crf", type=int, default=21, help="x264 quality for --export (lower = better/bigger)")
    ap.add_argument("--ffmpeg", default="", help="path to ffmpeg (default: found on PATH)")
    ap.add_argument("--bench", type=int, default=0, metavar="N", help="render N frames offline, write bench.json + a screenshot, exit")
    ap.add_argument("--shots", default="", metavar="T1,T2,..", help="save a screenshot at each of these times (seconds), then exit")
    ap.add_argument("--sync-ms", type=float, default=0.0, help="shift visuals relative to audio (ms)")
    ap.add_argument("--version", action="version", version=f"R00T_ACCS {__version__}")
    return ap.parse_args(argv)


def _dpi_aware():
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


class Loader:
    """tiny cracktro-style loading screen drawn with the engine's own sprite path"""

    def __init__(self, eng, win_size, pygame):
        self.eng, self.win, self.pg = eng, win_size, pygame

    def frame(self, frac, msg):
        from .canvas import V
        eng = self.eng
        eng.f_out.use()
        eng.f_out.clear(0.01, 0.0, 0.04, 1.0)
        title = eng.sprite("R00T_ACCS", "mono", 150, (255, 229, 0), grad=False)
        eng.draw_sprite(eng.f_out, title, V.cx, 800, tint=(1.4, 1.4, 1.4))
        n = int(frac * 24)
        bar = eng.sprite("[" + "#" * n + "." * (24 - n) + "]", "mono", 52, (149, 45, 255), grad=False)
        eng.draw_sprite(eng.f_out, bar, V.cx, 1000)
        m = eng.sprite(msg, "mono", 36, (230, 210, 200), grad=False)
        eng.draw_sprite(eng.f_out, m, V.cx, 1090)
        eng.present(*self.win)
        self.pg.display.flip()
        self.pg.event.pump()


def credits_frame(eng, tc, win):
    from .canvas import V
    eng.f_out.use()
    eng.f_out.clear(0.01, 0.0, 0.04, 1.0)
    total = sum(sz * 1.9 for _, sz, _ in CREDITS)
    max_off = 1250 + (total - CREDITS[-1][1] * 1.9) - 1700          # stop with the last lines (links + replay) on screen
    y = 1250 - min(tc * 90.0, max(max_off, 0.0))
    for text, size, col in CREDITS:
        if text:
            key = eng.sprite(text, "mono", size, tuple(col[::-1]), grad=False)
            if -100 < y < 2020:
                eng.draw_sprite(eng.f_out, key, V.cx, y, tint=(1.3, 1.3, 1.3))
        y += size * 1.9
    eng.present(*win)


def run(argv=None):
    args = parse(argv if argv is not None else sys.argv[1:])
    _dpi_aware()
    import pygame
    import moderngl
    from .engine import Engine

    os.environ.setdefault("SDL_VIDEO_CENTERED", "1")
    if not args.mute and not args.bench and not args.export:
        pygame.mixer.pre_init(44100, -16, 2, 1024)
    pygame.init()
    pygame.display.set_caption("R00T_ACCS")
    pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION, 3)
    pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MINOR_VERSION, 3)
    pygame.display.gl_set_attribute(pygame.GL_CONTEXT_PROFILE_MASK, pygame.GL_CONTEXT_PROFILE_CORE)
    flags = pygame.OPENGL | pygame.DOUBLEBUF
    windowed = args.windowed or args.bench > 0 or bool(args.shots)
    if args.export:
        pygame.display.set_mode((64, 64), flags | pygame.HIDDEN)
    elif windowed:
        rw, rh = (int(v) for v in args.res.lower().split("x"))
        pygame.display.set_mode((rw, rh), flags, vsync=0 if (args.no_vsync or args.bench) else 1)
    else:
        pygame.display.set_mode((0, 0), flags | pygame.FULLSCREEN, vsync=0 if args.no_vsync else 1)
        pygame.mouse.set_visible(False)
    win = pygame.display.get_window_size()
    ctx = moderngl.create_context(require=330)
    log(f"[r00t] {__version__} GL={ctx.info['GL_RENDERER']} window={win}")
    scale_i = min(range(len(SCALES)), key=lambda i: abs(SCALES[i] - args.scale))

    def internal(sc):
        return max(64, int(win[0] * sc) // 2 * 2), max(64, int(win[1] * sc) // 2 * 2)

    if args.export:
        ew, eh = (int(v) for v in args.res.lower().split("x"))
        eng = Engine(ctx, ew // 2 * 2, eh // 2 * 2)
    else:
        eng = Engine(ctx, *internal(SCALES[scale_i]))
    loader = Loader(eng, win, pygame)
    loader.frame(0.0, "decoding dancers ...")
    eng.load_video("dance_skel", asset("dance_skel.mp4"))
    loader.frame(0.2, "decoding dancers ...")
    eng.load_video("dance_hood", asset("dance_hood.mp4"))
    from . import scene
    scene.warm_caches(eng, lambda f: loader.frame(0.3 + 0.6 * f, "baking glyphs ..."))
    loader.frame(0.92, "compiling shaders ...")
    for tw in (30.0, 60.0, 102.3, 125.0):          # touch every heavy path once so the driver compiles it now
        scene.render(eng, tw)
    ctx.finish()
    eng.clear_all()
    loader.frame(1.0, "ready")

    if args.export:
        return export_video(args, eng, scene, pygame)
    if args.shots:
        return shots(args, eng, scene, ctx, win, pygame)
    if args.bench:
        return bench(args, eng, scene, ctx, win, pygame)

    use_audio = not args.mute
    if use_audio:
        pygame.mixer.music.load(asset("song.mp3"))
    clock = pygame.time.Clock()
    base = args.start
    perf0 = time.perf_counter()
    sync = args.sync_ms / 1000.0
    paused = False
    pause_at = 0.0
    state = "demo"
    credits_t0 = 0.0
    frame_n = 0
    if use_audio:
        pygame.mixer.music.play(start=base)
        perf0 = time.perf_counter()

    def now():
        return base + (time.perf_counter() - perf0)

    def seek(sec):
        nonlocal base, perf0, state
        sec = max(0.0, min(DEMO_LEN - 0.5, sec))
        base, perf0, state = sec, time.perf_counter(), "demo"
        if use_audio:
            pygame.mixer.music.play(start=sec)
        eng.clear_all()

    running = True
    while running:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
            elif ev.type == pygame.KEYDOWN:
                k = ev.key
                if k in (pygame.K_ESCAPE, pygame.K_q):
                    running = False
                elif k == pygame.K_f:
                    pygame.display.toggle_fullscreen()
                    win = pygame.display.get_window_size()
                    eng.alloc(*internal(SCALES[scale_i]))
                    loader.win = win
                elif k == pygame.K_SPACE and state == "demo":
                    if not paused:
                        paused, pause_at = True, now()
                        if use_audio:
                            pygame.mixer.music.pause()
                    else:
                        paused = False
                        base, perf0 = pause_at, time.perf_counter()
                        if use_audio:
                            pygame.mixer.music.unpause()
                elif k == pygame.K_LEFT:
                    seek((pause_at if paused else now()) - 10.0)
                elif k == pygame.K_RIGHT:
                    seek((pause_at if paused else now()) + 10.0)
                elif k == pygame.K_r:
                    seek(0.0)
                elif k in (pygame.K_MINUS, pygame.K_EQUALS, pygame.K_PLUS):
                    scale_i = max(0, min(len(SCALES) - 1, scale_i + (1 if k != pygame.K_MINUS else -1)))
                    eng.alloc(*internal(SCALES[scale_i]))
                    log(f"[r00t] render scale {SCALES[scale_i]} -> {eng.W}x{eng.H}")
                elif k == pygame.K_LEFTBRACKET:
                    sync -= 0.010
                elif k == pygame.K_RIGHTBRACKET:
                    sync += 0.010
                elif k == pygame.K_F12:
                    shot(eng)
                elif state == "credits" and k in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4):
                    import webbrowser
                    webbrowser.open(LINKS[chr(k)])
        if not running:
            break
        t = (pause_at if paused else now()) + sync
        if state == "demo":
            if use_audio and frame_n % 20 == 0 and not paused:
                gp = pygame.mixer.music.get_pos()
                if gp >= 0:
                    d = (base + gp / 1000.0) - (now())
                    if abs(d) > 0.02 and abs(d) < 2.0:
                        perf0 -= d * 0.3
            if t >= DEMO_LEN:
                state, credits_t0 = "credits", time.perf_counter()
            else:
                scene.render(eng, max(0.0, t), win)
        if state == "credits":
            credits_frame(eng, time.perf_counter() - credits_t0, win)
        pygame.display.flip()
        frame_n += 1
        clock.tick(60)
    pygame.quit()


def shot(eng, name=None):
    from PIL import Image
    d = os.path.join(user_dir(), "screenshots")
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, name or time.strftime("r00t_%Y%m%d_%H%M%S.png"))
    Image.fromarray(eng.read_frame()).save(p)
    log(f"[r00t] screenshot {p}")


def export_video(args, eng, scene, pygame):
    """offline render: every frame is a pure function of time, so the video is frame-exact and identical on every machine"""
    import shutil
    import subprocess
    ff = args.ffmpeg or shutil.which("ffmpeg")
    if not ff:
        raise RuntimeError("ffmpeg was not found. Install ffmpeg (or pass --ffmpeg C:\path\ffmpeg.exe) to use --export.")
    a, b = (float(x) for x in args.export_range.split(","))
    fps = max(1, args.fps)
    n = int(round((b - a) * fps))
    out = os.path.abspath(args.export)
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    cmd = [ff, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{eng.W}x{eng.H}", "-r", str(fps), "-i", "-",
           "-ss", f"{a:.3f}", "-t", f"{b - a:.3f}", "-i", asset("song.mp3"), "-map", "0:v", "-map", "1:a",
           "-c:v", "libx264", "-preset", "medium", "-crf", str(args.crf), "-maxrate", "16M", "-bufsize", "32M", "-pix_fmt", "yuv420p",
           "-profile:v", "high", "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-movflags", "+faststart", out]
    log(f"[r00t] export {eng.W}x{eng.H} @{fps} {a}-{b}s -> {out}")
    eng.clear_all()
    for k in range(min(60, int(a * fps))):                      # let the feedback buffer settle when starting mid-song
        scene.render(eng, a - (60 - k) / float(fps))
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    t0 = time.perf_counter()
    for i in range(n):
        scene.render(eng, a + i / float(fps))
        p.stdin.write(eng.read_frame().tobytes())
        if i % 600 == 0:
            log(f"[r00t] export frame {i}/{n}  {time.perf_counter() - t0:.0f}s")
        if i % 30 == 0:
            pygame.event.pump()
    p.stdin.close()
    rc = p.wait()
    log(f"[r00t] export done rc={rc} in {time.perf_counter() - t0:.0f}s -> {out}")
    pygame.quit()
    if rc != 0:
        raise RuntimeError(f"ffmpeg exited with code {rc}")


def shots(args, eng, scene, ctx, win, pygame):
    for tt in [float(x) for x in args.shots.split(",") if x.strip()]:
        if tt >= DEMO_LEN:                       # t >= 180 previews the credits screen (t - 180 = seconds into the credits)
            credits_frame(eng, tt - DEMO_LEN, win)
            pygame.display.flip()
            shot(eng, f"t_{tt:07.2f}.png")
            continue
        eng.clear_all()
        for k in range(40):                       # let the feedback buffer settle like it does in playback
            scene.render(eng, max(0.0, tt - 40 / 60.0 + k / 60.0))
        scene.render(eng, tt, win)
        pygame.display.flip()
        shot(eng, f"t_{tt:07.2f}.png")
    pygame.quit()


def bench(args, eng, scene, ctx, win, pygame):
    n = args.bench
    t0 = args.start
    times = []
    for i in range(n):
        t = t0 + i / 60.0
        a = time.perf_counter()
        scene.render(eng, t, win)
        ctx.finish()
        pygame.display.flip()
        times.append(time.perf_counter() - a)
        pygame.event.pump()
    arr = np.array(times[5:]) * 1000.0
    out = dict(gpu=ctx.info["GL_RENDERER"], internal=f"{eng.W}x{eng.H}", window=f"{win[0]}x{win[1]}", frames=n, start=t0,
               avg_ms=round(float(arr.mean()), 2), p95_ms=round(float(np.percentile(arr, 95)), 2), max_ms=round(float(arr.max()), 2),
               fps_avg=round(1000.0 / float(arr.mean()), 1))
    shot(eng)
    with open(os.path.join(user_dir(), "bench.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    print(json.dumps(out))
    pygame.quit()


def main():
    try:
        run()
    except SystemExit:
        raise
    except Exception:
        msg = traceback.format_exc()
        log(msg)
        print(msg)
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, "R00T_ACCS crashed.\nDetails were written to r00t_log.txt next to the exe.", "R00T_ACCS", 0x10)
        except Exception:
            pass
        sys.exit(1)
