#!/usr/bin/env python3
"""Flat-shaded textured preview (matplotlib, no GPU): render.py wrapped.obj template/head.obj atlas.png out.png
Views: front, 3/4, side. Each face takes the atlas colour at its UV centroid (painter's algorithm)."""
import sys
import numpy as np
import trimesh
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from PIL import Image
from bake import read_uv_faces


def main():
    W = trimesh.load(sys.argv[1], process=False).vertices
    vt, F = read_uv_faces(sys.argv[2])
    tex = np.asarray(Image.open(sys.argv[3]).convert('RGB'))
    S = tex.shape[0]
    tri = np.array([[p[0] for p in f] for f in F])
    uv = np.array([vt[[p[1] for p in f]].mean(0) for f in F])
    col = tex[np.clip(((1 - uv[:, 1]) * S).astype(int), 0, S - 1), np.clip((uv[:, 0] * S).astype(int), 0, S - 1)] / 255.
    fig, ax = plt.subplots(1, 3, figsize=(15, 6))
    for a, yaw in zip(ax, (0, 40, 90)):
        r = np.radians(yaw)
        R = np.array([[np.cos(r), 0, np.sin(r)], [0, 1, 0], [-np.sin(r), 0, np.cos(r)]])
        V = W @ R.T
        n = np.cross(V[tri[:, 1]] - V[tri[:, 0]], V[tri[:, 2]] - V[tri[:, 0]])
        vis = n[:, 2] > 0
        z = V[tri].mean(1)[:, 2]
        order = [i for i in np.argsort(z) if vis[i]]
        shade = 0.55 + 0.45 * np.abs(n[:, 2]) / (np.linalg.norm(n, axis=1) + 1e-12)
        a.add_collection(PolyCollection([V[tri[i]][:, :2] for i in order], facecolors=(col * shade[:, None])[order], edgecolors='none'))
        a.set_xlim(V[:, 0].min(), V[:, 0].max()); a.set_ylim(V[:, 1].min(), V[:, 1].max()); a.set_aspect('equal'); a.axis('off')
    plt.tight_layout(); plt.savefig(sys.argv[4], dpi=70)


if __name__ == '__main__':
    main()
