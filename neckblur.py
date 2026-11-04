#!/usr/bin/env python3
"""Smooth the blocky skin under the jaw (ours): the face island is magnified there, its texels show as blocks
and the zigzag border to the neck island reads as a patch outline.

neckblur.py in.png template/head_sub.obj template/regions.json out.png
Faces of the template in the band Y0..Y1 (not the neck region) are painted into a mask, only skin (L > LSKIN,
beard stays), feathered; inside it the texture is a gaussian blur (SIGMA texels)."""
import sys
import json
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
from skimage import color
import bake

Y0, Y1 = 6.35, 6.75
LSKIN = 38.0
SIGMA = 2.2
FEATHER = 4


def main():
    src, tpl, reg, dst = sys.argv[1:5]
    t = np.array(Image.open(src).convert('RGB'))
    S = t.shape[0]
    r = json.load(open(reg))
    nk = r['names'].index('neck')
    V = bake.read_v(tpl)
    vt, F = bake.read_uv_faces(tpl)
    m = Image.new('L', (S, S), 0)
    d = ImageDraw.Draw(m)
    for f in F:
        ys = [V[p[0]][1] for p in f]
        if min(ys) >= Y0 and max(ys) <= Y1 and not all(r['vertex'][p[0]] == nk for p in f):
            d.polygon([(vt[p[1]][0] * S, (1 - vt[p[1]][1]) * S) for p in f], fill=255)
    L = color.rgb2lab(t / 255.0)[..., 0]
    mask = (np.array(m) > 0) & (ndi.median_filter(L, 9) > LSKIN)
    w = ndi.gaussian_filter(ndi.binary_erosion(mask, iterations=1).astype(float), FEATHER / 2)[..., None]
    blur = np.stack([ndi.gaussian_filter(t[..., c].astype(float), SIGMA) for c in range(3)], -1)
    out = t * (1 - w) + blur * w
    print('blur texels', int(mask.sum()))
    Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).save(dst)


if __name__ == '__main__':
    main()
