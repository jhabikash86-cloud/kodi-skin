"""Generate the ATV Minimal skin textures (pure Python, no Pillow)."""
import math
import os
import struct
import sys
import zlib

OUT = sys.argv[1]


def write_png(path, w, h, px):
    """px: function(x, y) -> (r, g, b, a) floats 0..255."""
    raw = bytearray()
    for y in range(h):
        raw.append(0)
        for x in range(w):
            r, g, b, a = px(x, y)
            raw += bytes((int(r), int(g), int(b), max(0, min(255, int(round(a))))))

    def chunk(tag, data):
        c = struct.pack('>I', len(data)) + tag + data
        return c + struct.pack('>I', zlib.crc32(tag + data) & 0xFFFFFFFF)

    png = b'\x89PNG\r\n\x1a\n'
    png += chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 6, 0, 0, 0))
    png += chunk(b'IDAT', zlib.compress(bytes(raw), 9))
    png += chunk(b'IEND', b'')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'wb') as f:
        f.write(png)


def rrect_sdf(x, y, w, h, r):
    """Signed distance to a rounded rect (negative inside)."""
    cx, cy = w / 2, h / 2
    qx = abs(x - cx) - (cx - r)
    qy = abs(y - cy) - (cy - r)
    outside = math.hypot(max(qx, 0), max(qy, 0))
    inside = min(max(qx, qy), 0)
    return outside + inside - r


def rrect(path, w, h, r):
    """White rounded rect, 1px anti-aliased edge (usable as mask or 9-slice fill)."""
    def px(x, y):
        d = rrect_sdf(x + 0.5, y + 0.5, w, h, r)
        return 255, 255, 255, 255 * min(1, max(0, 0.5 - d))
    write_png(path, w, h, px)


def ring(path, w, h, r, t):
    """Rounded-rect outline of thickness t."""
    def px(x, y):
        d = rrect_sdf(x + 0.5, y + 0.5, w, h, r)
        a = min(1, max(0, 0.5 - d)) * min(1, max(0, d + t + 0.5))
        return 255, 255, 255, 255 * a
    write_png(path, w, h, px)


def shadow(path, size, pad, r, blur, strength):
    """Soft drop shadow: a rounded rect inset by `pad`, faded over `blur` px."""
    inner = size - 2 * pad

    def px(x, y):
        d = rrect_sdf(x + 0.5 - pad, y + 0.5 - pad, inner, inner, r)
        t = min(1, max(0, d / blur))
        a = (1 - t) ** 2.2 if d > 0 else 1
        return 0, 0, 0, 255 * strength * a
    write_png(path, size, size, px)


def circle(path, s):
    rrect(path, s, s, s / 2)


def play_icon(path, s):
    """Rounded play triangle, supersampled."""
    ss = 4
    ax, ay = 0.30 * s, 0.20 * s
    bx, by = 0.30 * s, 0.80 * s
    cx, cy = 0.82 * s, 0.50 * s

    def inside(x, y):
        def side(px_, py_, qx, qy):
            return (qx - px_) * (y - py_) - (qy - py_) * (x - px_)
        s1, s2, s3 = side(ax, ay, bx, by), side(bx, by, cx, cy), side(cx, cy, ax, ay)
        return (s1 <= 0 and s2 <= 0 and s3 <= 0) or (s1 >= 0 and s2 >= 0 and s3 >= 0)

    def px(x, y):
        n = sum(inside(x + (i + 0.5) / ss, y + (j + 0.5) / ss) for i in range(ss) for j in range(ss))
        return 255, 255, 255, 255 * n / (ss * ss)
    write_png(path, s, s, px)


def plus_icon(path, s, t):
    """Plus sign (used for 'More Info' style secondary buttons)."""
    def px(x, y):
        c = s / 2
        a = 0
        if abs(x + 0.5 - c) <= t / 2 and abs(y + 0.5 - c) <= s * 0.32:
            a = 1
        if abs(y + 0.5 - c) <= t / 2 and abs(x + 0.5 - c) <= s * 0.32:
            a = 1
        return 255, 255, 255, 255 * a
    write_png(path, s, s, px)


def vgradient(path, w, h, top_a, bottom_a, gamma=1.6):
    def px(x, y):
        t = (y + 0.5) / h
        return 0, 0, 0, 255 * (top_a + (bottom_a - top_a) * t ** gamma)
    write_png(path, w, h, px)


def hgradient(path, w, h, left_a, right_a, gamma=1.4):
    def px(x, y):
        t = (x + 0.5) / w
        return 0, 0, 0, 255 * (left_a + (right_a - left_a) * t ** (1 / gamma))
    write_png(path, w, h, px)


