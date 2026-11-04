#!/usr/bin/env python3
"""Score of the whole head surface (ours): finds the shards - single triangles whose skin colour differs from their neighbours
(the stretched or mis-mapped UV of the new mesh), and the triangles whose texture is stretched (few texels per unit of surface).

mesh_score.py [glb] [--png out.png] [--json out.json]   exit code 1 if a check fails
  shard    share of the head triangles whose mean colour differs from the median of the edge neighbours by > SHARD_DL (L units)
  stretch  share of the triangles whose texel density is below STRETCH x the median of the head (a magnified, blocky texture)
  seam     share of the edges where the colour jumps by > SEAM_DL although the UV is continuous (a texture crack inside a chart)
The zones (ear, cheek, neck, ...) are boxes of the head in head units; the score is the share of passed checks.
--png draws a profile of the head with the flagged triangles in red (shards) and blue (stretch)."""
import sys
import json
import numpy as np
import trimesh
from skimage import color
import eye_score

SHARD_DL = 14.0
STRETCH = 0.25
SEAM_DL = 18.0
THRESH = {'shard': 0.02, 'stretch': 0.03, 'seam': 0.03}


def face_colours(V, F, UV, tex):
    """Mean Lab colour of a triangle (centroid and the three points halfway to the corners)."""
    pts = [UV[F].mean(1)] + [0.5 * UV[F].mean(1) + 0.5 * UV[F][:, i] for i in range(3)]
    c = np.mean([eye_score.sample(tex, p) for p in pts], 0)
    return color.rgb2lab(c.reshape(-1, 1, 3) / 255.0)[:, 0, :]


def analyse(glb):
    sc = trimesh.load(glb)
    g = sc.geometry['geometry_0']
    V, F, UV, tex = g.vertices, g.faces, g.visual.uv, np.array(g.visual.material.baseColorTexture.convert('RGB'), float)
    lab = face_colours(V, F, UV, tex)
    adj = g.face_adjacency
    nb = [[] for _ in range(len(F))]
    for a, b in adj:
        nb[a].append(b)
        nb[b].append(a)
    dl = np.zeros(len(F))
    for i, n in enumerate(nb):
        if len(n) >= 2:
            dl[i] = abs(lab[i, 0] - np.median(lab[n, 0]))
    shard = dl > SHARD_DL
    a3 = np.linalg.norm(np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]]), axis=1) / 2
    ta = np.abs(np.cross(UV[F[:, 1]] - UV[F[:, 0]], UV[F[:, 2]] - UV[F[:, 0]])) / 2
    ok = a3 > 1e-12
    dens = np.where(ok, ta / np.maximum(a3, 1e-12), 0)
    stretch = ok & (dens < STRETCH * np.median(dens[ok]))
    # edges with the same UV on both sides (no seam) whose colour still jumps
    sh = np.zeros(len(adj), bool)
    d = np.abs(lab[adj[:, 0], 0] - lab[adj[:, 1], 0])
    sh = d > SEAM_DL
    return dict(V=V, F=F, shard=shard, stretch=stretch, dl=dl, seam=sh, adj=adj, tex=tex, g=g, lab=lab)


def zones(V):
    """Named boxes in head units, derived from the bounding box (x across, y up, z forward)."""
    lo, hi = V.min(0), V.max(0)
    s = hi - lo
    return {'head': (lo, hi),
            'face': ((lo[0], lo[1] + 0.25 * s[1], lo[2] + 0.45 * s[2]), (hi[0], lo[1] + 0.75 * s[1], hi[2])),
            'neck': ((lo[0], lo[1], lo[2]), (hi[0], lo[1] + 0.25 * s[1], hi[2])),
            'ear_side': ((lo[0], lo[1] + 0.3 * s[1], lo[2] + 0.2 * s[2]), (lo[0] + 0.2 * s[0], lo[1] + 0.7 * s[1], lo[2] + 0.6 * s[2]))}


def main():
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    glb = a[0] if a else 'work/hero1_eye.glb'
    r = analyse(glb)
    V, F = r['V'], r['F']
    cen = V[F].mean(1)
    out = {}
    print('%-9s %8s %8s %8s %6s' % ('zone', 'shard', 'stretch', 'seam', 'faces'))
    bad = 0
    for k, (lo, hi) in zones(V).items():
        m = np.all((cen >= lo) & (cen <= hi), 1)
        n = max(int(m.sum()), 1)
        ec = cen[r['adj']].mean(1)
        mid = np.all((ec >= lo) & (ec <= hi), 1)
        o = {'shard': float(r['shard'][m].sum() / n), 'stretch': float(r['stretch'][m].sum() / n),
             'seam': float(r['seam'][mid].sum() / max(int(mid.sum()), 1)), 'faces': n}
        out[k] = o
        flags = ['' if o[c] <= THRESH[c] else '!' for c in ('shard', 'stretch', 'seam')]
        bad += sum(f == '!' for f in flags)
        print('%-9s %7.3f%s %7.3f%s %7.3f%s %6d' % (k, o['shard'], flags[0], o['stretch'], flags[1], o['seam'], flags[2], n))
    total = 3 * len(out)
    s = 100.0 * (total - bad) / total
    print(f'mesh score {s:.0f}/100 ({total - bad}/{total} checks)')
    if '--png' in sys.argv:
        from PIL import Image
        box = (V[:, 2].min() - 0.02, V[:, 2].max() + 0.02, V[:, 1].min() - 0.02, V[:, 1].max() + 0.02)
        eye_score.RES = 0.0015
        g = r['g']
        tex = r['tex']
        shots = []
        for yaw in (90, -90):
            # profile: the view axis is z after the turn; box is given as (x0, x1, y0, y1) in the turned frame
            parts = [(g.vertices.copy(), g.faces, g.vertex_normals.copy(), g.visual.uv, tex, 0)]
            b2 = (V[:, 0].min() - 0.02, V[:, 0].max() + 0.02, box[2], box[3]) if False else (-1.2 * np.abs(V).max(), 1.2 * np.abs(V).max(), box[2], box[3])
            zb, idb, nb, col = eye_score.render(parts, b2, yaw)
            lit = col * (0.35 + 0.65 * np.clip(nb @ eye_score.LIGHT, 0, 1))[..., None]
            img = np.clip(lit, 0, 255).astype(np.uint8)
            a_ = np.radians(yaw)
            R = np.array([[np.cos(a_), 0, np.sin(a_)], [0, 1, 0], [-np.sin(a_), 0, np.cos(a_)]])
            P = cen @ R.T
            for flag, c in ((r['shard'], (255, 0, 0)), (r['stretch'], (0, 120, 255))):
                px = ((P[flag, 0] - b2[0]) / eye_score.RES).astype(int)
                py = ((b2[3] - P[flag, 1]) / eye_score.RES).astype(int)
                ok = (px >= 1) & (px < img.shape[1] - 1) & (py >= 1) & (py < img.shape[0] - 1) & (P[flag, 2] > 0)
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        img[py[ok] + dy, px[ok] + dx] = c
            shots.append(img)
        Image.fromarray(np.hstack(shots)).save(sys.argv[sys.argv.index('--png') + 1])
    if '--json' in sys.argv:
        json.dump({'score': s, 'zones': out}, open(sys.argv[sys.argv.index('--json') + 1], 'w'), indent=1)
    sys.exit(0 if bad == 0 else 1)


if __name__ == '__main__':
    main()
