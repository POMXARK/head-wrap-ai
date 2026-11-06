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


def vertex_normals(V, F):
    fn = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
    n = np.zeros_like(V)
    for k in range(3):
        np.add.at(n, F[:, k], fn)
    return n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)


def _center(V, w):
    return (V * w[:, None]).sum(0) / max(w.sum(), 1e-12)


@op('inflate')
def inflate(V, F, w, p):
    """push the area out (amount > 0) or in (< 0) along the surface normals, like the Inflate brush; amount in mesh units"""
    return V + (w * float(p.get('amount', 0.05)))[:, None] * vertex_normals(V, F)


@op('flatten')
def flatten(V, F, w, p):
    """pull the area to its mean plane (strength 0..1), like the Flatten brush"""
    n = vertex_normals(V, F)
    c = _center(V, w)
    nm = (n * w[:, None]).sum(0)
    nm /= max(np.linalg.norm(nm), 1e-12)
    d = (V - c) @ nm
    return V - (w * float(p.get('strength', 0.5)) * d)[:, None] * nm[None, :]


@op('pinch')
def pinch(V, F, w, p):
    """squeeze the area towards its centre along the surface (strength 0..1), like the Pinch brush"""
    n = vertex_normals(V, F)
    d = _center(V, w) - V
    d -= (d * n).sum(1, keepdims=True) * n
    return V + (w * float(p.get('strength', 0.3)))[:, None] * d


@op('scale')
def scale(V, F, w, p):
    """stretch/shrink the area about its centre: params factor [sx,sy,sz] (or one number); the weights blend it in"""
    f = np.broadcast_to(np.asarray(p.get('factor', 1.2), float), (3,))
    c = _center(V, w)
    return c + (V - c) * (1 + w[:, None] * (f[None, :] - 1))


def apply(name, V, F, w, params=None):
    if name not in REG:
        raise KeyError('op %s is not implemented (known: %s)' % (name, ', '.join(sorted(REG))))
    out = REG[name](np.asarray(V, float), np.asarray(F, int), np.asarray(w, float), params or {})
    out[w == 0] = V[w == 0]  # the guarantee: nothing outside the area moves
    return out
