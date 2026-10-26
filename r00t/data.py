"""Timed text tables: lyric lines, vocal chops, glass shatters."""

# captions: (text, t0, t1, colour hex, y fraction)
CAPTIONS = [
    ("NEON LIGHTS IN THE REARVIEW MIRROR", 11.59, 15.7, "#ff5ce1"),
    ("CHASING TIME, THE VISION GETS CLEARER", 16.95, 20.95, "#4df6ff"),
    ("MIDNIGHT CITY, GLOWING BRIGHT", 21.0, 25.6, "#ff5ce1"),
    ("WE OWN THE NIGHT", 26.11, 29.5, "#ffffff"),
    ("WE OWN THE NIGHT", 29.9, 36.4, "#4df6ff"),
    ("SYSTEM FAILING, GEARS ARE SHIFTING", 37.87, 40.5, "#ff7a59"),
    ("GRAVITY IS SLOWLY LIFTING", 40.45, 43.2, "#ffd58a"),
    ("HOLD ON TIGHT...", 43.1, 44.7, "#4df6ff"),
    ("HOLD ON TIGHT...", 44.7, 47.0, "#ff5ce1"),
    ("LEAVE THE SHADOWS IN THE PAST", 104.69, 107.3, "#9fb6ff"),
    ("SYSTEM COOLING...", 151.18, 154.0, "#8fd8ff"),
    ("NEON FADING...", 154.01, 157.0, "#ff8fd0"),
    ("(WE OWN THE NIGHT...)", 156.7, 158.4, "#ffd58a"),
    ("(WE OWN THE NIGHT...)", 158.4, 160.0, "#ffd58a"),
    ("(WE OWN THE NIGHT...)", 160.0, 165.5, "#ffd58a"),
]

# chop words: (text, t, hold_seconds or None=until next, kind)  kind: 'letter' | 'word'
CHOPS = []
for ch, t in zip("ACCELERATE", [58.31, 58.97, 59.49, 60.18, 60.83, 61.15, 61.94, 62.53, 62.86, 63.51]):
    CHOPS.append((ch, t, None, "letter"))
CHOPS += [
    ("ACCELERATE!", 64.2, 1.5, "word"),
    ("OWN", 79.75, None, "word"), ("THE", 80.08, None, "word"), ("NIGHT!", 80.59, 0.6, "word"),
    ("OWN", 81.26, None, "word"), ("THE", 81.93, None, "word"), ("NIGHT!", 82.45, 0.9, "word"),
    ("OWN THE NIGHT!", 83.9, 1.9, "word"),
    ("SYSTEM", 90.86, None, "word"), ("OVERLOAD!", 91.74, 1.6, "word"),
    ("BREAK", 101.76, None, "word"), ("THE", 102.28, None, "word"), ("GLASS!", 102.62, 0.8, "word"),
    ("HIT", 103.5, None, "word"), ("THE", 103.68, None, "word"), ("GAS!", 103.98, 0.7, "word"),
    ("IN THE PAST", 107.36, 1.3, "echo"), ("IN THE PAST", 109.2, 1.3, "echo"), ("IN THE PAST", 111.0, 1.3, "echo"),
    ("ACCELERATE!", 47.3, 0.9, "word"),
    ("OVERLOAD!", 123.28, 1.2, "word"),
    ("BREAK", 127.30, None, "word"), ("THE", 127.78, None, "word"), ("GLASS!", 128.28, 1.1, "word"),
    ("HOLD", 135.69, None, "word"), ("ON!", 136.02, 1.2, "word"),
]
CHOPS.sort(key=lambda c: c[1])
SHATTERS = [(102.62, 1.0), (103.98, 0.55), (128.28, 1.25), (123.28, 0.5), (136.02, 0.7)]
