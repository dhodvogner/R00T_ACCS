# Notice: assets, credits and third-party software

## What the MIT license covers
Only the source code in this repository (`r00t/`, `tools/`, `build_exe.ps1`, `docs/` page code). See `LICENSE`.

## Assets (NOT covered by the MIT license)
| file(s) | what | provenance |
|---|---|---|
| `assets/song.mp3` | the track "We Own the Night" | music by **hodiloves**, made with **Suno**. Suno's terms govern commercial use; check them for your plan before redistributing the track. |
| `assets/atlas.png` (+ `atlas.json`) | sprite atlas: neon retro objects, silhouettes, skulls, reapers, a hooded figure | generated with **fal.ai** image models, then cut out and packed locally |
| `assets/dance_skel.mp4`, `assets/dance_hood.mp4` | two 5 s dancer loops used as glitch/ASCII source material | generated with **fal.ai** (FLUX 3 Max text-to-video) |
| `assets/glyph_*.png`, `assets/features.npz`, `assets/icon.ico` | glyph atlases, baked audio analysis, app icon | produced by this project's own scripts |
| `docs/img/*.jpg` | screenshots of the demo | captured from the demo itself |

Unless a file says otherwise, the music and visual assets are (c) hodiloves, **all rights reserved**: you may run and share the
unmodified demo, but please do not re-upload the track or the artwork on their own. *(Owner: adjust this section to the terms you want.)*

## Fonts
Text is rendered from fonts that ship with Windows (Bahnschrift, Consolas, MS Gothic, Segoe UI). They are **not** bundled in this repository
or in the exe; if a font is missing the app falls back to a built-in font.

## Third-party software (bundled into the exe by PyInstaller)
| package | license |
|---|---|
| pygame / SDL2 | LGPL-2.1 / zlib |
| moderngl, glcontext | MIT |
| NumPy | BSD-3-Clause |
| Pillow | HPND |
| OpenCV (opencv-python-headless) | Apache-2.0 (+ FFmpeg components under LGPL) |
| PyInstaller (bootloader) | GPL-2.0 with the PyInstaller exception for bundled apps |

The shader code adapts public-domain / permissive techniques: simplex noise by Ian McEwan (Ashima Arts, MIT), a raymarched KIFS glass
scene adapted from a shader supplied by the author, and a block-ASCII glyph mapping.
