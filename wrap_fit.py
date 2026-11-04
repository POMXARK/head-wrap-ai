#!/usr/bin/env python3
"""Stage 3 (first version): fit the template head onto a generated head: wrap_fit.py target.glb template/head.obj out.obj
1. similarity ICP (scale, rotation, shift) from a bbox start, 2. non-rigid ICP (trimesh nricp_amberg).
The eyes are not touched here (rigid move with the head frame is done by the caller)."""
import sys
import numpy as np
import trimesh
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


def nonrigid(target, tpl):
    """steps: [stiffness, landmark weight, normal weight, iterations]; the stiffness falls, the template follows the target"""
    P = reg.nricp_amberg(tpl, target, steps=[[0.01, 10, 0.5, 10], [0.003, 5, 0.1, 10], [0.001, 2, 0.05, 10]],
                         eps=1e-4, gamma=1, distance_threshold=0.05)
    out = tpl.copy()
    out.vertices = P
    return out


def main():
    tgt = load_target(sys.argv[1])
    tpl = trimesh.load(sys.argv[2], process=False)
    out, M, cost = fit(tgt, tpl)
    print('similarity icp cost', cost, 'scale', np.cbrt(abs(np.linalg.det(M[:3, :3]))))
    out = nonrigid(tgt, out)
    d = tgt.nearest.on_surface(out.vertices)[1]
    print('distance to target: mean %.4f max %.4f, >3%% of head: %d vertices' % (d.mean(), d.max(), (d.size and (d > 0.03).sum())))
    out.export(sys.argv[3])


if __name__ == '__main__':
    main()
