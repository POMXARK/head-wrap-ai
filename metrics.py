#!/usr/bin/env python3
"""The judge on metrics (no VLM): metrics.py result.glb target.glb front.png left.png back.png right.png [--journal problem tool params]
Silhouettes of the result (all meshes of the glb) are drawn orthographically in the frame of the Qwen views (the box of the
target) and compared with the silhouette of every view: IoU, and the share of the view silhouette not covered (missing) and
of the result outside the view (extra). `mean_iou` is the number the agent can read; a change of a step is better when
mean_iou grows by more than EPS, worse when it falls by more than EPS (verdict_for)."""
import os
import sys
import numpy as np
import trimesh
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'corsairs-remake', 'tools'))
import pdm_project_views as pv  # noqa: E402
from bake import _tv  # noqa: E402

EPS = 0.003
SIZE = 512


def silhouette(meshes, name, lo, hi):
    img = Image.new('L', (SIZE, SIZE), 0)
    dr = ImageDraw.Draw(img)
    for m in meshes:
        tv, yv = _tv(pv, name, np.asarray(m.vertices), lo, hi)
        xy = np.stack([tv * (SIZE - 1), (1 - yv) * (SIZE - 1)], 1)
        for f in m.faces:
            dr.polygon([tuple(xy[i]) for i in f], fill=255)
    return np.asarray(img) > 0


def view_mask(path):
    f, (x0, x1, y0, y1), inner = pv.load_view(path)
    return np.asarray(Image.fromarray((inner[y0:y1 + 1, x0:x1 + 1] > 0.5).astype(np.uint8) * 255).resize((SIZE, SIZE), Image.BILINEAR)) > 127


def evaluate(result, target, views):
    T = trimesh.load(target, force='mesh')
    lo, hi = T.vertices.min(0), T.vertices.max(0)
    g = trimesh.load(result)
    meshes = list(g.geometry.values()) if hasattr(g, 'geometry') else [g]
    out = {}
    for name, path in zip(pv.NAMES, views):
        a, b = silhouette(meshes, name, lo, hi), view_mask(path)
        u = (a | b).sum()
        out[name] = {'iou': float((a & b).sum() / u), 'missing': float((b & ~a).sum() / b.sum()), 'extra': float((a & ~b).sum() / max(a.sum(), 1))}
    out['mean_iou'] = float(np.mean([out[n]['iou'] for n in pv.NAMES]))
    return out


def verdict_for(before, after):
    d = after['mean_iou'] - before['mean_iou']
    return 'better' if d > EPS else 'worse' if d < -EPS else 'same'


if __name__ == '__main__':
    r = evaluate(sys.argv[1], sys.argv[2], sys.argv[3:7])
    for n in pv.NAMES:
        print(f"{n:6} iou {r[n]['iou']:.3f} missing {r[n]['missing']:.3f} extra {r[n]['extra']:.3f}")
    print(f"mean_iou {r['mean_iou']:.4f}")
