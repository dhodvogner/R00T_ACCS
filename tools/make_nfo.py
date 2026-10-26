"""Generates R00T_ACCS.nfo (CP437, 78 columns, the classic scene-release look) and README.md (the same text in a code block).

    python tools/make_nfo.py          # run after building; picks up the exe size from dist/ if it exists
"""
import argparse
import datetime
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W = 78
ap = argparse.ArgumentParser()
ap.add_argument("--repo", default="", help="GitHub OWNER/NAME (fills the SOURCE field and the README links)")
ap.add_argument("--youtube", default="", help="URL of the video (fills the VIDEO field)")
ARGS = ap.parse_args()

# --- tiny 5x5 block font (original) -----------------------------------------------------------------------
FONT = {
    "R": ["XXXX.", "X...X", "XXXX.", "X..X.", "X...X"],
    "0": [".XXX.", "X..XX", "X.X.X", "XX..X", ".XXX."],
    "T": ["XXXXX", "..X..", "..X..", "..X..", "..X.."],
    "_": [".....", ".....", ".....", ".....", "XXXXX"],
    "A": [".XXX.", "X...X", "XXXXX", "X...X", "X...X"],
    "C": [".XXXX", "X....", "X....", "X....", ".XXXX"],
    "S": [".XXXX", "X....", ".XXX.", "....X", "XXXX."],
}


def banner(text):
    """block letters: 2 columns x 2 rows per pixel, shaded top-to-bottom (no shadow, so the letter counters stay open)"""
    shade = ["█"] * 4 + ["▓"] * 3 + ["▒"] * 3
    rows = [[] for _ in range(10)]
    for ch in text:
        for y, row in enumerate(FONT[ch]):
            for sub in (0, 1):
                rows[y * 2 + sub].append("".join((shade[y * 2 + sub] * 2) if c == "X" else "  " for c in row) + "  ")
    full = ["".join(r) for r in rows]
    width = max(len(x.rstrip()) for x in full)
    return [x[:width].ljust(width) for x in full]      # equal widths -> centring keeps the rows aligned


def centre(s):
    return s.center(W).rstrip()


def box(title, lines):
    out = ["╔" + "═" * (W - 2) + "╗"]
    t = f" {title} "
    out.append("║" + t.center(W - 2, "░") + "║")
    out.append("╠" + "═" * (W - 2) + "╣")
    for ln in lines:
        out.append("║ " + ln.ljust(W - 4) + " ║")
    out.append("╚" + "═" * (W - 2) + "╝")
    return out


def fields(rows):
    return [f"{k.ljust(14, '.')}: {v}" for k, v in rows]


def exe_size():
    for p in (os.path.join(ROOT, "dist", "R00T_ACCS.exe"), os.path.join(ROOT, "dist", "R00T_ACCS", "R00T_ACCS.exe")):
        if os.path.exists(p):
            return f"{os.path.getsize(p) / 1048576:.1f} MB"
    return "see release page"


today = datetime.date.today().isoformat()
L = []
L.append("")
L.append("░" * W)
L.append("▒" * W)
L.append("▓" * W)
L.append("")
for ln in banner("R00T_"):
    L.append(centre(ln))
L.append("")
for ln in banner("ACCS"):
    L.append(centre(ln))
