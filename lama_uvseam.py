#!/usr/bin/env python3
"""LaMa inpaint along the UV seams of a 3D box (ours): lama_uvseam.py padded.png template/head_sub.obj wrapped.obj out.png x0 x1 y0 y1 z0 z1 [width]
wrapped.obj = the fitted head (same vertex order as the template) gives the 3D positions. A seam edge = an edge whose two corners have the same 3D position on both faces but different UV (it is a boundary edge
of an unwelded mesh). The edges whose middle lies in the box are drawn into a mask `width` texels wide (both sides of the
seam, each island in its own UV place) and filled by LaMa from the padded context (padedge.py first!)."""
import os
import sys
import collections
import numpy as np
from PIL import Image, ImageDraw
import bake

W = os.environ.get('W', '/media/roman/383be9ee-c114-4bf8-8956-66b985661cb4/home/remake-linux')
os.environ.setdefault('LAMA_MODEL', W + '/lama/big-lama.pt')
sys.path.insert(0, W + '/lama/pkg')
from simple_lama_inpainting import SimpleLama  # noqa: E402


def main():
    src, tpl, pos, dst = sys.argv[1:5]
    x0, x1, y0, y1, z0, z1 = (float(v) for v in sys.argv[5:11])
    width = int(sys.argv[11]) if len(sys.argv) > 11 else 7
    t = np.array(Image.open(src).convert('RGB'))
    S = t.shape[0]
    vt, F = bake.read_uv_faces(tpl)
    P = np.array([[float(v) for v in l.split()[1:4]] for l in open(pos) if l.startswith('v ')])
    cnt = collections.defaultdict(list)
    for f in F:
        for a, b in ((0, 1), (1, 2), (2, 0)):
            pa, pb = f[a], f[b]
            key = tuple(sorted((tuple(np.round(P[pa[0]], 5)), tuple(np.round(P[pb[0]], 5)))))
            cnt[key].append((vt[pa[1]], vt[pb[1]]) if (tuple(P[pa[0]]) <= tuple(P[pb[0]])) else (vt[pb[1]], vt[pa[1]]))
    mk = Image.new('L', (S, S), 0)
    d = ImageDraw.Draw(mk)
    n = 0
    for key, uvs in cnt.items():
        mid = (np.array(key[0]) + np.array(key[1])) / 2
        if not (x0 <= mid[0] <= x1 and y0 <= mid[1] <= y1 and z0 <= mid[2] <= z1):
            continue
        if len({tuple(np.round(np.array(u), 4).ravel()) for u in uvs}) < 2:
            continue  # same UV on both faces: not a seam
        n += 1
        for a, b in uvs:
            d.line([(a[0] * S, (1 - a[1]) * S), (b[0] * S, (1 - b[1]) * S)], fill=255, width=width)
    m = np.array(mk) > 0
    print('seam edges', n, 'mask texels', int(m.sum()))
    ys, xs = np.where(m)
    a, b, c, e = max(ys.min() - 60, 0), min(ys.max() + 60, S), max(xs.min() - 60, 0), min(xs.max() + 60, S)
    sm = m[a:b, c:e]
    res = np.array(SimpleLama()(Image.fromarray(t[a:b, c:e]), Image.fromarray((sm * 255).astype(np.uint8))))[:b - a, :e - c]
    t[a:b, c:e][sm] = res[sm]
    Image.fromarray(t).save(dst)


if __name__ == '__main__':
    main()
