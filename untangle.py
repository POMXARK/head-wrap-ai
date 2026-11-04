#!/usr/bin/env python3
"""Self-intersections of the wrapped head are smoothed away (ours).

untangle.py in.obj out.obj [rounds]
Faces that cut other faces (pymeshlab) and their rings are Laplacian-smoothed; repeated until none are left
or the count stops falling. Only vertex positions change, so the UV and the topology stay."""
import sys
import numpy as np
import trimesh
import pymeshlab as pm


def bad_faces(V, F):
    ms = pm.MeshSet()
    ms.add_mesh(pm.Mesh(V, F))
    ms.compute_selection_by_self_intersections_per_face()
    return ms.current_mesh().face_selection_array()


def main():
    src, dst = sys.argv[1], sys.argv[2]
    rounds = int(sys.argv[3]) if len(sys.argv) > 3 else 30
    m = trimesh.load(src, process=False, maintain_order=True)
    V, F = np.asarray(m.vertices, float), np.asarray(m.faces)
    nb = [set() for _ in V]
    for a, b, c in F:
        nb[a] |= {b, c}; nb[b] |= {a, c}; nb[c] |= {a, b}
    best = None
    for r in range(rounds):
        sel = bad_faces(V, F)
        n = int(sel.sum())
        print(r, 'intersecting faces', n, flush=True)
        if best is None or n < best[0]:
            best = (n, V.copy())
        if n == 0:
            break
        ring = set(F[sel].ravel())
        for _ in range(2):
            ring |= {j for i in list(ring) for j in nb[i]}
        idx = np.array(sorted(ring))
        W = V.copy()
        for i in idx:
            W[i] = 0.5 * V[i] + 0.5 * V[list(nb[i])].mean(0)
        V = W
    V = best[1]
    out = trimesh.Trimesh(V, F, process=False)
    # vertices only: write over the v lines of the source
    lines, k = [], 0
    for ln in open(src):
        if ln.startswith('v '):
            lines.append('v %.6f %.6f %.6f\n' % tuple(V[k])); k += 1
        else:
            lines.append(ln)
    open(dst, 'w').writelines(lines)
    print('best', best[0], '->', dst)


if __name__ == '__main__':
    main()