M = os.path.join(OUT, 'media', 'atv')
# Masks (used via <texture diffuse="...">; they stretch with the control, so one per aspect)
rrect(f'{M}/mask_poster.png', 240, 360, 16)       # 2:3 posters
rrect(f'{M}/mask_landscape.png', 480, 270, 16)    # 16:9 tiles
circle(f'{M}/mask_circle.png', 256)               # people / avatars
# 9-slice fills (use border="N" so corners never stretch)
rrect(f'{M}/rounded16.png', 64, 64, 16)           # border="16"
rrect(f'{M}/rounded12.png', 48, 48, 12)           # border="12"
rrect(f'{M}/rounded24.png', 96, 96, 24)           # dialog panels   border="24"
# Focus shadow (9-slice, border="64")
shadow(f'{M}/shadow.png', 192, 40, 18, 40, 0.75)
# Icons
play_icon(f'{M}/icon_play.png', 64)
plus_icon(f'{M}/icon_plus.png', 64, 7)
circle(f'{M}/dot.png', 16)
# Gradients
vgradient(f'{M}/grad_bottom.png', 8, 512, 0.0, 1.0)
vgradient(f'{M}/grad_top.png', 8, 256, 0.85, 0.0, 0.8)
hgradient(f'{M}/grad_left.png', 512, 8, 0.92, 0.0)
print('ok')
# Capsules sized to their controls so the 9-slice border never exceeds the height
rrect(f'{M}/pill_56.png', 112, 56, 28)   # nav tabs        border="28"
rrect(f'{M}/pill_68.png', 136, 68, 34)   # hero buttons    border="34"
rrect(f'{M}/pill_72.png', 144, 72, 36)   # nav capsule     border="36"
rrect(f'{M}/pill_84.png', 168, 84, 42)   # search field    border="42"
print('pills ok')
circle(f'{M}/nib.png', 64)                        # scrubber playhead
# Progress bars at their real height, so the rounded ends never get stretched
rrect(f'{M}/bar8.png', 16, 8, 4)                  # player scrubber      border="4,0,4,0"
rrect(f'{M}/bar6.png', 12, 6, 3)                  # Up Next progress     border="3,0,3,0"


def check_icon(path, s):
    """Tick mark, drawn as two thick strokes with round-ish ends (supersampled)."""
    ss = 4
    pts = [((0.22 * s, 0.53 * s), (0.42 * s, 0.72 * s)), ((0.42 * s, 0.72 * s), (0.78 * s, 0.30 * s))]
    t = s * 0.085

    def near(x, y, a, b):
        (x1, y1), (x2, y2) = a, b
        dx, dy = x2 - x1, y2 - y1
        L = dx * dx + dy * dy
        u = max(0, min(1, ((x - x1) * dx + (y - y1) * dy) / L))
        px, py = x1 + u * dx, y1 + u * dy
        return math.hypot(x - px, y - py) <= t

    def px(x, y):
        n = 0
        for i in range(ss):
            for j in range(ss):
                sx, sy = x + (i + 0.5) / ss, y + (j + 0.5) / ss
                if any(near(sx, sy, a, b) for a, b in pts):
                    n += 1
        return 255, 255, 255, 255 * n / (ss * ss)
    write_png(path, s, s, px)


check_icon(f'{M}/icon_check.png', 48)
print('check ok')


def switch(path, on, w=76, h=44, knob=15):
    """Toggle pill with the knob punched out as a hole.

    The knob is transparent rather than painted, so one texture works on any
    background: colordiffuse the pill white on a dark row and dark on a focused
    (white) row, and the knob always shows the surface behind it.
    """
    r = h / 2
    kx = w - r if on else r
    ss = 3

    def px(x, y):
        a = 0.0
        for i in range(ss):
            for j in range(ss):
                sx, sy = x + (i + 0.5) / ss, y + (j + 0.5) / ss
                inside = rrect_sdf(sx, sy, w, h, r) <= 0
                in_knob = math.hypot(sx - kx, sy - r) <= knob
                if inside and not in_knob:
                    a += 1
        return 255, 255, 255, 255 * a / (ss * ss)
    write_png(path, w, h, px)


def chevron(path, s=48, t=None):
    """A '>' disclosure mark, two strokes meeting at a point."""
    t = t or s * 0.075
    x0, x1 = s * 0.36, s * 0.64
    pts = [((x0, s * 0.24), (x1, s * 0.50)), ((x1, s * 0.50), (x0, s * 0.76))]
    ss = 4

    def near(x, y, a, b):
        (x1_, y1), (x2, y2) = a, b
        dx, dy = x2 - x1_, y2 - y1
        L = dx * dx + dy * dy
        u = max(0, min(1, ((x - x1_) * dx + (y - y1) * dy) / L))
        return math.hypot(x - (x1_ + u * dx), y - (y1 + u * dy)) <= t

    def px(x, y):
        n = sum(1 for i in range(ss) for j in range(ss)
                if any(near(x + (i + 0.5) / ss, y + (j + 0.5) / ss, a, b) for a, b in pts))
        return 255, 255, 255, 255 * n / (ss * ss)
    write_png(path, s, s, px)


switch(f'{M}/switch_on.png', True)
switch(f'{M}/switch_off.png', False)
chevron(f'{M}/icon_chevron.png')
print('switches ok')
