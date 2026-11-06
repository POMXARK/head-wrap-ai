#!/usr/bin/env python3
"""Area selection on a triangle mesh (ours): the object behind the "select an area" tool of the panel.

A Selection holds a boolean vertex mask of one mesh. Everything works along the SURFACE (edge graph), so a brush on
the front of the face does not take the back of the head. weights(feather) gives 1 inside and falls to 0 over
`feather` (mesh units) outside - an op multiplies its displacement by it, so the edge leaves no seam.
python3 selection.py mesh.obj --region neck | --brush X,Y,Z,R   -> prints the number of selected vertices"""
import heapq
import json
import os
import sys
import numpy as np
from scipy import sparse
from scipy.sparse.csgraph import dijkstra

HERE = os.path.dirname(os.path.abspath(__file__))


class Mesh:
    def __init__(self, V, F):
        self.V, self.F = np.asarray(V, float), np.asarray(F, int)
        n = len(self.V)
        e = np.concatenate([self.F[:, [0, 1]], self.F[:, [1, 2]], self.F[:, [2, 0]]])
        e = np.unique(np.sort(e, 1), axis=0)
        w = np.linalg.norm(self.V[e[:, 0]] - self.V[e[:, 1]], axis=1)
        A = sparse.coo_matrix((np.r_[w, w], (np.r_[e[:, 0], e[:, 1]], np.r_[e[:, 1], e[:, 0]])), shape=(n, n)).tocsr()
        self.adj = A  # edge-length weighted adjacency
        self.edges = e

    def surface_dist(self, seeds, limit):
        """distance along the surface from the seed vertices (inf beyond limit)"""
        d = dijkstra(self.adj, directed=False, indices=np.asarray(seeds), min_only=True, limit=limit)
        return d


class Selection:
    def __init__(self, mesh, mask=None):
        self.m = mesh
        self.mask = np.zeros(len(mesh.V), bool) if mask is None else np.asarray(mask, bool).copy()

    # --- builders
    @classmethod
    def from_region(cls, mesh, regions, name):
        """regions: dict with 'names' and per-vertex 'vertex' (template/regions.json)"""
        k = regions['names'].index(name)
        return cls(mesh, np.array(regions['vertex']) == k)

    def brush(self, point, radius, add=True):
        """sphere cut by the surface: the nearest vertex is the seed, then surface distance <= radius"""
        p = np.asarray(point, float)
        seed = int(np.argmin(np.linalg.norm(self.m.V - p, axis=1)))
        inside = np.isfinite(self.m.surface_dist([seed], radius))
        self.mask = self.mask | inside if add else self.mask & ~inside
        return self

    def box(self, lo, hi, add=True, visible_from=None):
        """axis box; with visible_from (a direction, e.g. [0,0,1]) only the faces looking at the viewer"""
        inside = np.all((self.m.V >= lo) & (self.m.V <= hi), axis=1)
        if visible_from is not None:
            inside &= self.vertex_normals() @ np.asarray(visible_from, float) > 0
        self.mask = self.mask | inside if add else self.mask & ~inside
        return self

    def vertex_normals(self):
        V, F = self.m.V, self.m.F
        fn = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
        n = np.zeros_like(V)
        for k in range(3):
            np.add.at(n, F[:, k], fn)
        return n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)

    # --- operations
    def grow(self, steps=1):
        for _ in range(steps):
            r = self.m.adj @ self.mask.astype(float)
            self.mask = self.mask | (r > 0)
        return self

    def shrink(self, steps=1):
        for _ in range(steps):
            r = self.m.adj @ (~self.mask).astype(float)
            self.mask = self.mask & ~(r > 0)
        return self

    def invert(self):
        self.mask = ~self.mask
        return self

    def union(self, o):
        self.mask = self.mask | o.mask
        return self

    def subtract(self, o):
        self.mask = self.mask & ~o.mask
        return self

    def clear(self):
        self.mask[:] = False
        return self

    # --- use
    def count(self):
        return int(self.mask.sum())

    def weights(self, feather=0.0):
        """1 in the selection, linear fall to 0 over `feather` surface units outside"""
        w = self.mask.astype(float)
        if feather > 0 and self.mask.any() and not self.mask.all():
            d = self.m.surface_dist(np.where(self.mask)[0], feather)
            ok = np.isfinite(d) & ~self.mask
            w[ok] = 1 - d[ok] / feather
        return w

    def vertices(self):
        return np.where(self.mask)[0].tolist()

    def to_json(self, sid, name, part, feather=0.0, by='user'):
        return {'id': sid, 'name': name, 'part': part, 'mask': {'kind': 'vertices', 'vertices': self.vertices()},
                'feather_mm': feather, 'made_by': by}

    @classmethod
    def from_json(cls, mesh, d):
        m = d['mask']
        s = cls(mesh)
        if m['kind'] == 'vertices':
            s.mask[m['vertices']] = True
        else:
            raise ValueError('mask kind %s needs its own loader' % m['kind'])
        return s


def load_obj(path):
    V, F = [], []
    for l in open(path):
        t = l.split()
        if not t:
            continue
        if t[0] == 'v':
            V.append(list(map(float, t[1:4])))
        elif t[0] == 'f':
            p = [int(x.split('/')[0]) - 1 for x in t[1:]]
            for k in range(1, len(p) - 1):
                F.append([p[0], p[k], p[k + 1]])
    return Mesh(V, F)


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(usage=__doc__)
    ap.add_argument('mesh')
    ap.add_argument('--region')
    ap.add_argument('--brush')
    a = ap.parse_args()
    m = load_obj(a.mesh)
    if a.region:
        s = Selection.from_region(m, json.load(open(os.path.join(HERE, 'template/regions.json'))), a.region)
    else:
        x, y, z, r = map(float, a.brush.split(','))
        s = Selection(m).brush([x, y, z], r)
    print(s.count(), 'of', len(m.V))
