#!/usr/bin/env python3
"""Eye patches that close the slit of the lids (ours), a replacement of the eyeball of eye_slit.py.

The ellipsoid eyeball of eye_slit.py sat 12-26 mm behind the rim of the slit: seen from the side the gap between the
rim and the ball let the inside of the head show through and the eyes "did not reach the model". Here the hole that
drop_mask() cuts is filled by a patch: its edge is the very loop of vertices of the hole (the same points, no gap), the
inside is a grid with the height of the rim interpolated over it plus a dome (DOME of the head height) of the eye.

The texture is an atlas of 256x256 texels with one eye window per eye (planar from the front view, WINDOW_W texels
wide); everything outside the windows is skin, because the engine blinks it (location Character::UpdateEyeBlink,
resource/ini/eyes.ini [<texture>]): the rows of the window are squeezed to its middle row and the rows over and under
come from the skin row, so the lids close from the edges. The windows go to tools/pdm_eyes.py AI_EYES (written to
eyes.ini by pdm_glb2gm.py), the same numbers as here: WINDOWS.

  patches(W, F, drop, polys, view, lo, hi) -> (trimesh with the atlas, {'R': (x0, x1, y0, y1), 'L': ...}, skin_row)"""
import numpy as np
import trimesh
from PIL import Image
from matplotlib.path import Path
from scipy import ndimage as ndi
from scipy.spatial import Delaunay
from scipy.interpolate import LinearNDInterpolator, NearestNDInterpolator
import eye_slit

TEX = 256
WINDOW_W = 112.0  # texels: the width of an eye on the atlas
CENTRE = {'R': (64.0, 128.0), 'L': (192.0, 128.0)}  # centres of the windows (u, v from the top), texels
CELL = 2.0  # texels between the vertices of the grid: the lids close smoothly (the engine squeezes the rows by vertices)
DOME = 0.012  # the bulge of the eye over the rim of the slit, of the head height
PAD = 1.0  # texels added to the window around the vertices of the patch


def hole_loops(F, drop):
    """The loops of vertices (ids) around the dropped faces: edges of a dropped face whose other face is kept."""
    edges = {}
    for i, f in enumerate(F):
        ids = [p[0] for p in f]
        for a, b in zip(ids, ids[1:] + ids[:1]):
            edges.setdefault((min(a, b), max(a, b)), []).append(i)
    nxt = {}
    for f, d in zip(F, drop):
        if not d:
            continue
        ids = [p[0] for p in f]
        for a, b in zip(ids, ids[1:] + ids[:1]):
            if sum(drop[j] for j in edges[(min(a, b), max(a, b))]) == 1:
                nxt.setdefault(a, []).append(b)
    loops, seen = [], set()
    for s in list(nxt):
        if s in seen:
            continue
        loop, cur = [s], s
        seen.add(s)
        while True:
            c = [n for n in nxt.get(cur, []) if n not in seen]
            if not c:
                break
            cur = c[0]
            loop.append(cur)
            seen.add(cur)
        if len(loop) >= 6:
            loops.append(loop)
    return loops


def side_of(poly, polys):
    for k, p in polys.items():
        if np.allclose(np.mean(p, 0), np.mean(poly, 0)):
            return k
    return None


def fill_patch(P, z, scale):
    """Triangles and heights of a patch over the loop P (n x 2, head units) with the heights z of its vertices."""
    path = Path(P)
    step = CELL / scale
    lo, hi = P.min(0), P.max(0)
    gx, gy = np.meshgrid(np.arange(lo[0], hi[0], step), np.arange(lo[1], hi[1], step))
    g = np.c_[gx.ravel(), gy.ravel()]
    g = g[path.contains_points(g)]
    # distance of the grid points to the loop: points closer than a half step to it are left to the loop itself
    seg = np.stack([P, np.roll(P, -1, 0)], 1)
    d = np.full(len(g), np.inf)
    for a, b in seg:
        ab = b - a
        t = np.clip(((g - a) @ ab) / max(ab @ ab, 1e-12), 0, 1)
        d = np.minimum(d, np.linalg.norm(g - (a + t[:, None] * ab), axis=1))
    g, d = g[d > 0.6 * step], d[d > 0.6 * step]
    pts = np.vstack([P, g])
    tri = Delaunay(pts).simplices
    cen = pts[tri].mean(1)
    tri = tri[path.contains_points(cen)]
    # the height of the rim over the inside, the dome grows with the distance from the rim
    lin = LinearNDInterpolator(P, z)
    zi = lin(g)
    bad = np.isnan(zi)
    if bad.any():
        zi[bad] = NearestNDInterpolator(P, z)(g[bad])
    dmax = max(d.max(), 1e-9)
    s = np.clip(d / dmax, 0, 1)
    dome = DOME * (s * s * (3 - 2 * s))
    return pts, tri, np.concatenate([z, zi + dome])


