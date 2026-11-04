#!/usr/bin/env python3
"""Smooth a fold of the fitted head (ours): smooth_strip.py in.obj out.obj x0 x1 y0 y1 z0 z1 [iters] [lam]
Vertices (welded by position) inside the box get `iters` umbrella-Laplacian steps (neighbours outside stay put); the
obj keeps its vertex order, uv and faces, only the positions of the 'v' lines change."""
import sys
import numpy as np

src, dst = sys.argv[1:3]
x0, x1, y0, y1, z0, z1 = (float(v) for v in sys.argv[3:9])
it = int(sys.argv[9]) if len(sys.argv) > 9 else 10
lam = float(sys.argv[10]) if len(sys.argv) > 10 else 0.5
lines = open(src).read().split('\n')
vi = [i for i, l in enumerate(lines) if l.startswith('v ')]
P = np.array([[float(x) for x in lines[i].split()[1:4]] for i in vi])
key = {}
w = np.array([key.setdefault(tuple(np.round(p, 5)), len(key)) for p in P])
n = len(key)
Q = np.zeros((n, 3))
Q[w] = P
nb = [set() for _ in range(n)]
for l in lines:
    if l.startswith('f '):
        ids = [w[int(t.split('/')[0]) - 1] for t in l.split()[1:]]
        for a in range(len(ids)):
            nb[ids[a]].add(ids[(a + 1) % len(ids)])
            nb[ids[(a + 1) % len(ids)]].add(ids[a])
inb = (Q[:, 0] >= x0) & (Q[:, 0] <= x1) & (Q[:, 1] >= y0) & (Q[:, 1] <= y1) & (Q[:, 2] >= z0) & (Q[:, 2] <= z1)
print('vertices moved', int(inb.sum()))
for _ in range(it):
    R = Q.copy()
    for i in np.where(inb)[0]:
        if nb[i]:
            R[i] = Q[i] + lam * (Q[list(nb[i])].mean(0) - Q[i])
    Q = R
for k, i in enumerate(vi):
    q = Q[w[k]]
    lines[i] = 'v %.6f %.6f %.6f' % tuple(q) + (' ' + ' '.join(lines[i].split()[4:]) if len(lines[i].split()) > 4 else '')
open(dst, 'w').write('\n'.join(lines))
