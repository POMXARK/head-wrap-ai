#!/usr/bin/env python3
"""Stage 4 (first version): bake the texture of the target head into the UV of the template.
bake.py target.glb wrapped.obj template/head.obj out.png [--size 2048]
Every texel of the template UV -> point on the wrapped template -> nearest point of the target -> colour of the
target texture there. (Next: the best view per texel and the region classes, see docs/plan.md, stage 4.)"""
import argparse
import os
import sys
import numpy as np
import trimesh
from PIL import Image


FAR = 0.01  # target units (head height ~1)


def read_uv_faces(path):
    """(vt array, faces as [(vi, ti) x3]) of head.obj; quads are split."""
    vt, F = [], []
    for l in open(path):
        t = l.split()
        if not t:
            continue
        if t[0] == 'vt':
            vt.append(list(map(float, t[1:3])))
        elif t[0] == 'f':
            p = [tuple(int(x) - 1 for x in q.split('/')[:2]) for q in t[1:]]
            for k in range(1, len(p) - 1):
                F.append([p[0], p[k], p[k + 1]])
    return np.array(vt), F


def read_v(path):
    """vertices in the order of the v lines (trimesh splits vertices by (v, vt) pairs and reorders them)"""
    return np.array([list(map(float, l.split()[1:4])) for l in open(path) if l.startswith('v ')])


def read_mesh(path):
    """trimesh.Trimesh with the v index order of the file (no UV)"""
    _, F = read_uv_faces(path)
    return trimesh.Trimesh(read_v(path), np.array([[p[0] for p in f] for f in F]), process=False)


def write_v(template, out, V):
    """copy of the template obj with new v lines (UV and faces kept)"""
    it = iter(V)
    with open(out, 'w') as o:
        for l in open(template):
            o.write('v %.5f %.5f %.5f\n' % tuple(next(it)) if l.startswith('v ') else l)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('target')
    ap.add_argument('wrapped')
    ap.add_argument('template')
    ap.add_argument('out')
    ap.add_argument('--size', type=int, default=2048)
    ap.add_argument('--front', help='Qwen front view: texels facing the front take its pixel (sharper, the real eye)')
    a = ap.parse_args()
    tgt = trimesh.load(a.target, force='mesh')
    tex = np.asarray(tgt.visual.material.baseColorTexture.convert('RGB'))
    tuv = tgt.visual.uv
    W = read_v(a.wrapped)
    vt, F = read_uv_faces(a.template)
    S = a.size
    img = np.zeros((S, S, 3), np.uint8)
    cov = np.zeros((S, S), bool)
    pts, px, nrm = [], [], []
    for f in F:
        uv = vt[[p[1] for p in f]] * S
        x0, y0 = np.floor(uv.min(0)).astype(int)
        x1, y1 = np.ceil(uv.max(0)).astype(int)
        xs, ys = np.meshgrid(np.arange(max(x0, 0), min(x1 + 1, S)), np.arange(max(y0, 0), min(y1 + 1, S)))
        c = np.stack([xs.ravel() + .5, ys.ravel() + .5], 1)
        # barycentric in the UV plane (v flipped: image row = (1 - v) * S, so use v directly and flip at the end)
        A = np.array([uv[1] - uv[0], uv[2] - uv[0]]).T
        det = np.linalg.det(A)
        if abs(det) < 1e-12:
            continue
        b = np.linalg.solve(A, (c - uv[0]).T).T
        m = (b[:, 0] >= -1e-6) & (b[:, 1] >= -1e-6) & (b.sum(1) <= 1 + 1e-6)
        if not m.any():
            continue
        bb = np.column_stack([1 - b[m].sum(1), b[m]])
        P = bb @ W[[p[0] for p in f]]
        pts.append(P)
        n = np.cross(W[f[1][0]] - W[f[0][0]], W[f[2][0]] - W[f[0][0]])
        nrm.append(np.tile(n / (np.linalg.norm(n) + 1e-12), (len(P), 1)))
        px.append(c[m].astype(int) - 0)
        px[-1] = np.floor(c[m]).astype(int)
    P = np.vstack(pts)
    px = np.vstack(px)
    N = np.vstack(nrm)
    cp, dist, tid = trimesh.proximity.closest_point(tgt, P)
    # texels far from the target (eyelids: the target has a pit there) look along the normal of the template into the
    # target instead of taking the nearest point, which is skin beside the pit
    far = np.where(dist > FAR)[0]
    if len(far):
        loc, ray, tri_hit = tgt.ray.intersects_location(P[far] + N[far] * 0.05, -N[far], multiple_hits=False)
        cp[far[ray]], tid[far[ray]] = loc, tri_hit
        print('texels far from the target', len(far), 'ray hits', len(ray))
    tri = tgt.vertices[tgt.faces[tid]]
    # barycentric of cp in the target triangle
    v0, v1, v2 = tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0], cp - tri[:, 0]
    d00, d01, d11 = (v0 * v0).sum(1), (v0 * v1).sum(1), (v1 * v1).sum(1)
    d20, d21 = (v2 * v0).sum(1), (v2 * v1).sum(1)
    den = d00 * d11 - d01 * d01
    bv = (d11 * d20 - d01 * d21) / den
    bw = (d00 * d21 - d01 * d20) / den
    bu = 1 - bv - bw
    uvs = tuv[tgt.faces[tid]]
    q = bu[:, None] * uvs[:, 0] + bv[:, None] * uvs[:, 1] + bw[:, None] * uvs[:, 2]
    H, Wt = tex.shape[:2]
    tx = np.clip((q[:, 0] % 1 * Wt).astype(int), 0, Wt - 1)
    ty = np.clip(((1 - q[:, 1]) % 1 * H).astype(int), 0, H - 1)
    col = tex[ty, tx]
    row = np.clip(S - 1 - px[:, 1], 0, S - 1)  # template v up -> image row down
    img[row, np.clip(px[:, 0], 0, S - 1)] = col
    cov[row, np.clip(px[:, 0], 0, S - 1)] = True
    if a.front:
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'corsairs-remake', 'tools'))
        import pdm_project_views as pv
        f, (x0, x1, y0, y1), inner = pv.load_view(a.front)
        lo, hi = tgt.vertices.min(0), tgt.vertices.max(0)
        wgt = np.clip((N[:, 2] - 0.5) / 0.35, 0, 1)  # facing the front camera
        qx = np.clip((x0 + (P[:, 0] - lo[0]) / (hi[0] - lo[0]) * (x1 - x0)).astype(int), 0, f.shape[1] - 1)
        qy = np.clip((y1 - (P[:, 1] - lo[1]) / (hi[1] - lo[1]) * (y1 - y0)).astype(int), 0, f.shape[0] - 1)
        ok = inner[qy, qx]  # only inside the figure (not the blended rim)
        wgt = wgt * ok
        q = f[qy, qx]
        col = (col * (1 - wgt[:, None]) + q * wgt[:, None]).astype(np.uint8)
        img[row, np.clip(px[:, 0], 0, S - 1)] = col
        print('texels from the front view', int((wgt > 0.5).sum()))
    Image.fromarray(img).save(a.out)
    print('texels', int(cov.sum()), 'of', S * S, '->', a.out)


if __name__ == '__main__':
    main()
