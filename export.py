#!/usr/bin/env python3
"""Stage 8: one glb from the layers: export.py wrapped.obj template.obj baked.png out.glb [--ponytail tube.obj hair.png] [--slit eye_open.json front.png target.glb]
The head keeps the constant UV of the template (the texture is baked into it); the ponytail is a second mesh with its own
material. Vertices are split per (v, vt) pair by hand, the order of the template is kept."""
import os
import sys
import numpy as np
import trimesh
from PIL import Image
from bake import read_v, read_uv_faces


UNDER_SCALE = 2.2  # the opening of the eye is taken this much bigger for the faces of the lower lid


PIT_SCALE = 3.0  # the pit round the eye is smoothed within this many times the opening
BROW_FADE = (0.1, 0.7)  # above the eye top: the pit fill fades out between these heights of the eye (full -> none): the brows stay original
BROW_GAP = 99  # the pit is filled up to the top of the eye plus this of its height: the brows stay as they were
FIT_MAX = 0.15  # largest UV distance a pit vertex may be moved by the refit (the islands of the atlas are further apart)
PIT_RINGS = 6  # rings of vertices round the pit that are filled with it
WEIGHT = {}  # the weight of the pit fill per vertex (1 at the eye, 0 up at the brows)
FREE = set()  # the vertices of the pits (smooth_pits): their UV is refitted from the skin round them (fit_uv)
PIT_Z = 0.32  # vertices of the face behind this depth under the eye are the floor of the pit


def smooth_pits(W, F, polys):  # sys.argv[1] is the wrapped obj
    """The wrapped head has a pit (the socket of the eyeball) round every eye: the lower lid is a dish, its wall shows
    as an orange arc in the game. The depth of the vertices in the pit is smoothed (Laplace, the vertices outside it
    stay), the dish becomes the skin of the cheek."""
    from matplotlib.path import Path
    W = np.array(W, float)
    nb = [set() for _ in W]
    for f in F:
        ids = [p[0] for p in f]
        for a in ids:
            nb[a].update(i for i in ids if i != a)
    free = np.zeros(len(W), bool)
    for p in polys.values():
        p = np.array(p)
        c = p.mean(0)
        w, h = np.ptp(p[:, 0]), np.ptp(p[:, 1])
        # the floor of the socket of the wrap: flat plate far behind the cheek (z < PIT_Z); its edge is the wall = the fold
        free |= (np.abs(W[:, 0] - c[0]) < 1.3 * w) & (W[:, 1] < p[:, 1].max() + BROW_GAP * h) & (W[:, 1] > c[1] - 5 * h) & (W[:, 2] > 0.25) & (W[:, 2] < PIT_Z)
    ytop = max(np.array(p)[:, 1].max() + BROW_GAP * np.ptp(np.array(p)[:, 1]) for p in polys.values())
    for _ in range(PIT_RINGS):  # a few rings of the lip round the pit too: no step where the plate meets the cheek
        grown = free.copy()
        for i in np.where(free)[0]:
            grown[list(nb[i])] = True
        free = grown & (W[:, 2] > 0.25) & (W[:, 1] < ytop)  # never up into the brows
    idx = np.where(free)[0]
    # harmonic fill: the free vertices take the mean of their neighbours, the vertices round the pit stay (exact solve)
    import scipy.sparse as sp
    from scipy.sparse.linalg import spsolve
    # biharmonic (min of |L z|^2, L = uniform Laplacian): the plate meets the cheek with the same slope, no crease
    n = len(W)
    rows, cols = [], []
    for i in range(n):
        for j in nb[i]:
            rows.append(i)
            cols.append(j)
    Adj = sp.csr_matrix((np.ones(len(rows)), (rows, cols)), shape=(n, n))
    Lp = sp.diags(np.asarray(Adj.sum(1)).ravel()) - Adj
    LtL = (Lp.T @ Lp).tocsr()
    fixed = np.setdiff1d(np.arange(n), idx)
    rhs = -LtL[idx][:, fixed] @ W[fixed, 2]
    znew = spsolve(LtL[idx][:, idx].tocsc(), rhs)
    top = max(np.array(p)[:, 1].max() for p in polys.values())
    hgt = float(np.mean([np.ptp(np.array(p)[:, 1]) for p in polys.values()]))
    t = np.clip((W[idx, 1] - top - BROW_FADE[0] * hgt) / ((BROW_FADE[1] - BROW_FADE[0]) * hgt), 0, 1)
    wgt = 1 - t * t * (3 - 2 * t)  # 1 at the eye, 0 at the brows
    W[idx, 2] = wgt * znew + (1 - wgt) * W[idx, 2]
    WEIGHT.clear()
    WEIGHT.update({int(v): float(x) for v, x in zip(idx, wgt)})
    FREE.clear()
    FREE.update(int(i) for i in idx)
    print('pit vertices smoothed', len(idx), 'max shift', float(abs(W[idx, 2] - np.array(read_v(sys.argv[1]))[idx, 2]).max()))
    return W