L.append("")
L.append("▓" * W)
L.append("▒" * W)
L.append("░" * W)
L.append(centre("-=[  hodiloves  presents  a  REAL-TIME  cracktro-style  demo  ]=-"))
L.append(centre("W E   O W N   T H E   N I G H T"))
L.append("")
L += box("R E L E A S E   I N F O", fields([
    ("RELEASE", "R00T_ACCS-WIN64-REALTIME.DEMO-hodiloves"),
    ("DATE", today),
    ("GROUP", "hodiloves"),
    ("TYPE", "real-time demo / cracktro-style intro"),
    ("PLATFORM", "Windows 10/11 x64  (OpenGL 3.3+ GPU)"),
    ("TRACK", '"We Own the Night"  (3:00, 180 BPM)'),
    ("FORMAT", "1 x EXE.  no installer. no serial. no keygen. no nag."),
    ("SIZE", exe_size()),
    ("VIDEO", ARGS.youtube.replace("https://", "") if ARGS.youtube else "coming soon"),
    ("SOURCE", f"github.com/{ARGS.repo}" if ARGS.repo else "see the repo"),
    ("LICENSE", "MIT (code) . music & art (c) hodiloves"),
    ("PROTECTION", "none.  every pixel is computed live on YOUR gpu"),
    ("RATING", "11/10  would get hacked again"),
]))
L.append("")
L += box("C R A C K E R   N O T E S", [
    "Nothing was cracked in the making of this release.",
    "The only thing that got hacked is a perfectly good synthwave sunset.",
    "",
    "It started as a vertical music video. People asked if it was 'just AI'.",
    "It is not. The music and the sprites are AI-made; the PICTURE is a",
    "program: GLSL shaders, ASCII post-pass, raymarched glass, a type engine",
    "that slams on the real kick drums. This exe is that program, running",
    "live, synced to the audio clock, on whatever display you have.",
])
L.append("")
L += box("I N S T A L L", [
    "1. Download R00T_ACCS.exe from the release page.",
    "2. Double-click it.",
    "3. There is no step 3. Turn the volume up.",
    "",
    "Goes full-screen at your desktop resolution and re-lays itself out for",
    "your aspect ratio (16:9, 16:10, ultrawide, even a rotated monitor).",
])
L.append("")
L += box("C O N T R O L S", [
    "ESC / Q ........ quit              SPACE ......... pause / resume",
    "LEFT / RIGHT ... seek -10s / +10s  R ............ restart",
    "F .............. fullscreen toggle  F12 .......... screenshot",
    "- / = .......... render scale      [ / ] ......... audio sync -/+ 10ms",
    "",
    "R00T_ACCS.exe --windowed --res 1600x900 --scale 0.75 --start 48 --mute",
    "R00T_ACCS.exe --export out.mp4 --res 1920x1080     (video; needs ffmpeg)",
    "(--help lists everything.  slow GPU?  --scale 0.5.  a crash writes",
    " r00t_log.txt next to the exe.)",
])
L.append("")
L += box("T E C H   S P E C S", [
    "audio is the master clock; every frame is a pure function of time t",
    "per-frame band energies + kick/snare/hat envelopes baked into assets/",
    "scenes: synthwave world w/ 3D palms, KIFS glass, hyperspace, matrix rain,",
    "        EQ rings, feedback trails, kaleidoscope, shatter",
    "pass 2: whole-frame ASCII re-render, kick shockwave rings, melt/drip",
    "post  : bloom, VHS, simplex line-glitch, chroma aberration, FOV stretch",
    "type  : brutalist layer -> invert mask + knock-out window on drum hits",
    "canvas: 1920-unit virtual canvas, one code path for every aspect ratio",
    "stack : Python . pygame (SDL2) . moderngl . numpy . PyInstaller",
])
L.append("")
L += box("B U I L D   I T   Y O U R S E L F", [
    "git clone <this repo>",
    "cd r00t_accs",
    "python -m venv .venv && .venv\\Scripts\\pip install -r requirements.txt",
    ".venv\\Scripts\\python r00t_accs.py --windowed",
    "",
    "powershell .\\build_exe.ps1            ->  dist\\R00T_ACCS.exe",
    "powershell .\\build_exe.ps1 -OneDir    ->  folder build, instant start",
    "python tools\\make_page.py --repo OWNER/NAME   (download page in docs/)",
    "python tools\\bake_features.py track.mp3   (re-bake audio analysis)",
])
L.append("")
L += box("C O N T A C T", [
    "instagram.com/hodiloves          tiktok.com/@hodiloves",
    "youtube.com/@hodilovestoo        suno.com/@hodiloves",
])
L.append("")
L += box("G R E E T Z", [
    "to everybody who ever stayed up till 3am to make a pixel do something",
    "it was not supposed to do.  to the shader-toy night owls, the tracker",
    "kids, the cracktro nostalgics, and anyone who has ever typed",
    "'one more tweak'.  keep the scene alive.",
    "",
    "credits: music - hodiloves (made with Suno) . code - hodiloves + Claude",
    "         sprites & dancer loops - generated with fal.ai",
])
L.append("")
L.append(centre("░▒▓  if you like it: star the repo, share the demo, support the artists  ▓▒░"))
L.append("")
L.append("▓" * W)
L.append("▒" * W)
L.append("░" * W)
L.append("")

text = "\r\n".join(L)
for i, ln in enumerate(L):
    assert len(ln) <= W, (i, len(ln), ln)
with open(os.path.join(ROOT, "R00T_ACCS.nfo"), "wb") as f:
    f.write(text.encode("cp437"))

links = []
if ARGS.repo:
    owner, name = ARGS.repo.split("/", 1)
    links += [f"**[Download R00T_ACCS.exe](https://github.com/{ARGS.repo}/releases/latest/download/R00T_ACCS.exe)**",
              f"[download page](https://{owner}.github.io/{name}/)"]
if ARGS.youtube:
    links.append(f"[watch the video]({ARGS.youtube})")
head = ["# R00T_ACCS", "", "A real-time, full-screen synthwave-gets-hacked demo. Every pixel is computed live on your GPU.", ""]
if links:
    head += [" &middot; ".join(links), ""]
md = ["<!-- generated by tools/make_nfo.py -->", ""] + head + ["```text"] + L + ["```", "",
      "<sub>The same text ships as `R00T_ACCS.nfo` (CP437) - open it with an NFO viewer for the full effect.</sub>", ""]
with open(os.path.join(ROOT, "README.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(md))
print("wrote R00T_ACCS.nfo + README.md,", len(L), "lines, exe size:", exe_size())
