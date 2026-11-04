#!/usr/bin/env python3
"""Neural inpaint (LaMa, open source) of the light seam lines on the neck UV island (ours).

lama_seam.py padded.png (padedge.py output) template/head_sub.obj template/regions.json out.png
The island is found as in cleanneck.py; the seam = texels lighter than the local median (size 21) by > 5 L, grown by 2;
LaMa (big-lama.pt in $W/lama, LAMA_MODEL) fills them from the grain around."""
import os
import sys
import json
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
from skimage import color
import bake

W = os.environ.get('W', '/media/roman/383be9ee-c114-4bf8-8956-66b985661cb4/home/remake-linux')
os.environ.setdefault('LAMA_MODEL', W + '/lama/big-lama.pt')
sys.path.insert(0, W + '/lama/pkg')
from simple_lama_inpainting import SimpleLama  # noqa: E402


BAND = 5


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
    lab_, _ = ndi.label(np.array(m) > 0)
    keep = np.unique(lab_[np.array(mn) > 0])
    full = np.isin(lab_, keep[keep > 0])
    isl = ndi.binary_erosion(full, iterations=2)
    L = color.rgb2lab(t / 255.0)[..., 0]
    seam = isl & (L - ndi.median_filter(L, 21) > 5)
    seam = ndi.binary_dilation(seam, iterations=2) & isl
    seam |= ndi.binary_dilation(full, iterations=3) & ~ndi.binary_erosion(full, iterations=BAND)  # the border of the island: the line seen in the profile
    print('island', int(isl.sum()), 'seam texels', int(seam.sum()))
    ys, xs = np.where(ndi.binary_dilation(full, iterations=30))
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    sm = seam[y0:y1, x0:x1]
    res = np.array(SimpleLama()(Image.fromarray(t[y0:y1, x0:x1]), Image.fromarray((sm * 255).astype(np.uint8))))
    res = res[:y1 - y0, :x1 - x0]
    out = t.copy()
    out[y0:y1, x0:x1][sm] = res[sm]
    Image.fromarray(out).save(dst)


if __name__ == '__main__':
    main()
