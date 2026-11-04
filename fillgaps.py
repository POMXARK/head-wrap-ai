#!/usr/bin/env python3
"""Fills the unpainted texels (pure black) that lie inside the UV coverage: rasterization cracks between triangles (ours).

fillgaps.py baked.png template/head_sub.obj out.png
Each gap texel takes the mean of its painted 8 neighbours, repeated until none is left (at most 8 rounds)."""
import sys
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
import bake


def main():
    src, tpl, dst = sys.argv[1:4]
    t = np.array(Image.open(src).convert('RGB')).astype(float)
    S = t.shape[0]
    vt, F = bake.read_uv_faces(tpl)
    m = Image.new('L', (S, S), 0)
    d = ImageDraw.Draw(m)
    for f in F:
        d.polygon([(vt[p[1]][0] * S, (1 - vt[p[1]][1]) * S) for p in f], fill=255)
    cov = np.array(m) > 0
    gap = cov & (t.sum(2) <= 3)
    print('gap texels', int(gap.sum()))
    k = np.ones((3, 3))
    for _ in range(8):
        if not gap.any():
            break
        ok = (~gap).astype(float)
        num = np.stack([ndi.convolve(t[..., c] * ok, k, mode='constant') for c in range(3)], -1)
        den = ndi.convolve(ok, k, mode='constant')
        fill = gap & (den > 0)
        t[fill] = num[fill] / den[fill][:, None]
        gap &= ~fill
    print('left', int(gap.sum()))
    Image.fromarray(np.clip(t, 0, 255).astype(np.uint8)).save(dst)


if __name__ == '__main__':
    main()
