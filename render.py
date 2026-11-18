#!/usr/bin/env python3
"""Ray tracer for the news-image-20261117 entry (Python stdlib only).

Scene: "The Day the Bridge Fell" — dusk over a strait on 17 Nov 2026.
A bridge span collapses into the sea after a strike (Kerch Bridge, the
day's lead story), an oil tanker burns in the strait below (Hormuz mines,
story two), and a lone boatman watches from a small boat in the
foreground — threat, victim, witness. One consistent dusk palette:
deep blue sea and sky, warm orange firelight, dark steel.

Usage: python3 render.py [--size N] [--out entry.png]
Deterministic: no unseeded randomness; rows are computed in parallel
and assembled in order.
"""
import math
import os
import struct
import sys
import zlib
from multiprocessing import Pool

# ---------------------------------------------------------------- vector --
def vsub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def vadd(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def vscale(a, s):
    return (a[0] * s, a[1] * s, a[2] * s)


def vdot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def vcross(a, b):
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def vlen(a):
    return math.sqrt(vdot(a, a))


def vnorm(a):
    l = vlen(a)
    return (a[0] / l, a[1] / l, a[2] / l) if l > 0 else (0.0, 0.0, 0.0)


def vreflect(d, n):
    k = 2.0 * vdot(d, n)
    return (d[0] - k * n[0], d[1] - k * n[1], d[2] - k * n[2])


def lerp(a, b, t):
    return (a[0] + (b[0] - a[0]) * t,
            a[1] + (b[1] - a[1]) * t,
            a[2] + (b[2] - a[2]) * t)


def clamp(x, lo, hi):
    return lo if x < lo else hi if x > hi else x


# -------------------------------------------------------------- materials --
# mat = (color, amb, diff, spec, shin, refl, emis, alpha, cast_shadow)
# alpha < 1 means smoke: blends with what lies behind it.
def mat(color, amb=0.35, diff=0.75, spec=0.25, shin=40.0, refl=0.0,
        emis=(0.0, 0.0, 0.0), alpha=1.0, shadow=True):
    return (color, amb, diff, spec, shin, refl, emis, alpha, shadow)


SEA = mat((0.035, 0.07, 0.11), amb=0.5, diff=0.45, spec=0.7, shin=90.0,
          refl=0.55)
STEEL = mat((0.24, 0.26, 0.30), amb=0.4, diff=0.7, spec=0.35, shin=50.0)
DARK_STEEL = mat((0.13, 0.13, 0.15), amb=0.4, diff=0.7, spec=0.2, shin=30.0)
HEADLAND = mat((0.05, 0.06, 0.10), amb=0.6, diff=0.3, spec=0.0)
RUST = mat((0.38, 0.13, 0.09), amb=0.6, diff=0.85, spec=0.25, shin=35.0)
TANK = mat((0.52, 0.50, 0.46), amb=0.4, diff=0.7, spec=0.3, shin=40.0)
WHITE = mat((0.60, 0.58, 0.55), amb=0.4, diff=0.7, spec=0.2, shin=30.0)
WOOD = mat((0.35, 0.22, 0.13), amb=0.65, diff=0.7, spec=0.15, shin=20.0)
FIGURE = mat((0.14, 0.11, 0.10), amb=0.6, diff=0.6, spec=0.0)
CAR_RED = mat((0.45, 0.10, 0.08), amb=0.4, diff=0.7, spec=0.5, shin=60.0)
FIRE = mat((0.0, 0.0, 0.0), spec=0.0, emis=(2.2, 0.5, 0.06), alpha=1.0,
          shadow=False)
FIRE_SOFT = mat((0.0, 0.0, 0.0), spec=0.0, emis=(1.5, 0.38, 0.06),
                alpha=1.0, shadow=False)
TRAIL = mat((0.0, 0.0, 0.0), spec=0.0, emis=(1.2, 0.55, 0.18), alpha=1.0,
            shadow=False)
LANTERN = mat((0.0, 0.0, 0.0), spec=0.0, emis=(2.0, 1.2, 0.35), alpha=1.0,
              shadow=False)
SMOKE = mat((0.14, 0.12, 0.16), amb=0.7, diff=0.4, spec=0.0,
            alpha=0.15, shadow=False)
SMOKE_THIN = mat((0.12, 0.10, 0.14), amb=0.7, diff=0.4, spec=0.0,
                 alpha=0.08, shadow=False)
DEBRIS = mat((0.11, 0.11, 0.12), amb=0.45, diff=0.7, spec=0.2, shin=25.0)

# ------------------------------------------------------------- primitives --
# ('s', cx, cy, cz, r, mat)                       sphere
# ('b', cx, cy, cz, hx, hy, hz, R, mat)           oriented box,
#        R = 9 floats, rows of rotation matrix (local -> world)
# ('p', nx, ny, nz, d, mat)                       plane n.p = d
# ('c', cx, cz, r, y0, y1, mat)                   Y-axis cylinder + caps
PRIMS = []


def add_sphere(c, r, m):
    PRIMS.append(('s', c[0], c[1], c[2], r, m))


def add_box(c, h, rot, m):
    PRIMS.append(('b', c[0], c[1], c[2], h[0], h[1], h[2], rot, m))


def add_plane(n, d, m):
    PRIMS.append(('p', n[0], n[1], n[2], d, m))


def add_cyl(c, r, y0, y1, m):
    PRIMS.append(('c', c[0], c[1], r, y0, y1, m))


def rot_matrix(rx=0.0, ry=0.0, rz=0.0):
    """Rows of R = Rz * Ry * Rx (local -> world). Angles in radians."""
    cx, sx = math.cos(rx), math.sin(rx)
    cy, sy = math.cos(ry), math.sin(ry)
    cz, sz = math.cos(rz), math.sin(rz)
    # Rx
    rxm = (1, 0, 0, 0, cx, -sx, 0, sx, cx)
    # Ry
    rym = (cy, 0, sy, 0, 1, 0, -sy, 0, cy)
    # Rz
    rzm = (cz, -sz, 0, sz, cz, 0, 0, 0, 1)

    def mm(a, b):
        return tuple(sum(a[i * 3 + k] * b[k * 3 + j] for k in range(3))
                     for i in range(3) for j in range(3))
    return mm(rzm, mm(rym, rxm))


IDENT = (1, 0, 0, 0, 1, 0, 0, 0, 1)


def build_scene():
    # Sea (infinite plane y = 0)
    add_plane((0.0, 1.0, 0.0), 0.0, SEA)
    # Distant headland silhouette on the horizon
    add_box((0.0, 1.2, -55.0), (70.0, 1.2, 6.0), IDENT, HEADLAND)

    # ---- The bridge (runs along X at z = -10, deck at y = 14) ----
    # Intact deck, left of the break
    add_box((-16.0, 14.0, -10.0), (24.0, 0.8, 2.2), IDENT, STEEL)
    # Intact deck, right of the break
    add_box((31.0, 14.0, -10.0), (9.0, 0.8, 2.2), IDENT, STEEL)
    # Collapsed span: tilted down, far end in the water
    add_box((15.0, 8.5, -10.0), (7.5, 0.8, 2.2),
            rot_matrix(rz=math.radians(-40.0)), DARK_STEEL)
    # Broken stub at the left edge of the gap
    add_box((8.5, 12.5, -10.0), (1.6, 0.7, 2.2),
            rot_matrix(rz=math.radians(24.0)), DARK_STEEL)
    # Pillars
    for x in (-32.0, -18.0, -2.0, 30.0):
        add_box((x, 7.0, -10.0), (1.2, 7.0, 1.8), IDENT, STEEL)
    # Broken pillar, leaning where the span fell
    add_box((15.0, 3.5, -10.0), (1.2, 4.5, 1.8),
            rot_matrix(rz=math.radians(17.0)), DARK_STEEL)
    # Cars halted on the intact deck
    add_box((-6.0, 15.3, -10.0), (0.9, 0.5, 0.9), IDENT, CAR_RED)
    add_box((-3.0, 15.3, -10.0), (0.9, 0.5, 0.9), IDENT, DARK_STEEL)
    add_box((0.0, 15.3, -10.0), (0.9, 0.5, 0.9), IDENT, WHITE)

    # ---- The strike: fireball + missile trail + smoke ----
    add_sphere((12.5, 15.5, -10.0), 1.7, FIRE)
    add_sphere((10.8, 14.2, -10.0), 1.1, FIRE_SOFT)
    add_sphere((14.3, 14.3, -10.0), 1.0, FIRE_SOFT)
    add_sphere((12.0, 17.3, -10.0), 0.9, FIRE_SOFT)
    # Dotted missile trail coming down from the sky
    for i, t in enumerate((0.15, 0.38, 0.6, 0.82)):
        p = (20.0 + (12.5 - 20.0) * t, 40.0 + (15.5 - 40.0) * t,
             -25.0 + (-10.0 + 25.0) * t)
        add_sphere(p, 0.55 - i * 0.08, TRAIL)
    # Smoke column rising from the break (tight stack, heavy overlap;
    # upper puffs thinner, like dissipating smoke)
    for (x, y, z, r) in (
            (12.0, 18.5, -10.0, 3.0), (10.9, 20.3, -10.4, 3.5),
            (13.1, 22.1, -10.0, 4.0), (11.4, 23.9, -10.6, 4.5)):
        add_sphere((x, y, z), r, SMOKE)
    for (x, y, z, r) in (
            (13.0, 25.7, -10.0, 5.0),):
        add_sphere((x, y, z), r, SMOKE_THIN)

    # ---- The burning tanker (mid-ground, left) ----
    # Hull, listing to starboard
    add_box((-14.0, 1.2, 0.0), (9.0, 1.4, 2.6),
            rot_matrix(rx=math.radians(8.0)), RUST)
    # Deck tanks
    for x in (-19.0, -14.0, -9.0):
        add_cyl((x, 0.0), 1.6, 2.6, 5.2, TANK)
    # Superstructure + funnel
    add_box((-5.5, 3.6, 0.0), (1.6, 2.2, 2.2), IDENT, WHITE)
    add_box((-5.5, 6.4, 0.0), (0.7, 0.9, 1.0), IDENT, DARK_STEEL)
    # Deck fires
    add_sphere((-12.0, 4.6, 0.0), 1.4, FIRE)
    add_sphere((-9.5, 4.3, 0.0), 1.0, FIRE_SOFT)
    add_sphere((-16.0, 4.4, 0.0), 0.9, FIRE_SOFT)
    # Tanker smoke
    for (x, y, z, r) in ((-14.0, 7.5, 0.0, 2.4), (-13.0, 9.8, -0.5, 2.9),
                         (-15.0, 12.0, 0.0, 3.4)):
        add_sphere((x, y, z), r, SMOKE)
    for (x, y, z, r) in ((-13.5, 14.2, -0.5, 3.9),):
        add_sphere((x, y, z), r, SMOKE_THIN)

    # ---- The witness: small boat + lone figure + lantern (foreground) ----
    add_box((6.0, 0.5, 15.0), (2.2, 0.5, 0.85), IDENT, WOOD)
    add_cyl((6.0, 15.0), 0.09, 1.0, 4.5, WOOD)
    add_cyl((6.8, 15.0), 0.28, 1.0, 1.9, FIGURE)   # body
    add_sphere((6.8, 2.2, 15.0), 0.28, FIGURE)      # head
    add_sphere((5.2, 2.0, 15.0), 0.24, LANTERN)     # lantern

    # ---- Chaos details: debris near the collapse + wreckage afloat ----
    for (x, y, z, s, a) in (
            (10.5, 11.0, -9.0, 0.5, 0.5), (13.5, 9.0, -11.5, 0.4, -0.9),
            (16.0, 7.0, -9.5, 0.6, 0.3), (11.0, 6.5, -8.5, 0.35, 1.2),
            (18.5, 10.5, -11.0, 0.45, -0.4), (14.0, 12.5, -8.0, 0.3, 0.8),
            (20.0, 5.5, -9.0, 0.5, 1.9), (9.0, 9.5, -11.0, 0.4, -1.4)):
        add_box((x, y, z), (s, s * 0.6, s * 0.6),
                rot_matrix(ry=a, rz=a * 0.7), DEBRIS)
    for (x, z, a) in ((17.0, 2.0, 0.4), (21.0, 5.0, -0.7),
                      (15.0, -3.0, 1.1), (24.0, 1.0, 0.2)):
        add_box((x, 0.15, z), (1.2, 0.08, 0.4),
                rot_matrix(ry=a), DEBRIS)


# ---------------------------------------------------------------- lights --
SUN_DIR = vnorm((-0.55, 0.09, -1.0))      # direction TO the low dusk sun
SUN_COLOR = (1.0, 0.5, 0.22)
SUN_INT = 1.15
AMBIENT = (0.10, 0.12, 0.20)
# (position, color, intensity)
POINT_LIGHTS = [
    ((12.5, 16.0, -10.0), (1.0, 0.45, 0.12), 20.0),   # bridge explosion
    ((-13.0, 5.0, 0.0), (1.0, 0.42, 0.10), 18.0),    # tanker fire
    ((5.2, 2.0, 15.0), (1.0, 0.65, 0.25), 4.0),      # boat lantern
]
FOG_COLOR = (0.30, 0.18, 0.13)
SKY_ZEN = (0.04, 0.06, 0.15)
SKY_HOR = (0.75, 0.32, 0.10)


def sky_color(d):
    t = clamp((d[1] + 0.05) / 0.6, 0.0, 1.0)
    col = lerp(SKY_HOR, SKY_ZEN, pow(t, 0.55))
    s = max(vdot(d, SUN_DIR), 0.0)
    g = pow(s, 900.0) * 3.0
    h = pow(s, 12.0) * 0.25
    return (col[0] + 1.0 * g + SUN_COLOR[0] * h,
            col[1] + 0.45 * g + SUN_COLOR[1] * h,
            col[2] + 0.15 * g + SUN_COLOR[2] * h)


# ------------------------------------------------------------ intersection --
def intersect(o, d, shadow_mode=False):
    """Nearest hit (t, prim, normal). Returns None on miss."""
    best_t = 1e30
    best = None
    for prim in PRIMS:
        tag = prim[0]
        if tag == 's':
            _, cx, cy, cz, r, m = prim
            if shadow_mode and not m[8]:
                continue
            ox, oy, oz = o[0] - cx, o[1] - cy, o[2] - cz
            b = ox * d[0] + oy * d[1] + oz * d[2]
            c = ox * ox + oy * oy + oz * oz - r * r
            disc = b * b - c
            if disc <= 0:
                continue
            sq = math.sqrt(disc)
            t = -b - sq
            if t < 1e-4:
                t = -b + sq
            if t < 1e-4 or t >= best_t:
                continue
            px, py, pz = o[0] + d[0] * t, o[1] + d[1] * t, o[2] + d[2] * t
            n = ((px - cx) / r, (py - cy) / r, (pz - cz) / r)
            best_t, best = t, (prim, n)
        elif tag == 'p':
            _, nx, ny, nz, pd, m = prim
            den = nx * d[0] + ny * d[1] + nz * d[2]
            if abs(den) < 1e-9:
                continue
            t = (pd - (nx * o[0] + ny * o[1] + nz * o[2])) / den
            if t < 1e-4 or t >= best_t:
                continue
            # Rippled water normal
            if m is SEA:
                px = o[0] + d[0] * t
                pz = o[2] + d[2] * t
                n = vnorm((0.025 * math.sin(0.5 * px + 1.7 * pz)
                           + 0.015 * math.sin(1.3 * px - 0.8 * pz + 2.0),
                           1.0,
                           0.025 * math.sin(0.4 * pz - 1.1 * px)
                           + 0.015 * math.sin(1.1 * pz + 0.7 * px)))
            else:
                n = (nx, ny, nz)
            best_t, best = t, (prim, n)
        elif tag == 'b':
            _, cx, cy, cz, hx, hy, hz, R, m = prim
            # Ray into box local space: o' = R^T (o - c), d' = R^T d
            ox, oy, oz = o[0] - cx, o[1] - cy, o[2] - cz
            lo = (R[0] * ox + R[3] * oy + R[6] * oz,
                  R[1] * ox + R[4] * oy + R[7] * oz,
                  R[2] * ox + R[5] * oy + R[8] * oz)
            ld = (R[0] * d[0] + R[3] * d[1] + R[6] * d[2],
                  R[1] * d[0] + R[4] * d[1] + R[7] * d[2],
                  R[2] * d[0] + R[5] * d[1] + R[8] * d[2])
            tmin, tmax = -1e30, 1e30
            axis = -1
            ok = True
            for i, (oi, di, hi) in enumerate(((lo[0], ld[0], hx),
                                              (lo[1], ld[1], hy),
                                              (lo[2], ld[2], hz))):
                if abs(di) < 1e-9:
                    if abs(oi) > hi:
                        ok = False
                        break
                else:
                    ta = (-hi - oi) / di
                    tb = (hi - oi) / di
                    if ta > tb:
                        ta, tb = tb, ta
                    if ta > tmin:
                        tmin, axis = ta, i
                    if tb < tmax:
                        tmax = tb
                    if tmin > tmax:
                        ok = False
                        break
            if not ok or tmax < 1e-4:
                continue
            t = tmin if tmin > 1e-4 else tmax
            if t < 1e-4 or t >= best_t:
                continue
            # Local normal on the hit face
            ln = [0.0, 0.0, 0.0]
            hit_local = (lo[0] + ld[0] * t, lo[1] + ld[1] * t,
                         lo[2] + ld[2] * t)
            h = (hx, hy, hz)
            ln[axis] = 1.0 if hit_local[axis] > 0 else -1.0
            # World normal: n = R * ln
            n = (R[0] * ln[0] + R[1] * ln[1] + R[2] * ln[2],
                 R[3] * ln[0] + R[4] * ln[1] + R[5] * ln[2],
                 R[6] * ln[0] + R[7] * ln[1] + R[8] * ln[2])
            if vdot(n, d) > 0:
                n = (-n[0], -n[1], -n[2])
            best_t, best = t, (prim, n)
        else:  # cylinder, Y axis
            _, cx, cz, r, y0, y1, m = prim
            ox, oz = o[0] - cx, o[2] - cz
            a = d[0] * d[0] + d[2] * d[2]
            t = None
            n = None
            if a > 1e-12:
                b = 2.0 * (ox * d[0] + oz * d[2])
                c = ox * ox + oz * oz - r * r
                disc = b * b - 4.0 * a * c
                if disc > 0:
                    sq = math.sqrt(disc)
                    for tc in ((-b - sq) / (2 * a), (-b + sq) / (2 * a)):
                        if tc < 1e-4:
                            continue
                        y = o[1] + d[1] * tc
                        if y0 <= y <= y1:
                            t = tc
                            px = o[0] + d[0] * tc
                            pz = o[2] + d[2] * tc
                            n = ((px - cx) / r, 0.0, (pz - cz) / r)
                            break
            # Caps
            if abs(d[1]) > 1e-9:
                for yc, ny in ((y0, -1.0), (y1, 1.0)):
                    tc = (yc - o[1]) / d[1]
                    if tc < 1e-4 or (t is not None and tc >= t):
                        continue
                    px = o[0] + d[0] * tc
                    pz = o[2] + d[2] * tc
                    if (px - cx) ** 2 + (pz - cz) ** 2 <= r * r:
                        t, n = tc, (0.0, ny, 0.0)
            if t is None or t >= best_t:
                continue
            best_t, best = t, (prim, n)
    if best is None:
        return None
    return (best_t, best[0], best[1])


def in_shadow(p, light_dir, max_dist):
    """Shadow ray from p toward the sun; True if something blocks it."""
    o = (p[0] + light_dir[0] * 1e-3, p[1] + light_dir[1] * 1e-3,
         p[2] + light_dir[2] * 1e-3)
    hit = intersect(o, light_dir, shadow_mode=True)
    return hit is not None and hit[0] < max_dist


# ----------------------------------------------------------------- shading --
def shade(p, n, m, view_dir, depth):
    color, amb, diff, spec, shin, refl, emis, alpha, _ = m
    r = AMBIENT[0] * color[0] * amb + emis[0]
    g = AMBIENT[1] * color[1] * amb + emis[1]
    b = AMBIENT[2] * color[2] * amb + emis[2]
    # Dusk sun (directional, casts shadows)
    ndotl = vdot(n, SUN_DIR)
    if ndotl > 0 and not in_shadow(p, SUN_DIR, 1e30):
        r += color[0] * SUN_COLOR[0] * SUN_INT * ndotl * diff
        g += color[1] * SUN_COLOR[1] * SUN_INT * ndotl * diff
        b += color[2] * SUN_COLOR[2] * SUN_INT * ndotl * diff
        h = vnorm(vadd(SUN_DIR, view_dir))
        ndoth = max(vdot(n, h), 0.0)
        s = spec * pow(ndoth, shin) * SUN_INT
        r += SUN_COLOR[0] * s
        g += SUN_COLOR[1] * s
        b += SUN_COLOR[2] * s
    # Fire / lantern point lights (no shadows: glow wraps the scene)
    for (lp, lc, inten) in POINT_LIGHTS:
        lv = vsub(lp, p)
        dist = vlen(lv)
        if dist < 1e-6:
            continue
        lv = (lv[0] / dist, lv[1] / dist, lv[2] / dist)
        ndotl = vdot(n, lv)
        if ndotl <= 0:
            continue
        atten = inten / (1.0 + 0.08 * dist * dist)
        r += color[0] * lc[0] * atten * ndotl * diff
        g += color[1] * lc[1] * atten * ndotl * diff
        b += color[2] * lc[2] * atten * ndotl * diff
        h = vnorm(vadd(lv, view_dir))
        ndoth = max(vdot(n, h), 0.0)
        s = spec * pow(ndoth, shin) * atten
        r += lc[0] * s
        g += lc[1] * s
        b += lc[2] * s
    return (r, g, b)


def trace(o, d, depth):
    hit = intersect(o, d)
    if hit is None:
        return sky_color(d)
    t, prim, n = hit
    m = prim[-1]
    color, amb, diff, spec, shin, refl, emis, alpha, _ = m
    p = (o[0] + d[0] * t, o[1] + d[1] * t, o[2] + d[2] * t)
    view_dir = (-d[0], -d[1], -d[2])
    if alpha < 1.0:
        # Smoke: shade it, then blend with what lies behind.
        behind_o = (p[0] + d[0] * 1e-2, p[1] + d[1] * 1e-2,
                    p[2] + d[2] * 1e-2)
        behind = trace(behind_o, d, depth)
        lit = shade(p, n, m, view_dir, depth)
        col = (alpha * lit[0] + (1 - alpha) * behind[0],
               alpha * lit[1] + (1 - alpha) * behind[1],
               alpha * lit[2] + (1 - alpha) * behind[2])
    else:
        col = shade(p, n, m, view_dir, depth)
        if refl > 0.0 and depth < 2:
            rd = vreflect(d, n)
            ro = (p[0] + n[0] * 1e-3, p[1] + n[1] * 1e-3,
                  p[2] + n[2] * 1e-3)
            rcol = trace(ro, rd, depth + 1)
            col = ((1 - refl) * col[0] + refl * rcol[0],
                   (1 - refl) * col[1] + refl * rcol[1],
                   (1 - refl) * col[2] + refl * rcol[2])
    # Warm haze with distance
    f = 1.0 - math.exp(-t * 0.004)
    return (col[0] + (FOG_COLOR[0] - col[0]) * f,
            col[1] + (FOG_COLOR[1] - col[1]) * f,
            col[2] + (FOG_COLOR[2] - col[2]) * f)


# ------------------------------------------------------------------ render --
CAM_POS = (2.0, 4.5, 30.0)
CAM_LOOK = (-2.0, 6.0, -10.0)
FOV = 55.0


def render_rows(args):
    y0, y1, w, h = args
    fwd = vnorm(vsub(CAM_LOOK, CAM_POS))
    right = vnorm(vcross(fwd, (0.0, 1.0, 0.0)))
    up = vcross(right, fwd)
    tan = math.tan(math.radians(FOV) / 2.0)
    out = bytearray()
    for y in range(y0, y1):
        py = (1.0 - 2.0 * (y + 0.5) / h) * tan
        for x in range(w):
            px = (2.0 * (x + 0.5) / w - 1.0) * tan
            d = vnorm(vadd(vadd(fwd, vscale(right, px)), vscale(up, py)))
            c = trace(CAM_POS, d, 0)
            # Reinhard tone map + gamma
            for v in c:
                v = v / (1.0 + v) if v > 0 else 0.0
                out.append(int(clamp(math.sqrt(v), 0.0, 1.0) * 255.0 + 0.5))
    return (y0, bytes(out))


def write_png(path, w, h, rgb):
    raw = b''.join(b'\x00' + rgb[y * w * 3:(y + 1) * w * 3]
                   for y in range(h))

    def chunk(tag, data):
        c = tag + data
        return (struct.pack('>I', len(data)) + c +
                struct.pack('>I', zlib.crc32(c) & 0xffffffff))
    png = b'\x89PNG\r\n\x1a\n'
    png += chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))
    png += chunk(b'IDAT', zlib.compress(raw, 6))
    png += chunk(b'IEND', b'')
    with open(path, 'wb') as f:
        f.write(png)
    return len(png)


def main():
    size = 1024
    out = 'entry.png'
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == '--size' and i + 1 < len(sys.argv):
            size = int(sys.argv[i + 1])
            i += 2
        elif sys.argv[i] == '--out' and i + 1 < len(sys.argv):
            out = sys.argv[i + 1]
            i += 2
        else:
            i += 1
    build_scene()
    print('primitives:', len(PRIMS), 'size:', size, flush=True)
    workers = min(4, os.cpu_count() or 1)
    rows = [(y, min(y + size // workers, size), size, size)
            for y in range(0, size, size // workers)]
    with Pool(workers) as pool:
        parts = pool.map(render_rows, rows)
    rgb = b''.join(p[1] for p in sorted(parts))
    n = write_png(out, size, size, rgb)
    print('wrote', out, size, 'x', size, n, 'bytes', flush=True)


if __name__ == '__main__':
    main()
