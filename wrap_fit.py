#!/usr/bin/env python3
"""Stage 3 (first version): fit the template head onto a generated head: wrap_fit.py target.glb template/head.obj out.obj
1. similarity ICP (scale, rotation, shift) from a bbox start, 2. non-rigid ICP (trimesh nricp_amberg).
The eyes are not touched here (rigid move with the head frame is done by the caller)."""
import sys
import numpy as np
import trimesh
from bake import read_mesh, read_v, write_v
from trimesh import registration as reg


def load_target(p):
    m = trimesh.load(p, force='mesh')
    return m


def fit(target, tpl, iters=30):
    # bbox start: same height, centred
    s0 = (target.bounds[1] - target.bounds[0])[1] / (tpl.bounds[1] - tpl.bounds[0])[1]
    T0 = np.eye(4)
    T0[:3, :3] *= s0
    T0[:3, 3] = target.bounds.mean(0) - tpl.bounds.mean(0) * s0
    M, _, cost = reg.icp(tpl.vertices, target, initial=T0, max_iterations=iters, scale=True, reflection=False, translation=True)
    out = tpl.copy()
    out.apply_transform(M)
    return out, M, cost


def free_weights(tpl_base, eyes_path='template/eyes.obj', r_eye=0.55):
    """vertex weights of the template (base units, before the similarity move): 0 = not pulled to the target, only the
    stiffness moves the vertex with its neighbours (eyelids, ears: the target has a pit and a flat leaf there)"""
    ev = read_v(eyes_path)
    c = [ev[ev[:, 0] > 0].mean(0), ev[ev[:, 0] < 0].mean(0)]
    V = tpl_base.vertices
    w = np.ones(len(V))
    for e in c:
        w[np.linalg.norm(V - e, axis=1) < r_eye] = 0
    w[(np.abs(V[:, 0]) > 1.05) & (V[:, 1] > 6.4) & (V[:, 1] < 7.6) & (V[:, 2] < 0.9)] = 0
    return w


def nonrigid(target, tpl, weights=None):
    """steps: [stiffness, landmark weight, normal weight, iterations]; the stiffness falls, the template follows the target"""
    P = reg.nricp_amberg(tpl, target, steps=[[0.01, 10, 0.5, 10], [0.003, 5, 0.1, 10], [0.001, 2, 0.05, 10]],
                         eps=1e-4, gamma=1, distance_threshold=0.05)
    out = tpl.copy()
    out.vertices = P
    if weights is not None:  # the free vertices keep the shape of the template: only a smooth shift of their neighbours
        D = P - tpl.vertices
        free = weights == 0
        nb = [[] for _ in range(len(P))]
        for a, b in tpl.edges_unique:
            nb[a].append(b)
            nb[b].append(a)
        D[free] = 0
        for _ in range(300):
            for i in np.where(free)[0]:
                D[i] = D[nb[i]].mean(0)
        out.vertices = tpl.vertices + D
    return out


def main():
    tgt = load_target(sys.argv[1])
    tpl = read_mesh(sys.argv[2])
    out, M, cost = fit(tgt, tpl)
    print('similarity icp cost', cost, 'scale', np.cbrt(abs(np.linalg.det(M[:3, :3]))))
    sim = out
    out = nonrigid(tgt, sim, free_weights(tpl))
    ev = read_v('template/eyes.obj')
    ne = ev @ M[:3, :3].T + M[:3, 3]
    for sgn in (1, -1):  # each eye follows the mean shift of the eyelid vertices around it
        side = sgn * ev[:, 0] > 0
        near = np.linalg.norm(tpl.vertices - ev[side].mean(0), axis=1) < 0.55
        ne[side] += (out.vertices[near] - sim.vertices[near]).mean(0)
    write_v('template/eyes.obj', sys.argv[3].replace('.obj', '_eyes.obj'), ne)
    d = tgt.nearest.on_surface(out.vertices)[1]
    print('distance to target: mean %.4f max %.4f, >3%% of head: %d vertices' % (d.mean(), d.max(), (d.size and (d > 0.03).sum())))
    write_v(sys.argv[2], sys.argv[3], out.vertices)


if __name__ == '__main__':
    main()
