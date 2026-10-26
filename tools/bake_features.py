"""Bake the audio-feature file the demo reads at runtime (so the exe needs no audio analysis at all).

    python tools/bake_features.py path/to/track.mp3 [out.npz]

Writes per-frame (60 fps) band energies, kick / snare / hi-hat hit envelopes, a 64-band spectrum and the beat grid.
The choreography (r00t/choreo*.py) is hand-timed to the bundled track, so a different song needs its own timeline.
Requires librosa + scipy (see requirements-dev.txt).
"""
import os
import sys

import librosa
import numpy as np
from scipy.signal import find_peaks

src = sys.argv[1]
dst = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "features.npz")
SR, FPS = 44100, 60
HOP = SR // FPS

y, _ = librosa.load(src, sr=SR, mono=True)
S = np.abs(librosa.stft(y, n_fft=2048, hop_length=HOP))
freqs = librosa.fft_frequencies(sr=SR, n_fft=2048)
T = S.shape[1]


def band(lo, hi):
    return S[(freqs >= lo) & (freqs < hi)].sum(axis=0)


def norm(x, pct=99.5):
    return x / (np.percentile(x, pct) + 1e-9)


def smooth_ad(x, att, dec):
    out, v = np.zeros_like(x), 0.0
    for i, s in enumerate(x):
        v = v + (s - v) * (att if s > v else dec)
        out[i] = v
    return out


bass, lowmid, mid, high, rms = norm(band(30, 140)), norm(band(140, 500)), norm(band(500, 3000)), norm(band(3000, 12000)), norm(S.sum(axis=0))


def flux(x):
    return np.maximum(0, np.diff(x, prepend=x[0]))


def peaks(f, height, dist_s):
    f = f / (np.percentile(f, 99.7) + 1e-9)
    pk, _ = find_peaks(f, height=height, distance=int(dist_s * FPS))
    return pk, f[pk]


kick_i, kick_s = peaks(flux(np.convolve(band(35, 130), np.ones(2) / 2, mode="same")), 0.18, 0.12)
snare_i, snare_s = peaks(flux(band(1500, 6000)), 0.22, 0.12)
hat_i, hat_s = peaks(flux(band(8000, 16000)), 0.25, 0.05)
all_i, all_s = peaks(flux(S.sum(axis=0)), 0.25, 0.08)
edges = np.geomspace(40, 14000, 65)
spec = np.zeros((T, 64), np.float32)
for b in range(64):
    spec[:, b] = S[(freqs >= edges[b]) & (freqs < edges[b + 1])].sum(axis=0)
spec = np.clip(np.log1p(spec * 3.0) / (np.percentile(np.log1p(spec * 3.0), 99.5) + 1e-9), 0, 1.2).astype(np.float32)
_, beats = librosa.beat.beat_track(y=y, sr=SR, hop_length=HOP)
np.savez_compressed(dst, fps=FPS, T=T, bass=bass.astype(np.float32), lowmid=lowmid.astype(np.float32), mid=mid.astype(np.float32),
                    high=high.astype(np.float32), rms=rms.astype(np.float32), bass_s=smooth_ad(bass, 0.6, 0.18).astype(np.float32),
                    rms_s=smooth_ad(rms, 0.4, 0.06).astype(np.float32), kick_i=kick_i, kick_s=kick_s, snare_i=snare_i, snare_s=snare_s,
                    hat_i=hat_i, hat_s=hat_s, all_i=all_i, all_s=all_s, spec=spec, beat_t=beats / FPS)
print("wrote", dst, "frames", T, "kicks", len(kick_i), "snares", len(snare_i))
