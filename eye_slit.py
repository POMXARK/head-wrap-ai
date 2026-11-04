#!/usr/bin/env python3
"""Eye slit and eyeballs (ours): the faces of the head inside the eye opening are dropped and an ellipsoid eyeball
with a texture taken from the Qwen front view is put behind them.

eye_slit.py is used by export.py (--slit eye_open.json front.png target.glb); alone it writes a test glb.
- drop_mask(W, F, polys): face of the template (vertex ids) whose centre falls inside an opening polygon (xy), on the
  front (z > 0.25);
- eyeball(poly, W, front, target): UV ellipsoid (equirectangular UV, axis y, front pole at u = 0.5, v = 0.5), the
  centre BALL_BACK behind the skin surface at the centre of the opening, semi-axes BALL = (rx, ry, rz). Colours: where
  the front view sees the ball inside the opening (padded by PAD) - its pixel; everywhere else the mean sclera colour."""
import numpy as np
import trimesh
from PIL import Image
from matplotlib.path import Path
import sys
sys.path.insert(0, '../corsairs-remake/tools')
import pdm_project_views as pv  # noqa: E402

RX, RY, RZ = 0.62, 0.95, 0.03  # semi-axes: of the opening width, of its height, absolute
BALL_BACK = 0.012  # the pole stands RZ - BALL_BACK = 4 mm before the skin
PAD = 1.25  # the opening is enlarged about its centre for the colours: the ball shows under the lid rim
N_LON, N_LAT = 48, 24
TEX = 256


LOW = 0.55  # the lower half of the slit is this much of the opening
SHRINK = (0.97, 0.8)  # the slit is a little smaller than the opening read from the view: the lid rim covers its edge


def look_ahead(out, okm):
    """The Qwen face looks aside: the iris (the darkest part of the opening, near the middle of the ball) is rolled to the
    front pole of the texture, so both eyes look straight ahead (ours)."""
    h, w = okm.shape
    g = out.mean(2)
    ys, xs = np.where(okm)
    dark = g[ys, xs] <= np.percentile(g[ys, xs], 15)
    cy, cx = ys[dark].mean(), xs[dark].mean()
    dy, dx = 0, int(round(w / 2 - cx))  # only sideways: a vertical roll brings the lid shadow into the eye
    return np.roll(np.roll(out, dx, axis=1), dy, axis=0)


def lower_sclera(out, okm):
    """Below the iris the Qwen view shows the grey wet line of the lower lid and the nearest-colour fill smears it into
    radial streaks: that part is one sclera colour (median of the bright texels of the opening) fading to 0.85 at the bottom."""
    from scipy import ndimage as ndi
    ys, xs = np.where(okm)
    L = out.max(2)
    dark = okm & (L <= np.percentile(L[okm], 30))
    iris_bot = np.percentile(np.where(dark)[0], 99) + 3
    row = np.arange(okm.shape[0])[:, None] <= iris_bot
    br = okm & row & (L >= np.percentile(L[okm & row], 92))  # the sclera beside the iris, above the lower lid
    sc = np.median(out[br], 0) * np.array([1.04, 1.0, 0.95])
    bot = ys.max()
    rows = np.arange(okm.shape[0])[:, None]
    t = np.clip((rows - iris_bot) / max(bot - iris_bot, 1), 0, 1)  # 0 at the iris, 1 at the lid
    wgt = ndi.gaussian_filter(np.clip(t * 6, 0, 1), 1.5)[..., None]
    shade = (1 - 0.08 * t)[..., None]
    return out * (1 - wgt) + sc * shade * wgt


def drop_mask(W, F, polys):
    drop = np.zeros(len(F), bool)
    for p in polys.values():
        p = np.array(p)
        c = p.mean(0)
        q = c + (p - c) * SHRINK
        low = q[:, 1] < c[1]
        q[low, 1] = c[1] + (q[low, 1] - c[1]) * LOW  # the lower lid: the ball under it showed as a grey band from below
        path = Path(q)
        for i, f in enumerate(F):
            c = W[[q[0] for q in f]].mean(0)
            if c[2] > 0.25 and path.contains_point(c[:2]):
                drop[i] = True
    return drop


def surface_z(W, P):
    """z of the skin around the opening: the median of the front vertices in the ring 1.0-1.5 times the polygon"""
    c = P.mean(0)
    ring = Path(c + (P - c) * 1.5).contains_points(W[:, :2]) & ~Path(c + (P - c) * 1.0).contains_points(W[:, :2]) & (W[:, 2] > 0.25)
    return float(np.median(W[ring][:, 2]))


