#!/usr/bin/env python3
"""Ponytail as a separate layer: ponytail.py target.glb wrapped.obj out.glb
The target (generated head) has the ponytail, the wrapped template does not. The ponytail is the part of the target that
lies outside the wrapped head (distance > OUT) behind and below the skull (z < ZMAX, y < YMAX); the connected pieces
of it are kept as their own mesh with the UV and the material of the target. The head stays the clean template."""
import os
import sys
import numpy as np
import trimesh
from bake import read_mesh

HERE = os.path.dirname(os.path.abspath(__file__))
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


BAND_RING, BAND_W, CURL = 2, 0.03, 0.10  # the band: ring of S (y -0.035), half width in v; the tip curls back by CURL (z)


def tube(S, sides=24, sub=4):
    """a smooth tapered tube through the rings (cubic in between); returns vertices, uv, faces"""
    from scipy.interpolate import CubicSpline
    t = np.arange(len(S))
    cs = CubicSpline(t, S, axis=0)
    tt = np.linspace(0, len(S) - 1, (len(S) - 1) * sub + 1)
    R = cs(tt)
    R[:, 3:] = np.clip(R[:, 3:], 0.01, None)
    taper = 1 - 0.55 * (tt / tt[-1]) ** 2  # the tip is thinner
    taper *= 1 - 0.25 * np.exp(-((tt - BAND_RING) / 0.35) ** 2)  # the hair is pinched by the band
    f = np.clip((tt / tt[-1] - 0.7) / 0.3, 0, 1)
    R[:, 2] -= CURL * f * f * (3 - 2 * f)  # the tip curls back as in the Qwen left view
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
    # the band: a darker stripe at the pinch (v from the top: ring BAND_RING of 10 rings)
    v = 1 - BAND_RING / 10.0
    r0, r1 = int((1 - v - BAND_W / 2) * size), int((1 - v + BAND_W / 2) * size)
    img[r0:r1] = (img[r0:r1] * 0.45).astype(img.dtype)
    return img.astype(np.uint8)


def build(P, out_obj, out_png, scale=0.85, target=None, views=None):
    from PIL import Image
    S = spine(P)
    S[:, 3:] *= scale
    S[0, 0], S[0, 2] = 0.03, -0.27  # the root sits inside the back of the head
    S[1, 2] = max(S[1, 2], -0.31)  # the first ring leaves the skull gradually (back of the head at y 0: z -0.28)
    S = np.vstack([[0.08, 0.0, -0.255, 0.05, 0.05], S])  # a ring inside the hair mass above: no gap at the nape
    V, UV, F = tube(S)
    if views:  # strands from the views (the original), the procedural texture only as a fallback
        S0 = spine(P)
        img = texture_from_views(S0, target, views, scale=scale)
    else:
        img = hair_texture(P)
    Image.fromarray(img).save(out_png)
    with open(out_obj, 'w') as f:
        for v in V:
            f.write('v %.5f %.5f %.5f\n' % tuple(v))
        for u in UV:
            f.write('vt %.5f %.5f\n' % tuple(u))
        for a, b, c in F + 1:
            f.write('f %d/%d %d/%d %d/%d\n' % (a, a, b, b, c, c))
    return V, F


def texture_from_views(S, target, view_paths, size=512, scale=0.85):
    """strand texture of the tube from the four Qwen views: a fine grid of the tube (rings x sides) is projected into the
    views (as in bake.from_views), the colour is blended by facing^3 inside the figure, then resized to size x size
    (row = ring from the root, column = angle, as the UV of tube())."""
    sys.path.insert(0, os.path.join(HERE, '..', 'corsairs-remake', 'tools'))
    import pdm_project_views as pv
    from PIL import Image
    from bake import CAM, _tv
    S = S.copy()
    S[:, 3:] *= scale
    S[0, 0], S[0, 2] = 0.03, -0.27
    S[1, 2] = max(S[1, 2], -0.31)
    S = np.vstack([[0.08, 0.0, -0.255, 0.05, 0.05], S])
    sides, sub = 96, 16
    V, UV, _ = tube(S, sides=sides, sub=sub)
    n_ring = len(V) // (sides + 1)
    G = V.reshape(n_ring, sides + 1, 3)
    cen = G[:, :-1].mean(1, keepdims=True)
    nrm = G - cen
    nrm[..., 1] = 0
    nrm /= np.linalg.norm(nrm, axis=2, keepdims=True) + 1e-9
    P, N = G.reshape(-1, 3), nrm.reshape(-1, 3)
    lo, hi = target.vertices.min(0), target.vertices.max(0)
    acc, wsum = np.zeros((len(P), 3)), np.full(len(P), 1e-6)
    for name, path in zip(pv.NAMES, view_paths):
        if name == 'front':  # the face looks through the head onto the inner side of the tail: only back and sides
            continue
        f, (x0, x1, y0, y1), inner = pv.load_view(path)
        tp, yp = _tv(pv, name, P, lo, hi)
        qx = np.clip((x0 + tp * (x1 - x0)).astype(int), 0, f.shape[1] - 1)
        qy = np.clip((y1 - yp * (y1 - y0)).astype(int), 0, f.shape[0] - 1)
        w = np.clip((N @ np.array(CAM[name], float) - 0.2) / 0.6, 0, 1) ** 2 * inner[qy, qx]
        acc += f[qy, qx] * w[:, None]
        wsum += w
    base = np.array([35., 27., 24.])  # dark hair where no view sees the tube
    col = (acc + base * 0.05) / (wsum[:, None] + 0.05)
    img = Image.fromarray(col.reshape(n_ring, sides + 1, 3).clip(0, 255).astype(np.uint8)).resize((size, size), Image.BICUBIC)
    return np.asarray(img)

