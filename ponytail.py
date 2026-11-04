#!/usr/bin/env python3
"""Ponytail as a separate layer: ponytail.py target.glb wrapped.obj out.glb
The target (generated head) has the ponytail, the wrapped template does not. The ponytail is the part of the target that
lies outside the wrapped head (distance > OUT) behind and below the skull (z < ZMAX, y < YMAX); the connected pieces
of it are kept as their own mesh with the UV and the material of the target. The head stays the clean template."""
import sys
import numpy as np
import trimesh
from bake import read_mesh

OUT, ZMAX, YMAX, MIN_FACES = 0.02, -0.2, 0.03, 200


def extract(T, Wm):
    d = Wm.nearest.on_surface(T.vertices)[1]
    v = T.vertices
    sel = (d > OUT) & (v[:, 2] < ZMAX) & (v[:, 1] < YMAX)
    fm = sel[T.faces].all(1)
    sub = T.submesh([np.where(fm)[0]], append=True)
    parts = [c for c in sub.split(only_watertight=False) if len(c.faces) >= MIN_FACES]
    return trimesh.util.concatenate(parts) if parts else None


if __name__ == '__main__':
    T = trimesh.load(sys.argv[1], force='mesh')
    P = extract(T, read_mesh(sys.argv[2]))
    print('ponytail faces', len(P.faces), 'bounds', P.bounds.round(3).tolist())
    P.export(sys.argv[3])


def spine(P, step=0.05, y_lo=-0.46, y_hi=0.02):
    """rings along y: centre (x, z) and the half sizes of the ellipse from the extracted ponytail (ours: the tube is built, not copied)"""
    v = P.vertices
    rows = []
    for y0 in np.arange(y_lo, y_hi, step):
        s = v[(v[:, 1] >= y0) & (v[:, 1] < y0 + step)]
        if len(s) < 20:
            continue
        lo, hi = np.percentile(s[:, 0], [5, 95]), np.percentile(s[:, 2], [5, 95])
        rows.append([y0 + step / 2, (lo[0] + lo[1]) / 2, (hi[0] + hi[1]) / 2, (lo[1] - lo[0]) / 2, (hi[1] - hi[0]) / 2])
    return np.array(rows)[::-1]  # from the root (top) down


def tube(S, sides=24, sub=4):
    """a smooth tapered tube through the rings (cubic in between); returns vertices, uv, faces"""
    from scipy.interpolate import CubicSpline
    t = np.arange(len(S))
    cs = CubicSpline(t, S, axis=0)
    tt = np.linspace(0, len(S) - 1, (len(S) - 1) * sub + 1)
    R = cs(tt)
    R[:, 3:] = np.clip(R[:, 3:], 0.01, None)
    taper = 1 - 0.55 * (tt / tt[-1]) ** 2  # the tip is thinner
    ang = np.linspace(0, 2 * np.pi, sides, endpoint=False)
    V, UV = [], []
    for k, (y, cx, cz, rx, rz) in enumerate(R):
        for a in np.append(ang, 2 * np.pi):
            V.append([cx + rx * taper[k] * np.cos(a), y, cz + rz * taper[k] * np.sin(a)])
            UV.append([a / (2 * np.pi), 1 - k / (len(R) - 1)])
    n = sides + 1
    Fc = []
    for k in range(len(R) - 1):
        for j in range(sides):
            a, b, c, d = k * n + j, k * n + j + 1, (k + 1) * n + j, (k + 1) * n + j + 1
            Fc += [[a, c, b], [b, c, d]]
    return np.array(V), np.array(UV), np.array(Fc)


def hair_texture(P, size=512, seed=1):
    """strands: vertical streaks of the mean colour of the target ponytail texture (ours, marked as such in docs/plan.md)"""
    t = np.asarray(P.visual.material.baseColorTexture.convert('RGB'), float)
    m = t.reshape(-1, 3).mean(0)
    rng = np.random.default_rng(seed)
    cols = rng.normal(0, 1, (1, size))
    for s in (1, 2, 4):
        cols = cols + np.repeat(rng.normal(0, 1, (1, size // s + 1)), s, 1)[:, :size]
    along = rng.normal(0, 1, (size, 1)) * 0.15
    g = cols / cols.std() + along
    img = np.clip(m[None, None] * (1 + 0.28 * g[..., None]) * np.ones((size, size, 1)), 0, 255)
    return img.astype(np.uint8)


def build(P, out_obj, out_png, scale=0.65):
    from PIL import Image
    S = spine(P)
    S[:, 3:] *= scale
    S[0, 0], S[0, 2] = 0.03, -0.27  # the root sits inside the back of the head
    V, UV, F = tube(S)
    Image.fromarray(hair_texture(P)).save(out_png)
    with open(out_obj, 'w') as f:
        for v in V:
            f.write('v %.5f %.5f %.5f\n' % tuple(v))
        for u in UV:
            f.write('vt %.5f %.5f\n' % tuple(u))
        for a, b, c in F + 1:
            f.write('f %d/%d %d/%d %d/%d\n' % (a, a, b, b, c, c))
    return V, F
