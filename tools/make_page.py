"""Generates docs/index.html (the GitHub Pages download page) from tools/page_template.html.

    python tools/make_page.py --repo OWNER/NAME [--youtube https://youtu.be/...] [--size "87 MB"]

* the exe size defaults to dist/R00T_ACCS.exe if it exists
* --youtube adds a link to the video above the screenshots
"""
import argparse
import html
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ap = argparse.ArgumentParser()
ap.add_argument("--repo", required=True, help="GitHub OWNER/NAME")
ap.add_argument("--youtube", default="")
ap.add_argument("--size", default="")
ap.add_argument("--version", default="")
a = ap.parse_args()
owner, name = a.repo.split("/", 1)

size = a.size
if not size:
    p = os.path.join(ROOT, "dist", "R00T_ACCS.exe")
    size = f"{os.path.getsize(p) / 1048576:.0f} MB" if os.path.exists(p) else "~90 MB"
version = a.version
if not version:
    import re
    m = re.search(r'__version__ = "([^"]+)"', open(os.path.join(ROOT, "r00t", "__init__.py"), encoding="utf-8").read())
    version = m.group(1) if m else "1.0.0"

yt = ""
if a.youtube:
    yt = f'<p class="hint">&#9654; <a href="{html.escape(a.youtube)}" rel="noopener">watch the video</a></p>'

page = open(os.path.join(ROOT, "tools", "page_template.html"), encoding="utf-8").read()
for k, v in {"{{REPO}}": a.repo, "{{OWNER}}": owner, "{{NAME}}": name, "{{EXESIZE}}": size,
             "{{VERSION}}": version, "{{YOUTUBE_BLOCK}}": yt}.items():
    page = page.replace(k, v)
os.makedirs(os.path.join(ROOT, "docs"), exist_ok=True)
with open(os.path.join(ROOT, "docs", "index.html"), "w", encoding="utf-8", newline="\n") as f:
    f.write(page)
print("wrote docs/index.html  repo", a.repo, "size", size)
