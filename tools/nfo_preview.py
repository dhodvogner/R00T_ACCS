"""Renders R00T_ACCS.nfo to screenshots/nfo_preview.png (dev helper: shows what an NFO viewer would show)."""
import os

from PIL import Image, ImageDraw, ImageFont

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
text = open(os.path.join(root, "R00T_ACCS.nfo"), "rb").read().decode("cp437")
lines = text.split("\r\n")
f = ImageFont.truetype(r"C:\Windows\Fonts\consola.ttf", 16)
cw = int(f.getlength("M"))
ch = 19
im = Image.new("RGB", (cw * 80, ch * (len(lines) + 2)), (12, 8, 24))
d = ImageDraw.Draw(im)
for i, ln in enumerate(lines):
    for j, c in enumerate(ln):
        col = (0, 229, 255)
        if c in "\u2588\u2593\u2592\u2591":
            col = (255, 45, 149) if c in "\u2588\u2593" else (138, 43, 255)
        elif c in "\u2550\u2551\u2554\u2557\u255a\u255d\u2560\u2563":
            col = (255, 225, 74)
        d.text((cw + j * cw, ch + i * ch), c, font=f, fill=col)
os.makedirs(os.path.join(root, "screenshots"), exist_ok=True)
out = os.path.join(root, "screenshots", "nfo_preview.png")
im.save(out)
print(out, im.size)