def proj(view, lo, hi, X):
    """pixels (column, row) of the head points in the front view, as bake.py / pdm_project_views.project"""
    return pv.project(np.asarray(X, float), 'front', view, lo, hi)


def eyeball(poly, W, view, lo, hi):
    front = view[0]
    P = np.array(poly)
    c = P.mean(0)
    w, h = np.ptp(P[:, 0]), np.ptp(P[:, 1])
    BALL = (RX * w, RY * h, RZ)
    cz = surface_z(W, P) - BALL_BACK
    lon = (np.arange(N_LON + 1) / N_LON - 0.5) * 2 * np.pi
    lat = (0.5 - np.arange(N_LAT + 1) / N_LAT) * np.pi
    LO, LA = np.meshgrid(lon, lat)
    d = np.stack([np.cos(LA) * np.sin(LO), np.sin(LA), np.cos(LA) * np.cos(LO)], -1)
    X = d * np.array(BALL) + np.array([c[0], c[1], cz])
    uv = np.stack([np.meshgrid(np.arange(N_LON + 1) / N_LON, 1 - np.arange(N_LAT + 1) / N_LAT)[0],
                   np.meshgrid(np.arange(N_LON + 1) / N_LON, 1 - np.arange(N_LAT + 1) / N_LAT)[1]], -1)
    S = front.shape[0]
    # sclera colour: bright pixels of the opening
    pad = c + (P - c) * PAD
    path = Path(pad)
    gx, gy = np.meshgrid(np.linspace(P[:, 0].min(), P[:, 0].max(), 80), np.linspace(P[:, 1].min(), P[:, 1].max(), 40))
    g = np.c_[gx.ravel(), gy.ravel()]
    g = g[Path(P).contains_points(g)]
    cg, rg = proj(view, lo, hi, np.c_[g, np.zeros(len(g))])
    px = front[np.clip(rg.astype(int), 0, S - 1), np.clip(cg.astype(int), 0, S - 1)].astype(float)
    br = px.max(1)
    sclera = np.median(px[br >= np.percentile(br, 70)], 0)
    # texture: every texel of the equirectangular map -> the point of the ball -> the front pixel
    n = TEX
    u = (np.arange(n) + 0.5) / n
    v = (np.arange(n // 2) + 0.5) / (n // 2)
    U, V = np.meshgrid(u, v)
    lo_ = (U - 0.5) * 2 * np.pi
    la = (0.5 - V) * np.pi
    dd = np.stack([np.cos(la) * np.sin(lo_), np.sin(la), np.cos(la) * np.cos(lo_)], -1)
    pt = dd * np.array(BALL) + np.array([c[0], c[1], cz])
    ct, rt = proj(view, lo, hi, pt.reshape(-1, 3))
    img = front[np.clip(rt.astype(int), 0, S - 1), np.clip(ct.astype(int), 0, S - 1)].astype(float)
    ok = path.contains_points(pt.reshape(-1, 3)[:, :2]) & (dd.reshape(-1, 3)[:, 2] > 0.2)
    okm = ok.reshape(n // 2, n)
    out = img.reshape(n // 2, n, 3).copy()
    # outside the opening the texel takes the nearest colour of the opening (the slit is a little larger than the
    # polygon by the size of a face): the lid rim colour, not a flat grey
    from scipy import ndimage as ndi
    iy, ix = ndi.distance_transform_edt(~okm, return_distances=False, return_indices=True)
    out = out[iy, ix]
    out = lower_sclera(out, okm)
    out = look_ahead(out, okm)
    tex = Image.fromarray(out.clip(0, 255).astype(np.uint8))
    faces = []
    for j in range(N_LAT):
        for i in range(N_LON):
            a = j * (N_LON + 1) + i
            b = a + 1
            c2 = a + N_LON + 1
            d2 = c2 + 1
            faces += [[a, c2, b], [b, c2, d2]]
    m = trimesh.Trimesh(X.reshape(-1, 3), np.array(faces), process=False)
    m.visual = trimesh.visual.TextureVisuals(uv=uv.reshape(-1, 2), material=trimesh.visual.material.PBRMaterial(
        baseColorTexture=tex, metallicFactor=0.0, roughnessFactor=0.5))
    # outward: the triangles face along the sphere normal
    nrm = np.cross(m.vertices[m.faces[:, 1]] - m.vertices[m.faces[:, 0]], m.vertices[m.faces[:, 2]] - m.vertices[m.faces[:, 0]])
    cen = m.vertices[m.faces].mean(1) - np.array([c[0], c[1], cz])
    if (nrm * cen).sum() < 0:
        m.faces = m.faces[:, ::-1]
    return m, tex
