"""Generates assets/icon.ico (a tiny terminal-style 'R' tile). Run by build_exe.ps1."""
import os

from PIL import Image, ImageDraw, ImageFont

here = os.path.dirname(os.path.abspath(__file__))
out = os.path.join(os.path.dirname(here), "assets", "icon.ico")
S = 256
im = Image.new("RGBA", (S, S), (8, 2, 22, 255))
d = ImageDraw.Draw(im)
d.rectangle((6, 6, S - 7, S - 7), outline=(255, 45, 149, 255), width=8)
try:
    f = ImageFont.truetype(r"C:\Windows\Fonts\consolab.ttf", 150)
except Exception:
    f = ImageFont.load_default(150)
d.text((S // 2, S // 2 - 6), "R", font=f, fill=(0, 229, 255, 255), anchor="mm")
d.text((S // 2, S - 40), "00T", font=ImageFont.truetype(r"C:\Windows\Fonts\consolab.ttf", 38) if os.path.exists(r"C:\Windows\Fonts\consolab.ttf") else f,
       fill=(255, 225, 74, 255), anchor="mm")
im.save(out, sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
print("wrote", out)
