#!/usr/bin/env python3
"""Offline probe of the fold under the eye (ours): no game run needed.

fold_probe.py [glb] [eye_open.json]
Prints, for the right eye, a vertical cross-section of the head surface through the centre of the eye (y, z, normal
tilt, texture colour of the nearest vertex) and the sharpest edges (dihedral angle) in the area under the eye; saves
fold_profile.png (depth z over the face, crease edges marked)."""
import sys
import json
import numpy as np
import trimesh
from PIL import Image

glb = sys.argv[1] if len(sys.argv) > 1 else 'work/hero1_eye.glb'
polys = json.load(open(sys.argv[2] if len(sys.argv) > 2 else 'work/eye_open.json'))
sc = trimesh.load(glb)
g = sc.geometry['geometry_0']
V, T = g.vertices, g.faces
tex = np.array(g.visual.material.baseColorTexture.convert('RGB'))
uv = g.visual.uv
p = np.array(polys['R'])
c = p.mean(0)
w = np.ptp(p[:, 0])
h = np.ptp(p[:, 1])
print(f'eye centre {c.round(4)} width {w:.3f} height {h:.3f}')
fn = g.face_normals
front = V[T].mean(1)[:, 2] > 0.25
print('\nsection x=%.3f (+-%.3f): y, z, normal tilt (deg from +z), colour' % (c[0], w * 0.1))
sel = np.where((np.abs(V[:, 0] - c[0]) < w * 0.1) & (V[:, 2] > 0.25))[0]
sel = sel[np.argsort(-V[sel, 1])]
vn = g.vertex_normals
last = None
for i in sel:
    y = V[i, 1]
    if y > c[1] + 1.2 * h or y < c[1] - 4 * h:
        continue
    if last is not None and abs(last - y) < h * 0.15:
        continue
    last = y
    u, v = uv[i]
    col = tex[min(2047, int((1 - v) * tex.shape[0])), min(2047, int(u * tex.shape[1]))]
    tilt = np.degrees(np.arccos(np.clip(vn[i, 2], -1, 1)))
    print(f'  y {y:+.4f}  z {V[i, 2]:.4f}  tilt {tilt:5.1f}  rgb {col}')
adj = g.face_adjacency
ang = np.degrees(g.face_adjacency_angles)
ctr = V[T].mean(1)
area = lambda f: (np.abs(ctr[f][:, 0] - c[0]) < w * 0.8) & (ctr[f][:, 1] < c[1]) & (ctr[f][:, 1] > c[1] - 4 * h) & (ctr[f][:, 2] > 0.25)
m = area(adj[:, 0]) & area(adj[:, 1])
print('\nedges under the eye: %d, dihedral > 25 deg: %d, > 40: %d' % (m.sum(), (m & (ang > 25)).sum(), (m & (ang > 40)).sum()))
for k in np.argsort(-ang * m)[:8]:
    if m[k]:
        e = g.face_adjacency_edges[k]
        print('  angle %.1f at %s' % (ang[k], V[e].mean(0).round(4)))
# vertices of the same position with different normals/UV (split along a seam)
key = {}
for i, q in enumerate(V.round(5)):
    key.setdefault(tuple(q), []).append(i)
seam = [ids for ids in key.values() if len(ids) > 1 and abs(ids and V[ids[0]][0] - c[0]) < w * 0.8 and c[1] - 4 * h < V[ids[0]][1] < c[1]]
print('split vertices (UV seam) under the eye:', len(seam))
# depth map image
S = 400
x0, x1, y0, y1 = c[0] - w, c[0] + w, c[1] - 4 * h, c[1] + 1.5 * h
img = np.zeros((S, S, 3), np.uint8)
for i in np.where((V[:, 2] > 0.25) & (V[:, 0] > x0) & (V[:, 0] < x1) & (V[:, 1] > y0) & (V[:, 1] < y1))[0]:
    px, py = int((V[i, 0] - x0) / (x1 - x0) * (S - 1)), int((y1 - V[i, 1]) / (y1 - y0) * (S - 1))
    z = (V[i, 2] - 0.28) / 0.07
    img[py, px] = np.clip([z * 255] * 3, 0, 255)
for k in np.where(m & (ang > 25))[0]:
    e = V[g.face_adjacency_edges[k]].mean(0)
    px, py = int((e[0] - x0) / (x1 - x0) * (S - 1)), int((y1 - e[1]) / (y1 - y0) * (S - 1))
    if 0 <= px < S and 0 <= py < S:
        img[py, px] = (255, 0, 0)
Image.fromarray(img).resize((800, 800), Image.NEAREST).save('fold_profile.png')
