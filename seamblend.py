#!/usr/bin/env python3
"""Evens the colour across UV seams of the baked atlas (ours): both sides of a seam edge sample the same 3D line,
so after blending they show the same colour and the seam stops being a line on the head.

seamblend.py baked.png wrapped.obj template/head_sub.obj out.png [mouth_y_lo mouth_y_hi]
Along every seam edge (a mesh edge whose two faces have different UV for it) both UV copies are blended to the mean
colour, spread over 2 texels; edges at the mouth opening (their y between the two limits) are left alone."""
import sys
import numpy as np
from collections import defaultdict
from PIL import Image
from scipy import ndimage as ndi
import bake


def main():
    src, wob, tpl, dst = sys.argv[1:5]
    lo, hi = (float(sys.argv[5]), float(sys.argv[6])) if len(sys.argv) > 6 else (-0.222, -0.200)
    t = np.array(Image.open(src).convert('RGB')).astype(float)
    S = t.shape[0]
    W = bake.read_v(wob)
    vt, F = bake.read_uv_faces(tpl)
    ed = defaultdict(list)
    for f in F:
        for i in range(3):
            a, b = f[i], f[(i + 1) % 3]
            ed[tuple(sorted((a[0], b[0])))].append((a, b))
    acc = np.zeros_like(t)
    cnt = np.zeros((S, S))
    n = 0
    for k, l in ed.items():
        if len(l) != 2:
            continue
        sides = []
        for a, b in l:
            pa = {a[0]: vt[a[1]], b[0]: vt[b[1]]}
            sides.append((pa[k[0]], pa[k[1]]))
        (p0, p1), (q0, q1) = sides
        if np.allclose(p0, q0, atol=1e-6) and np.allclose(p1, q1, atol=1e-6):
            continue
        y = (W[k[0]][1] + W[k[1]][1]) / 2
        if lo < y < hi and W[k[0]][2] > 0.15:
            continue
        L = max(2, int(max(np.hypot(*(np.subtract(p1, p0) * S)), 2)))
        s = np.linspace(0, 1, L)[:, None]
        P = np.array(p0) + s * (np.array(p1) - np.array(p0))
        Q = np.array(q0) + s * (np.array(q1) - np.array(q0))
        px = np.clip((P * S).astype(int), 0, S - 1); qx = np.clip((Q * S).astype(int), 0, S - 1)
        pr, qr = (S - 1 - px[:, 1], px[:, 0]), (S - 1 - qx[:, 1], qx[:, 0])
        m = (t[pr] + t[qr]) / 2
        for r in (pr, qr):
            np.add.at(acc, r, m); np.add.at(cnt, r, 1)
        n += 1
    mask = cnt > 0
    tgt = np.zeros_like(t)
    tgt[mask] = acc[mask] / cnt[mask][:, None]
    w = ndi.gaussian_filter(mask.astype(float), 1.0)
    w = np.clip(w * 2, 0, 1) * 0.8
    # spread the target colour to the neighbours of the seam texels
    num = np.stack([ndi.gaussian_filter(tgt[..., c], 1.0) for c in range(3)], -1)
    den = ndi.gaussian_filter(mask.astype(float), 1.0)[..., None] + 1e-9
    out = t * (1 - w[..., None]) + (num / den) * w[..., None]
    out[w < 1e-3] = t[w < 1e-3]
    print('seam edges', n, 'texels touched', int((w > 1e-3).sum()))
    Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).save(dst)


if __name__ == '__main__':
    main()