def lama_fill(img, mask):
    """The masked texels filled by LaMa (open source neural inpaint, as lama_seam.py): the grain of the face skin goes
    over the area, not a flat colour; cv2 Telea if the model is not there."""
    import os
    import cv2
    W = os.environ.get('W', '/media/roman/383be9ee-c114-4bf8-8956-66b985661cb4/home/remake-linux')
    os.environ.setdefault('LAMA_MODEL', W + '/lama/big-lama.pt')
    try:
        sys.path.insert(0, W + '/lama/pkg')
        from simple_lama_inpainting import SimpleLama
        ys, xs = np.where(mask > 0)
        y0, y1, x0, x1 = max(ys.min() - 40, 0), ys.max() + 41, max(xs.min() - 40, 0), xs.max() + 41
        res = np.array(SimpleLama()(Image.fromarray(img[y0:y1, x0:x1]), Image.fromarray(mask[y0:y1, x0:x1])))
        out = img.copy()
        h, w = img[y0:y1, x0:x1].shape[:2]
        out[y0:y1, x0:x1] = res[:h, :w]
        return out
    except Exception as e:  # noqa: BLE001
        print('lama unavailable, cv2 inpaint:', e)
        return cv2.inpaint(img, mask, 7, cv2.INPAINT_TELEA)


def under_eye_mask(W, vt, F, drop, polys, tex):
    """The texture with the flat pink circles under the eyes painted over from the skin around them (ours): the
    kept faces in the opening of the eye (the lower lid) got the colour of the pit of the bake, not the skin."""
    import cv2
    from matplotlib.path import Path
    from PIL import ImageDraw
    img = np.array(Image.open(tex).convert('RGB'))
    S = img.shape[0]
    m = Image.new('L', (S, S), 0)
    d = ImageDraw.Draw(m)
    for k, p in polys.items():
        p = np.array(p)
        c = p.mean(0)
        path = Path(c + (p - c) * UNDER_SCALE)
        for f, dr in zip(F, drop):
            if dr:  # the dropped faces: the picture of the eye on the texture is no longer needed
                d.polygon([(vt[u][0] * S, (1 - vt[u][1]) * S) for _, u in f], fill=255)
                continue
            q = W[[v for v, _ in f]]
            if q[:, 2].mean() > 0.25 and q[:, 1].mean() < p[:, 1].max() and path.contains_point(q[:, :2].mean(0)):  # not the brows
                d.polygon([(vt[u][0] * S, (1 - vt[u][1]) * S) for _, u in f], fill=255)
    mask = cv2.dilate(np.array(m), np.ones((5, 5), np.uint8))
    print('under-eye texels painted over', int((mask > 0).sum()))
    inp = lama_fill(img, mask).astype(float)
    # feathered edge: no round spot where the painted area ends
    a = cv2.GaussianBlur(cv2.dilate(mask, np.ones((5, 5), np.uint8)).astype(float) / 255, (0, 0), 18)[..., None]
    return Image.fromarray((inp * a + img * (1 - a)).clip(0, 255).astype(np.uint8))


def fit_uv(W, vt, F):
    """The UV of the pit vertices from the skin round them (ours): the template UV of the old eye socket is cramped (a
    few texels over the whole dish: blocks of magnified texture). The UV of the vertices outside the pit, a quadratic
    in (x, y) fitted to them (robust), is taken over the pit: the dish shows the face texture at its true scale."""
    if not FREE or os.environ.get('EYE_DBG') == 'nofit':
        return vt, F
    uvs = {}
    for f in F:
        for v, u in f:
            uvs.setdefault(v, set()).add(u)
    free = np.array(sorted(FREE))
    lo, hi = W[free][:, :2].min(0), W[free][:, :2].max(0)
    pad = 0.35 * (hi - lo)
    ring = [v for v, us in uvs.items() if v not in FREE and len(us) == 1 and W[v, 2] > 0.25
            and (lo - pad <= W[v, :2]).all() and (W[v, :2] <= hi + pad).all()]
    X = np.array([[1, W[v, 0], W[v, 1], W[v, 0] ** 2, W[v, 0] * W[v, 1], W[v, 1] ** 2] for v in ring])
    T = np.array([vt[next(iter(uvs[v]))] for v in ring])
    keep = np.ones(len(ring), bool)
    for _ in range(4):
        C = np.linalg.lstsq(X[keep], T[keep], rcond=None)[0]
        r = np.linalg.norm(X @ C - T, axis=1)
        keep = r < max(3 * np.median(r[keep]), 1e-4)
    vt = list(vt)
    new = {}
    base = list(vt)
    for v in FREE:
        x, y = W[v, 0], W[v, 1]
        fit = np.array([1, x, y, x * x, x * y, y * y]) @ C
        for u in uvs[v]:  # the weight blends the fit with the own UV of the vertex: no change at the brows
            if np.linalg.norm(fit - np.asarray(base[u])) > FIT_MAX:
                continue  # the vertex sits in another island (the old socket): the fit would stretch its faces across the atlas
            new[(v, u)] = len(vt)
            vt.append(WEIGHT.get(v, 1.0) * fit + (1 - WEIGHT.get(v, 1.0)) * np.asarray(base[u]))
    F = [[(v, new.get((v, u), u)) for v, u in f] for f in F]
    print('pit uv refitted: %d vertices from %d ring vertices, residual %.5f' % (len(FREE), int(keep.sum()), float(np.median(r[keep]))))
    return vt, F


