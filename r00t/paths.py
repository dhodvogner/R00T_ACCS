"""Asset lookup that works from source and from a PyInstaller bundle, plus font loading with fallbacks."""
import os
import sys

from PIL import ImageFont


def base_dir():
    # PyInstaller one-file unpacks next to sys._MEIPASS; from source we live in <repo>/r00t/
    return getattr(sys, "_MEIPASS", None) or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def asset(name):
    return os.path.join(base_dir(), "assets", name)


def user_dir():
    """folder next to the exe (or the repo) for logs / screenshots"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return base_dir()


_WARNED = set()


def load_font(path, size, variation=None):
    """TrueType font from a Windows system path; falls back to Pillow's bundled font if it is missing."""
    try:
        f = ImageFont.truetype(path, int(size))
        if variation:
            try:
                f.set_variation_by_name(variation)
            except Exception:
                pass
        return f
    except Exception:
        if path not in _WARNED:
            _WARNED.add(path)
            print(f"[r00t] font not found: {path} -> using fallback")
        return ImageFont.load_default(int(size))
