#!/usr/bin/env python3
"""Edge padding: the texels around the UV islands take the colour of the nearest painted texel (ours).

padedge.py baked.png template/head_sub.obj out.png [pixels=24]
The engine reads the texture with mip maps and bilinear filtering: black between the islands bleeds into the edge
texels and draws dark dotted lines along the seams (the zigzag of the neck island on the neck, the ear island)."""
import sys
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
import bake


def main():
    src, tpl, dst = sys.argv[1:4]
    px = int(sys.argv[4]) if len(sys.argv) > 4 else 24
    t = np.array(Image.open(src).convert('RGB'))
    S = t.shape[0]
    vt, F = bake.read_uv_faces(tpl)
    m = Image.new('L', (S, S), 0)
    d = ImageDraw.Draw(m)
    for f in F:
        d.polygon([(vt[p[1]][0] * S, (1 - vt[p[1]][1]) * S) for p in f], fill=255)
    cov = ndi.binary_erosion(np.array(m) > 0, iterations=1)  # the rim of the island is rasterised half black
    dist, (iy, ix) = ndi.distance_transform_edt(~cov, return_indices=True)
    out = t.copy()
    pad = (~cov) & (dist <= px)
    out[pad] = t[iy[pad], ix[pad]]
    print('padded texels', int(pad.sum()))
    Image.fromarray(out).save(dst)


if __name__ == '__main__':
    main()