def rim_colour(F, drop, loop, vt, tex, W):
    """Median colour of the head texture on the skin around the hole (vertices 1.4-2.4 times the hole away from its
    centre, in front): the skin the patch must match; the vertices on the rim itself are in the shadow of the lids."""
    S = tex.shape[0]
    c = W[loop][:, :2].mean(0)
    r = np.linalg.norm(W[loop][:, :2] - c, axis=1).max()
    cols = {}
    for f, d in zip(F, drop):
        if d:
            continue
        for v, u in f:
            dist = np.linalg.norm(W[v][:2] - c)
            if v not in cols and 1.4 * r < dist < 2.4 * r and W[v][2] > 0.25:
                x, y = vt[u]
                cols[v] = tex[min(S - 1, max(0, int((1 - y) * S))), min(S - 1, max(0, int(x * S)))]
    return np.median(list(cols.values()), 0)


def patches(W, F, drop, polys, view, lo, hi, head=None):
    loops = hole_loops(F, drop)
    W = np.asarray(W, float)
    kept = np.array([[p[0] for p in f[:3]] for f, d in zip(F, drop) if not d])
    hn = trimesh.Trimesh(W, kept, process=False).vertex_normals  # the shading of the rim: the patch takes it over
    height = float(np.ptp(W[:, 1]))
    front = view[0]
    S = front.shape[0]
    atlas = np.zeros((TEX, TEX, 3), float)
    verts, uvs, tris, windows, norms = [], [], [], {}, []
    skin = None
    for k, poly in polys.items():
        P0 = np.array(poly)
        c = P0.mean(0)
        loop = [l for l in loops if np.linalg.norm(W[l][:, :2].mean(0) - c) < 0.5 * np.ptp(P0[:, 0])]
        if not loop:
            raise SystemExit(f'eye_patch: no hole around the eye {k}')
        # the outer loops: those not inside a wider one (the stacked layers of the pit and the islands give inner loops);
        # a hole of two separate pieces gets a patch on each
        loop.sort(key=lambda l: -np.ptp(W[l][:, 0]))
        outer = []
        for l in loop:
            if not any(Path(W[o][:, :2]).contains_point(W[l][:, :2].mean(0)) for o in outer):
                outer.append(l)
        scale = WINDOW_W / np.ptp(P0[:, 0])  # texels per head unit
        cu, cv = CENTRE[k]
        to_uv = lambda xy: np.c_[cu + (xy[:, 0] - c[0]) * scale, cv - (xy[:, 1] - c[1]) * scale]
        parts = []
        for loop in outer:
            L = W[loop]
            pts, tri, z = fill_patch(L[:, :2], L[:, 2], scale)
            # the normals of the patch: those of the rim vertices carried over the inside (a flat patch lit its own way:
            # the pink circles under the eyes)
            ln = hn[loop].copy()
            ln[ln[:, 2] < 0] *= -1  # the faces of the pit were folded by the wrap: their normals look inside
            nn = np.vstack([ln, np.zeros((len(pts) - len(loop), 3))])
            gi = np.arange(len(loop), len(pts))
            for ax in range(3):
                v = LinearNDInterpolator(L[:, :2], ln[:, ax])(pts[gi])
                bad = np.isnan(v)
                v[bad] = NearestNDInterpolator(L[:, :2], ln[:, ax])(pts[gi][bad])
                nn[gi, ax] = v
            nn /= np.maximum(np.linalg.norm(nn, axis=1, keepdims=True), 1e-9)
            parts.append((pts, tri, z, nn))
        off = np.cumsum([0] + [len(p[0]) for p in parts])
        pts = np.vstack([p[0] for p in parts])
        tri = np.vstack([p[1] + o for p, o in zip(parts, off)])
        z = np.concatenate([p[2] for p in parts])
        nn = np.vstack([p[3] for p in parts])
        uv = to_uv(pts)
        norms.append(nn)
        windows[k] = [float(uv[:, 0].min() - PAD), float(uv[:, 0].max() + PAD), float(uv[:, 1].min() - PAD),
                      float(uv[:, 1].max() + PAD)]
        # the texels of the atlas around this eye -> a point of the head plane -> the pixel of the front view
        ys, xs = np.mgrid[0:TEX, 0:TEX]
        tx, ty = xs + 0.5, ys + 0.5
        reg = (np.abs(tx - cu) <= WINDOW_W * 0.57) & (np.abs(ty - cv) <= WINDOW_W * 0.4)
        hx = c[0] + (tx - cu) / scale
        hy = c[1] - (ty - cv) / scale
        col, row = eye_slit.proj(view, lo, hi, np.c_[hx[reg], hy[reg], np.zeros(reg.sum())])
        img = np.zeros((TEX, TEX, 3))
        img[reg] = front[np.clip(row.astype(int), 0, S - 1), np.clip(col.astype(int), 0, S - 1)]
        ok = np.zeros((TEX, TEX), bool)
        ok[reg] = Path(c + (P0 - c) * eye_slit.PAD).contains_points(np.c_[hx[reg], hy[reg]])
        # skin around the opening, for the whole atlas and for the skin row of the engine
        ring = reg & ~ndi.binary_dilation(ok, iterations=3) & ndi.binary_dilation(ok, iterations=14)
        skin_c = np.median(img[ring], 0) if ring.any() else np.array([200., 150., 120.])
        if head is not None:  # the colour of the head texture itself: the patch has no lighter circles under the eyes
            skin_c = rim_colour(F, drop, loop, *head, W)
        iy, ix = ndi.distance_transform_edt(~ok, return_distances=False, return_indices=True)
        out = img[iy, ix]
        sub = (slice(int(cv - 0.4 * WINDOW_W), int(cv + 0.4 * WINDOW_W)), slice(int(cu - 0.57 * WINDOW_W), int(cu + 0.57 * WINDOW_W)))
        o2, m2 = out[sub], ok[sub]
        o2 = eye_slit.lower_sclera(o2, m2)
        o2 = eye_slit.look_ahead(o2, m2)
        out[sub] = o2
        # the picture fades into the skin colour away from the opening: no orange arcs at the edge of the window
        w = np.clip(ndi.distance_transform_edt(~m2) / 3.0, 0, 1)[..., None]
        atlas[sub] = o2 * (1 - w) + skin_c * w
        skin = skin_c if skin is None else (skin + skin_c) / 2
        n0 = sum(len(v) for v in verts)
        verts.append(np.c_[pts, z])
        uvs.append(uv)
        tris.append(tri + n0)
    # the atlas outside the windows is skin, inside the windows - the eye pictures; the windows are cut out whole
    full = np.tile(skin, (TEX, TEX, 1))
    for k, (x0, x1, y0, y1) in windows.items():
        a, b, c0, d = int(np.floor(x0)), int(np.ceil(x1)), int(np.floor(y0)), int(np.ceil(y1))
        full[c0:d, a:b] = atlas[c0:d, a:b]
    skin_row = max(y1 for _, _, _, y1 in windows.values()) + 6.0
    V = np.vstack(verts)
    UV = np.vstack(uvs) / TEX
    T = np.vstack(tris)
    # the front of the patch looks along +z
    n = np.cross(V[T[:, 1]] - V[T[:, 0]], V[T[:, 2]] - V[T[:, 0]])
    T[n[:, 2] < 0] = T[n[:, 2] < 0][:, ::-1]
    tex = Image.fromarray(full.clip(0, 255).astype(np.uint8))
    m = trimesh.Trimesh(V, T, vertex_normals=np.vstack(norms), process=False)
    m.visual = trimesh.visual.TextureVisuals(uv=np.c_[UV[:, 0], 1 - UV[:, 1]], material=trimesh.visual.material.PBRMaterial(
        baseColorTexture=tex, metallicFactor=0.0, roughnessFactor=0.5))
    return m, windows, float(skin_row)
