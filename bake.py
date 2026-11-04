#!/usr/bin/env python3
"""Stage 4 (first version): bake the texture of the target head into the UV of the template.
bake.py target.glb wrapped.obj template/head.obj out.png [--size 2048]
Every texel of the template UV -> point on the wrapped template -> nearest point of the target -> colour of the
target texture there. (Next: the best view per texel and the region classes, see docs/plan.md, stage 4.)"""
import argparse
import numpy as np
import trimesh
from PIL import Image


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
    a = ap.parse_args()
    tgt = trimesh.load(a.target, force='mesh')
    tex = np.asarray(tgt.visual.material.baseColorTexture.convert('RGB'))
    tuv = tgt.visual.uv
    W = read_v(a.wrapped)
    vt, F = read_uv_faces(a.template)
    S = a.size
    img = np.zeros((S, S, 3), np.uint8)
    cov = np.zeros((S, S), bool)
    pts, px = [], []
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
        px.append(c[m].astype(int) - 0)
        px[-1] = np.floor(c[m]).astype(int)
    P = np.vstack(pts)
    px = np.vstack(px)
    cp, _, tid = trimesh.proximity.closest_point(tgt, P)
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
    Image.fromarray(img).save(a.out)
    print('texels', int(cov.sum()), 'of', S * S, '->', a.out)


if __name__ == '__main__':
    main()
