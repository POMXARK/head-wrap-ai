#!/usr/bin/env python3
"""Colours of the head as in the original: Lab mean/std of skin and of hair of the baked texture are moved to those of
the original head texture (ours, the colours come from the original, the detail from the new texture).

colormatch.py baked.png template/head_sub.obj template/regions.json orig_hero.gm game_dir out.png [ponytail_in.png ponytail_out.png]
original skin: the vertices of the original head below the hair line in front; hair: the top and the back.
The std of a class is scaled by at most [STD_LO, STD_HI] so the detail stays; --strength 0..1 blends the shift."""
import sys
import pathlib
import numpy as np
from PIL import Image, ImageDraw
from skimage import color
import bake

STD_LO, STD_HI = 0.8, 1.25
SKIN = {'face', 'eyelid', 'ear', 'neck', 'lips', 'nose'}


def lab(a):
    return color.rgb2lab(np.clip(a, 0, 255).astype(np.uint8) / 255.0)


def stats(px):
    return px.mean(0), px.std(0)


def orig_classes(gm_path, game):
    sys.path.insert(0, str(pathlib.Path(game).parent / 'tools'))
    sys.path.insert(0, str(pathlib.Path(game).parent / 'engine' / 'demos' / 'common'))
    import pdm_model_views as m
    from storm_formats import read_tx
    gm = m.read_gm(pathlib.Path(gm_path))
    o = gm['objects'][0]
    tx = m.texture_of(m.texture_index(pathlib.Path(game)), o[1])
    img = np.array(read_tx(tx).convert('RGB'))
    h, w = img.shape[:2]
    p, uv = o[2], o[4]
    px = img[np.clip(((uv[:, 1] % 1) * h).astype(int), 0, h - 1), np.clip(((uv[:, 0] % 1) * w).astype(int), 0, w - 1)]
    top, bot = p[:, 1].max(), p[:, 1].min()
    skin = (p[:, 2] > 0.08) & (p[:, 1] < top - 0.09) & (p[:, 1] > bot + 0.06)
    hair = (p[:, 1] > top - 0.05) | (p[:, 2] < -0.03)
    return lab(px[skin].reshape(-1, 1, 3)).reshape(-1, 3), lab(px[hair].reshape(-1, 1, 3)).reshape(-1, 3)


def move(L, target, mask, strength):
    (m0, s0), (m1, s1) = stats(L[mask]), target
    k = np.clip(s1 / np.maximum(s0, 1e-6), STD_LO, STD_HI)
    new = (L[mask] - m0) * k + m1
    L[mask] = L[mask] + (new - L[mask]) * strength


def main():
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    strength = float(sys.argv[sys.argv.index('--strength') + 1]) if '--strength' in sys.argv else 1.0
    if '--strength' in sys.argv:
        a.remove(str(strength)) if str(strength) in a else None
    src, tpl, reg, gm, game, dst = a[:6]
    t = np.array(Image.open(src).convert('RGB')).astype(float)
    S = t.shape[0]
    import json
    r = json.load(open(reg))
    vt, F = bake.read_uv_faces(tpl)
    names = r['names']
    skin_m, hair_m = Image.new('L', (S, S), 0), Image.new('L', (S, S), 0)
    ds, dh = ImageDraw.Draw(skin_m), ImageDraw.Draw(hair_m)
    for f in F:
        cls = [names[r['vertex'][p[0]]] for p in f]
        poly = [(vt[p[1]][0] * S, (1 - vt[p[1]][1]) * S) for p in f]
        (dh if sum(c == 'scalp' for c in cls) >= 2 else ds).polygon(poly, fill=255)
    sk, ha = np.array(skin_m) > 0, np.array(hair_m) > 0
    ha &= ~sk
    Lt = lab(t)
    dark = (Lt[..., 0] < 40) & (np.hypot(Lt[..., 1], Lt[..., 2]) < 7)  # warm texels of the scalp (the hair line) are skin
    cov = sk | ha
    ha = cov & dark  # dark neutral texels are hair wherever they lie (side, beard, brows), the rest is skin
    sk = cov & ~dark
    ts, th = orig_classes(gm, game)
    L = lab(t)
    print('ours   skin', L[sk].mean(0).round(1), 'hair', L[ha].mean(0).round(1))
    print('orig   skin', ts.mean(0).round(1), 'hair', th.mean(0).round(1))
    from scipy import ndimage as ndi
    Ls, Lh = L.copy(), L.copy()
    move(Ls, stats(ts), sk, strength)
    move(Lh, stats(th), ha, strength)
    ws, wh = ndi.gaussian_filter(sk.astype(float), 3), ndi.gaussian_filter(ha.astype(float), 3)
    tot = np.maximum(ws + wh, 1.0)  # a soft border: no seam between the classes
    L = L + ((Ls - L) * ws[..., None] + (Lh - L) * wh[..., None]) / tot[..., None]
    out = np.clip(color.lab2rgb(L) * 255, 0, 255).astype(np.uint8)
    out[~(sk | ha)] = t[~(sk | ha)].astype(np.uint8)
    Image.fromarray(out).save(dst)
    if len(a) >= 8:
        p = np.array(Image.open(a[6]).convert('RGB')).astype(float)
        Lp = lab(p)
        move(Lp, stats(th), np.ones(Lp.shape[:2], bool), strength)
        Image.fromarray(np.clip(color.lab2rgb(Lp) * 255, 0, 255).astype(np.uint8)).save(a[7])
        print('ponytail ->', a[7])
    print('done ->', dst)


if __name__ == '__main__':
    main()
