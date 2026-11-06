"""Registry of edit operations (ours): name -> function(mesh V, F, weights, params) -> new V.
Every op gets per-vertex weights (1 inside the selection, feathered edge, 0 outside) and must return V where the
vertices with weight 0 are unchanged. New ops are added with @op('name')."""
import numpy as np
from scipy import sparse

REG = {}


def op(name):
    def d(f):
        REG[name] = f
        return f
    return d


def laplacian_avg(F, n):
    e = np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
    e = np.unique(np.sort(e, 1), axis=0)
    A = sparse.coo_matrix((np.ones(2 * len(e)), (np.r_[e[:, 0], e[:, 1]], np.r_[e[:, 1], e[:, 0]])), shape=(n, n)).tocsr()
    deg = np.asarray(A.sum(1)).ravel()
    return sparse.diags(1 / np.maximum(deg, 1)) @ A


@op('smooth')
def smooth(V, F, w, p):
    """Laplacian smoothing: params iterations (default 5), lam (0..1, default 0.5)"""
    L = laplacian_avg(F, len(V))
    lam = float(p.get('lam', 0.5))
    out = V.copy()
    for _ in range(int(p.get('iterations', 5))):
        out = out + (lam * w)[:, None] * (L @ out - out)
    return out


@op('displace')
def displace(V, F, w, p):
    """move by params vector [x,y,z] (scaled by the weights): the manual edit of a selected area"""
    return V + w[:, None] * np.asarray(p['vector'], float)[None, :]


def apply(name, V, F, w, params=None):
    if name not in REG:
        raise KeyError('op %s is not implemented (known: %s)' % (name, ', '.join(sorted(REG))))
    out = REG[name](np.asarray(V, float), np.asarray(F, int), np.asarray(w, float), params or {})
    out[w == 0] = V[w == 0]  # the guarantee: nothing outside the area moves
    return out
