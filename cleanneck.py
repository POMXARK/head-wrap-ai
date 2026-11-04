#!/usr/bin/env python3
"""Clean skin on the neck: dark blotches of the neck islands (hair of the back view, the beard shadow, the ear) are painted
over with the skin colour around them (ours).

cleanneck.py baked.png template/head_sub.obj template/regions.json out.png
Texels of triangles whose vertices are mostly 'neck' and that are darker than the skin of the island (L below the
median - 12) are replaced by the normalised blur of the good texels (a wide gaussian, so the colour flows in from
all sides); the border of the replaced area is feathered."""
import sys
import json
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
from skimage import color
import bake

DARK = 12.0
B = 24  # grain block, texels
GRAIN = 1.0


def main():
    src, tpl, reg, dst = sys.argv[1:5]
    t = np.array(Image.open(src).convert('RGB'))
    S = t.shape[0]
    r = json.load(open(reg))
    nk = r['names'].index('neck')
    vt, F = bake.read_uv_faces(tpl)
    m, mn = Image.new('L', (S, S), 0), Image.new('L', (S, S), 0)
    d, dn = ImageDraw.Draw(m), ImageDraw.Draw(mn)
    for f in F:
        poly = [(vt[p[1]][0] * S, (1 - vt[p[1]][1]) * S) for p in f]
        d.polygon(poly, fill=255)
        if sum(r['vertex'][p[0]] == nk for p in f) >= 2:
            dn.polygon(poly, fill=255)
    lab_, n = ndi.label(np.array(m) > 0)  # the whole UV island that holds the neck triangles (its corners are ear/hair)
    keep = np.unique(lab_[np.array(mn) > 0])
    isl = ndi.binary_erosion(np.isin(lab_, keep[keep > 0]), iterations=2)
    L = color.rgb2lab(t / 255.0)
    med = np.median(L[isl][:, 0])
    bad = isl & (L[..., 0] < med - DARK)
    bad = ndi.binary_dilation(bad, iterations=4) & isl
    print('neck texels', int(isl.sum()), 'median L', round(float(med), 1), 'repainted', int(bad.sum()))
    good = (isl & ~bad).astype(float)
    out = t.astype(float)
    for sig in (6, 20, 60):  # near colour first, then wider where nothing good is near
        num = np.stack([ndi.gaussian_filter(out[..., c] * good, sig) for c in range(3)], -1)
        den = ndi.gaussian_filter(good, sig)
        fill = bad & (den > 0.02)
        out[fill] = num[fill] / den[fill][:, None]
        good = np.maximum(good, fill.astype(float))
        bad &= ~fill
    # the fill is smooth: the grain of the skin is copied back from good texels (blocks of the high-pass at random places)
    rng = np.random.default_rng(7)
    goodm = isl & ~ndi.binary_dilation(np.array(Image.fromarray(((np.abs(out - t).sum(2) > 0) * 255).astype(np.uint8))) > 0, iterations=6)
    hp = t.astype(float) - np.stack([ndi.gaussian_filter(t[..., c].astype(float), 2.5) for c in range(3)], -1)
    gy, gx = np.where(ndi.binary_erosion(goodm, iterations=B))
    filled = np.abs(out - t).sum(2) > 0
    grain = np.zeros_like(out)
    for y0 in range(0, S, B):
        for x0 in range(0, S, B):
            blk = filled[y0:y0 + B, x0:x0 + B]
            if not blk.any() or len(gy) == 0:
                continue
            k = rng.integers(len(gy))
            sy, sx = gy[k] - B // 2, gx[k] - B // 2
            sy, sx = min(max(sy, 0), S - B), min(max(sx, 0), S - B)
            grain[y0:y0 + B, x0:x0 + B] = hp[sy:sy + B, sx:sx + B]
    out = out + grain * filled[..., None] * GRAIN
    w = ndi.gaussian_filter(((isl) & (np.abs(out - t).sum(2) > 0)).astype(float), 2)[..., None]
    res = (t * (1 - w) + out * w).clip(0, 255).astype(np.uint8)
    Image.fromarray(res).save(dst)


if __name__ == '__main__':
    main()
