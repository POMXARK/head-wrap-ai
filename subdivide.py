#!/usr/bin/env python3
"""Midpoint subdivision of the template with UV kept: subdivide.py template/head.obj template/head_sub.obj
Each triangle -> 4; new vertices and UVs sit on the edges (a seam keeps its two UVs, the vertices are shared)."""
import sys
import numpy as np
from bake import read_uv_faces


def main():
    v = np.array([list(map(float, l.split()[1:4])) for l in open(sys.argv[1]) if l.startswith('v ')])
    vt, F = read_uv_faces(sys.argv[1])
    V, T = list(v), list(vt)
    mv, mt = {}, {}

    def mid(store, arr, a, b):
        k = (min(a, b), max(a, b))
        if k not in store:
            store[k] = len(arr)
            arr.append((arr[a] + arr[b]) / 2)
        return store[k]

    out = []
    for f in F:
        (a, ta), (b, tb), (c, tc) = f
        ab, bc, ca = mid(mv, V, a, b), mid(mv, V, b, c), mid(mv, V, c, a)
        tab, tbc, tca = mid(mt, T, ta, tb), mid(mt, T, tb, tc), mid(mt, T, tc, ta)
        out += [[(a, ta), (ab, tab), (ca, tca)], [(ab, tab), (b, tb), (bc, tbc)],
                [(ca, tca), (bc, tbc), (c, tc)], [(ab, tab), (bc, tbc), (ca, tca)]]
    with open(sys.argv[2], 'w') as o:
        for p in V:
            o.write('v %.5f %.5f %.5f\n' % tuple(p))
        for p in T:
            o.write('vt %.6f %.6f\n' % tuple(p))
        for f in out:
            o.write('f ' + ' '.join(f'{p[0] + 1}/{p[1] + 1}' for p in f) + '\n')
    print(len(V), 'vertices', len(out), 'triangles')


if __name__ == '__main__':
    main()
