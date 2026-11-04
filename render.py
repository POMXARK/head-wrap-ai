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
from bake import read_uv_faces, read_v


def draw(W, tri, col, out, E=None, crop=None, yaws=(0, 40, 90)):
    fig, ax = plt.subplots(1, len(yaws), figsize=(5 * len(yaws), 6))
    ax = np.atleast_1d(ax)
    for a, yaw in zip(ax, yaws):
        r = np.radians(yaw)
        R = np.array([[np.cos(r), 0, np.sin(r)], [0, 1, 0], [-np.sin(r), 0, np.cos(r)]])
        V = W @ R.T
        if E is not None:  # eyeballs: white, painted before the head only where the head does not cover them
            VE = E[0] @ R.T
            ne = np.cross(VE[E[1][:, 1]] - VE[E[1][:, 0]], VE[E[1][:, 2]] - VE[E[1][:, 0]])
            a.add_collection(PolyCollection([VE[f][:, :2] for f, k in zip(E[1], ne[:, 2]) if k > 0], facecolors='#e8e2d8', edgecolors='none', zorder=0))
        n = np.cross(V[tri[:, 1]] - V[tri[:, 0]], V[tri[:, 2]] - V[tri[:, 0]])
        vis = n[:, 2] > 0
        z = V[tri].mean(1)[:, 2]
        order = [i for i in np.argsort(z) if vis[i]]
        nn = n / (np.linalg.norm(n, axis=1, keepdims=True) + 1e-12)
        shade = 0.45 + 0.55 * np.clip(nn @ np.array([-0.35, 0.5, 0.8]), 0, 1)  # one light from the upper left front: relief is visible
        a.add_collection(PolyCollection([V[tri[i]][:, :2] for i in order], facecolors=(col * shade[:, None])[order], edgecolors='none'))
        a.set_xlim(*(crop[0] if crop else (V[:, 0].min(), V[:, 0].max()))); a.set_ylim(*(crop[1] if crop else (V[:, 1].min(), V[:, 1].max()))); a.set_aspect('equal'); a.axis('off')
    plt.tight_layout(); plt.savefig(out, dpi=70)
    plt.close()


def main():
    import os
    W = read_v(sys.argv[1])
    vt, F = read_uv_faces(sys.argv[2])
    tex = np.asarray(Image.open(sys.argv[3]).convert('RGB'))
    S = tex.shape[0]
    tri = np.array([[p[0] for p in f] for f in F])
    uv = np.array([vt[[p[1] for p in f]].mean(0) for f in F])
    col = tex[np.clip(((1 - uv[:, 1]) * S).astype(int), 0, S - 1), np.clip((uv[:, 0] * S).astype(int), 0, S - 1)] / 255.
    ep = sys.argv[1].replace('.obj', '_eyes.obj')
    E = None
    if os.path.exists(ep):
        from bake import read_mesh
        em = read_mesh(ep)
        E = (em.vertices, em.faces)
    draw(W, tri, col, sys.argv[4], E)


def render_glb(path, out):
    """the same preview of a textured glb (the generated head)"""
    m = trimesh.load(path, force='mesh')
    tex = np.asarray(m.visual.material.baseColorTexture.convert('RGB'))
    H, Wd = tex.shape[:2]
    uv = m.visual.uv[m.faces].mean(1)
    col = tex[np.clip(((1 - uv[:, 1]) % 1 * H).astype(int), 0, H - 1), np.clip((uv[:, 0] % 1 * Wd).astype(int), 0, Wd - 1)] / 255.
    draw(np.asarray(m.vertices), m.faces, col, out)


if __name__ == '__main__':
    main()
