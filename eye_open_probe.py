#!/usr/bin/env python3
"""Offline probe of the eye opening (ours): how wide the palpebral fissure is, no game run.

eye_open_probe.py [eye_open.json] [glb]
Per eye: the opening polygon (width, height, height/width, area), the share of the head height, the patch of the glb
(its box, the same ratio) and the open part of the atlas window (rows with the eye picture: sclera / iris, not skin).
A natural open eye has height/width about 0.30-0.38; below 0.25 the eyes look sleepy."""
import sys
import json
import numpy as np
import trimesh

polys = json.load(open(sys.argv[1] if len(sys.argv) > 1 else 'work/eye_open.json'))
sc = trimesh.load(sys.argv[2] if len(sys.argv) > 2 else 'work/hero1_eye.glb')
head = sc.geometry['geometry_0']
height = float(np.ptp(head.vertices[:, 1]))
patch = sc.geometry['geometry_1']
atlas = np.array(patch.visual.material.baseColorTexture.convert('RGB'), float)
skin = np.median(atlas[:6, :6].reshape(-1, 3), 0)
for k, p in polys.items():
    p = np.array(p)
    w, h = np.ptp(p[:, 0]), np.ptp(p[:, 1])
    area = 0.5 * abs(np.dot(p[:, 0], np.roll(p[:, 1], 1)) - np.dot(p[:, 1], np.roll(p[:, 0], 1)))
    print(f'{k}: opening {w:.4f} x {h:.4f}  height/width {h / w:.2f}  area/(w*h) {area / (w * h):.2f}  '
          f'width {100 * w / height:.1f}% of the head, height {100 * h / height:.1f}%')
    # the lids: the polygon above and below its middle line
    c = p[:, 1].mean()
    print(f'   upper part {p[:, 1].max() - c:.4f}, lower part {c - p[:, 1].min():.4f}  (the lower lid is shrunk by LOW in eye_slit)')
vs = patch.vertices
m = vs[:, 0] > 0
print(f'patch R box {np.ptp(vs[m, 0]):.4f} x {np.ptp(vs[m, 1]):.4f}  ratio {np.ptp(vs[m, 1]) / np.ptp(vs[m, 0]):.2f}')
for name, x0, x1 in (('R', 8, 121), ('L', 138, 246)):
    sub = atlas[100:160, x0:x1]
    eye = np.linalg.norm(sub - skin, axis=2) > 40
    rows = np.where(eye.sum(1) > 6)[0]
    if len(rows):
        print(f'atlas {name}: rows with the eye picture {rows.min() + 100}..{rows.max() + 100} ({len(rows)} rows) over {x1 - x0} texels: '
              f'ratio {len(rows) / (x1 - x0):.2f}')
