"""Writes the skin's navigation sounds (extras/uisounds/resource.uisounds.atv, which extras/setup.py
installs): tvOS-quiet ticks, made here rather
than borrowed so the skin can ship them. A tick for moving, a rounder tap for select, a
falling tone for back - each a few tens of milliseconds, well below programme level.

    python3 tools/gen_sounds.py
"""
import math
import os
import random
import struct
import wave

RATE = 48000
OUT = os.path.join(os.path.dirname(__file__), '..', 'extras', 'uisounds', 'resource.uisounds.atv', 'resources')


def write(name, samples):
    with wave.open(os.path.join(OUT, name), 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(b''.join(struct.pack('<h', int(max(-1, min(1, s)) * 32767)) for s in samples))


def tone(ms, partials, decay_ms, level_db, glide=1.0, noise=0.0, seed=1):
    """Partials (frequency, weight) under an exponential decay, 1 ms fade in, a short
    burst of filtered noise at the front for the 'click' of a physical key."""
    random.seed(seed)
    n = int(RATE * ms / 1000)
    gain = 10 ** (level_db / 20)
    out, phase, lp = [], [0.0] * len(partials), 0.0
    for i in range(n):
        t = i / RATE
        env = math.exp(-t * 1000 / decay_ms) * min(1.0, i / (RATE * 0.001))
        env *= min(1.0, (n - i) / (RATE * 0.004))            # no click at the end
        f_scale = glide ** (i / n)
        s = 0.0
        for k, (f, weight) in enumerate(partials):
            phase[k] += 2 * math.pi * f * f_scale / RATE
            s += weight * math.sin(phase[k])
        if noise and t < 0.004:
            lp += 0.35 * (random.uniform(-1, 1) - lp)
            s += noise * lp * (1 - t / 0.004)
        out.append(s * env * gain)
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    # moving focus: a tiny, bright, woody tick
    write('cursor.wav', tone(45, [(2100, 0.7), (4300, 0.2)], 7, -24, noise=0.6, seed=2))
    # select: lower and rounder, a touch longer
    write('select.wav', tone(90, [(1250, 0.7), (2500, 0.25)], 16, -20, noise=0.4, seed=3))
    # back: a short fall in pitch
    write('back.wav', tone(110, [(1500, 0.8), (3000, 0.15)], 26, -23, glide=0.6, seed=4))
    # opening a dialog or a page's menu: a soft, low tap
    write('open.wav', tone(80, [(900, 0.8), (1800, 0.2)], 18, -24, noise=0.3, seed=5))


if __name__ == '__main__':
    main()