def obj_mesh(vpath, tpath, tex, polys=None, W=None):
    W = read_v(vpath) if W is None else W
    vt, F = read_uv_faces(tpath)
    under = None
    if polys and FREE:
        vt, F = fit_uv(W, vt, F)
    if polys:
        import eye_slit
        drop = eye_slit.drop_mask(W, F, polys)
        print('slit: faces dropped', int(drop.sum()))
        under = None if os.environ.get('EYE_DBG') == 'nounder' else under_eye_mask(W, vt, F, drop, polys, tex)
        F = [f for f, d in zip(F, drop) if not d]
    pairs, idx, faces = {}, [], []
    for f in F:
        t = []
        for v, u in f:
            k = (v, u)
            if k not in pairs:
                pairs[k] = len(pairs)
                idx.append(k)
            t.append(pairs[k])
        faces.append(t)
    V = np.array([W[v] for v, _ in idx])
    if polys and FREE:  # the faces of the pit folded by the wrap look away: turn them to the front
        fa = np.array(faces)
        nrm = np.cross(V[fa[:, 1]] - V[fa[:, 0]], V[fa[:, 2]] - V[fa[:, 0]])
        inpit = np.array([all(idx[i][0] in FREE for i in f) for f in faces])
        flip = inpit & (nrm[:, 2] < 0)
        fa[flip] = fa[flip][:, ::-1]
        faces = fa.tolist()
        print('pit faces turned to the front:', int(flip.sum()))
    UV = np.array([vt[u] for _, u in idx])
    m = trimesh.Trimesh(V, np.array(faces), process=False)
    m.visual = trimesh.visual.TextureVisuals(uv=UV, material=trimesh.visual.material.PBRMaterial(
        baseColorTexture=under or Image.open(tex).convert('RGB'), metallicFactor=0.0, roughnessFactor=0.9))
    return m


def main():
    a = sys.argv[1:]
    sc = trimesh.Scene()
    polys = None
    if '--slit' in a:  # --slit eye_open.json front.png target.glb: slit in the lids and an eyeball behind each
        import json
        import eye_slit
        i = a.index('--slit')
        polys = json.load(open(a[i + 1]))
        tgt = trimesh.load(a[i + 3], force='mesh')
        import pdm_project_views  # noqa: F401
        view = eye_slit.pv.load_view(a[i + 2])
    Wp = None
    if polys:
        Wp = read_v(a[0])
        Wp = smooth_pits(Wp, read_uv_faces(a[1])[1], polys) if '--no-fold' not in a else Wp
    sc.add_geometry(obj_mesh(a[0], a[1], a[2], polys, Wp), node_name='head')
    if polys:
        W = Wp
        if '--ball' in a:  # the old ellipsoid eyeballs behind the slit (a gap shows between the rim and the ball)
            for k, p in polys.items():
                m, _ = eye_slit.eyeball(p, W, view, *tgt.bounds)
                sc.add_geometry(m, node_name='eye_' + k)
        else:  # one patch per eye in the very hole of the slit, both on one atlas (the blink of the engine, eyes.ini)
            import eye_patch
            vt, F = fit_uv(W, *read_uv_faces(a[1]))
            m, windows, skin_row = eye_patch.patches(W, F, eye_slit.drop_mask(W, F, polys), polys, view, *tgt.bounds,
                                                  head=(vt, np.array(Image.open(a[2]).convert('RGB'), float)))
            sc.add_geometry(m, node_name='eyes')
            print('eye windows', windows, 'skin row', skin_row)
            if '--eyes-json' in a:  # --eyes-json tools/eyes_ai.json key[,key...]: the windows for the blink (pdm_eyes.py)
                import json as _j
                i = a.index('--eyes-json')
                data = _j.load(open(a[i + 1])) if __import__('os').path.exists(a[i + 1]) else {}
                for key in a[i + 2].split(','):
                    data[key] = [[round(v, 1) for v in w] + [round(skin_row, 1)] for w in (windows['R'], windows['L'])]
                _j.dump(data, open(a[i + 1], 'w'), indent=1, sort_keys=True)
    if '--ponytail' in a:
        i = a.index('--ponytail')
        pm = obj_mesh(a[i + 1], a[i + 1], a[i + 2])
        if pm.volume < 0:  # the tube was wound inside out: the engine culled its outside and showed its inside
            pm.invert()
        sc.add_geometry(pm, node_name='ponytail')
    sc.export(a[3])
    g = trimesh.load(a[3])
    print('exported', a[3], {k: (len(v.vertices), len(v.faces)) for k, v in g.geometry.items()})


if __name__ == '__main__':
    main()
