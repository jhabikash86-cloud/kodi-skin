"""Generate the skin's own artwork: resources/icon.png and resources/fanart.png.

Run from the skin folder:  python3 tools/gen_icon.py

Kodi shows these in the skin list and the add-on info page; without them the skin
appears as a blank tile. Screenshots are real captures, added separately.
"""
import math
import os
import struct
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'resources')


def write_png(path, w, h, px):
    raw = bytearray()
    for y in range(h):
        raw.append(0)
        for x in range(w):
            r, g, b, a = px(x, y)
            raw += bytes((int(max(0, min(255, r))), int(max(0, min(255, g))),
                          int(max(0, min(255, b))), int(max(0, min(255, a)))))

    def chunk(tag, data):
        return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data) & 0xFFFFFFFF)

    png = (b'\x89PNG\r\n\x1a\n'
           + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 6, 0, 0, 0))
           + chunk(b'IDAT', zlib.compress(bytes(raw), 9))
           + chunk(b'IEND', b''))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'wb') as f:
        f.write(png)


def rrect_sdf(x, y, w, h, r):
    qx, qy = abs(x - w / 2) - (w / 2 - r), abs(y - h / 2) - (h / 2 - r)
    return math.hypot(max(qx, 0), max(qy, 0)) + min(max(qx, qy), 0) - r


def icon(path, size=512):
    """Dark rounded tile with the skin's play glyph, matching the buttons in the UI."""
    radius = size * 0.22
    cx, cy = size * 0.54, size / 2
    tri = ((size * 0.40, size * 0.30), (size * 0.40, size * 0.70), (size * 0.72, size * 0.50))
    ring_r, ring_w = size * 0.30, size * 0.035

    def inside_tri(x, y):
        def side(ax, ay, bx, by):
            return (bx - ax) * (y - ay) - (by - ay) * (x - ax)
        s = [side(*tri[0], *tri[1]), side(*tri[1], *tri[2]), side(*tri[2], *tri[0])]
        return all(v <= 0 for v in s) or all(v >= 0 for v in s)

    ss = 3

    def px(x, y):
        # tile: soft vertical gradient from #1C1C1E to #0B0B0D
        t = y / size
        base = (28 - 17 * t, 28 - 17 * t, 30 - 17 * t)
        d = rrect_sdf(x + 0.5, y + 0.5, size, size, radius)
        alpha = 255 * min(1, max(0, 0.5 - d))
        hits = ring = 0
        for i in range(ss):
            for j in range(ss):
                sx, sy = x + (i + 0.5) / ss, y + (j + 0.5) / ss
                if inside_tri(sx, sy):
                    hits += 1
                dr = abs(math.hypot(sx - cx, sy - cy) - ring_r)
                if dr <= ring_w / 2:
                    ring += 1
        mark = max(hits, ring * 0.55) / (ss * ss)
        r = base[0] + (255 - base[0]) * mark
        g = base[1] + (255 - base[1]) * mark
        b = base[2] + (255 - base[2]) * mark
        return r, g, b, alpha
    write_png(path, size, size, px)


def fanart(path, w=1920, h=1080):
    """Quiet dark backdrop with a soft glow, in the skin's palette."""
    def px(x, y):
        t = ((x / w - 0.32) ** 2 + (y / h - 0.42) ** 2) ** 0.5
        glow = max(0, 1 - t * 1.5) ** 2.4
        v = 11 + 26 * glow
        return v, v, v + 2 * glow, 255
    write_png(path, w, h, px)


if __name__ == '__main__':
    icon(os.path.join(OUT, 'icon.png'))
    fanart(os.path.join(OUT, 'fanart.png'))
    print('wrote resources/icon.png and resources/fanart.png')
