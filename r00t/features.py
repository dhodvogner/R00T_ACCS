"""Per-frame (60 fps) audio feature arrays for the visualizer."""
import numpy as np

from .paths import asset

FPS = 60


def hit_env(idx, strength, n, tau, min_s=0.0, gain=0.75, base=0.45):
    env = np.zeros(n, np.float32)
    k = np.arange(int(tau * 8))
    for i, s in zip(idx, strength):
        if s < min_s:
            continue
        a = min(1.35, base + gain * float(s))
        e = a * np.exp(-k / tau)
        j = min(n, i + len(k))
        env[i:j] = np.maximum(env[i:j], e[: j - i])
    return env


class Feat:
    def __init__(self):
        d = np.load(asset("features.npz"))
        self.n = int(d["T"])
        n = self.n
        self.bass, self.lowmid, self.mid, self.high, self.rms = (d[k] for k in ("bass", "lowmid", "mid", "high", "rms"))
        self.bass_s, self.rms_s = d["bass_s"], d["rms_s"]
        self.kick = hit_env(d["kick_i"], d["kick_s"], n, 4.5, min_s=0.12)
        self.snare = hit_env(d["snare_i"], d["snare_s"], n, 3.5, min_s=0.40, base=0.55)
        self.hat = hit_env(d["hat_i"], d["hat_s"], n, 2.2, min_s=0.18, base=0.4)
        self.spec = d["spec"]
        self.beat_t = d["beat_t"]
        self.kick_t = d["kick_i"] / FPS
        self.kick_str = d["kick_s"]
        self.snare_t = d["snare_i"] / FPS
        self.snare_str = d["snare_s"]

    def at(self, i):
        i = min(max(i, 0), self.n - 1)
        return dict(bass=float(self.bass[i]), lowmid=float(self.lowmid[i]), mid=float(self.mid[i]),
                    high=float(self.high[i]), rms=float(self.rms[i]), bass_s=float(self.bass_s[i]),
                    rms_s=float(self.rms_s[i]), kick=float(self.kick[i]), snare=float(self.snare[i]),
                    hat=float(self.hat[i]), spec=self.spec[i])

    def nearest_beat(self, t):
        j = int(np.argmin(np.abs(self.beat_t - t)))
        return float(self.beat_t[j])
