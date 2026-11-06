"""Replace a part through a socket (ours, task A4): the donor is aligned to the socket ring of the target, scaled by the
ring radius (match_ring), and the seam quality is measured. Meshes are (V, F) numpy arrays.

ring_of(V, F, k)            k-th open boundary loop (vertex ids in order), longest first
ring_frame(V, ring)         centre, radius, normal (PCA), so an arbitrary ring becomes a socket frame
replace(tV, tF, t_ring, dV, dF, d_ring, scale='match_ring') -> (V, F, report)
  the donor part moves so that its ring lies on t_ring (centre, plane, radius, rotation about the normal picked by the
  best matching of the ring points); the target part is returned unchanged next to it (not welded: the weld 'bridge'
  is the next step); report: ring_gap (max distance between matched ring points, relative to radius), scale."""
import numpy as np
from scipy.spatial import cKDTree


def boundary_loops(F):
    e = np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
    s = np.sort(e, 1)
    u, inv, cnt = np.unique(s, axis=0, return_inverse=True, return_counts=True)
    b = u[cnt == 1]
    nxt = {}
    for a, c in b:
        nxt.setdefault(a, []).append(c)
        nxt.setdefault(c, []).append(a)
    seen, loops = set(), []
    for a in nxt:
        if a in seen:
            continue
        loop, cur, prev = [a], a, None
        seen.add(a)
        while True:
            c = [x for x in nxt[cur] if x != prev and x not in seen]
            if not c:
                break
            prev, cur = cur, c[0]
            seen.add(cur)
            loop.append(cur)
        loops.append(loop)
    return sorted(loops, key=len, reverse=True)


def ring_of(V, F, k=0):
    return boundary_loops(np.asarray(F))[k]


def ring_frame(V, ring):
    P = np.asarray(V)[ring]
    c = P.mean(0)
    u, s, vt = np.linalg.svd(P - c)
    n = vt[2]
    r = np.linalg.norm(P - c, axis=1).mean()
    return c, r, n


def _rot(a, b):
    """rotation taking unit a to unit b"""
    v = np.cross(a, b)
    c = float(a @ b)
    if np.linalg.norm(v) < 1e-9:
        if c > 0:
            return np.eye(3)
        p = np.cross(a, [1, 0, 0] if abs(a[0]) < .9 else [0, 1, 0])
        p /= np.linalg.norm(p)
        return 2 * np.outer(p, p) - np.eye(3)
    K = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + K + K @ K / (1 + c)


def replace(tV, tF, t_ring, dV, dF, d_ring, scale='match_ring', outward=None):
    """outward: direction the donor body should extend (the side away from the target), e.g. up for a head on a body;
    default: opposite to the target part's centroid seen from the ring"""
    tV, dV = np.asarray(tV, float), np.asarray(dV, float)
    tc, tr, tn = ring_frame(tV, t_ring)
    dc, dr, dn = ring_frame(dV, d_ring)
    if outward is None:
        outward = tc - tV.mean(0)
    outward = np.asarray(outward, float)
    if tn @ outward < 0:
        tn = -tn
    if dn @ (dV.mean(0) - dc) > 0:   # the donor normal must point from its body to its ring (i.e. toward the target)
        dn = -dn
    k = {'match_ring': tr / dr, 'keep': 1.0}[scale] if scale != 'uniform_by_height' else tr / dr
    R = _rot(dn, -tn)
    W = (dV - dc) @ R.T * k + tc
    # twist about the normal: best matching of ring points
    A = W[d_ring] - tc
    B = tV[t_ring] - tc
    best, ang = 1e9, 0
    for a in np.linspace(0, 2 * np.pi, 72, endpoint=False):
        c, s = np.cos(a), np.sin(a)
        K = np.array([[0, -tn[2], tn[1]], [tn[2], 0, -tn[0]], [-tn[1], tn[0], 0]])
        Rt = np.eye(3) * c + s * K + (1 - c) * np.outer(tn, tn)
        g = cKDTree(B).query(A @ Rt.T)[0].max()
        if g < best:
            best, ang = g, a
    c, s = np.cos(ang), np.sin(ang)
    K = np.array([[0, -tn[2], tn[1]], [tn[2], 0, -tn[0]], [-tn[1], tn[0], 0]])
    Rt = np.eye(3) * c + s * K + (1 - c) * np.outer(tn, tn)
    W = (W - tc) @ Rt.T + tc
    V = np.vstack([tV, W])
    F = np.vstack([np.asarray(tF), np.asarray(dF) + len(tV)])
    rep = {'scale': float(k), 'ring_gap': float(best / tr), 'donor_offset': len(tV)}
    return V, F, rep


def _angles(P, c, n):
    """angle of each ring point around the axis n (in a basis chosen from n)"""
    a = np.cross(n, [1, 0, 0] if abs(n[0]) < .9 else [0, 1, 0])
    a /= np.linalg.norm(a)
    b = np.cross(n, a)
    return np.arctan2((P - c) @ b, (P - c) @ a)


def bridge(V, ringA, ringB):
    """triangle strip between two rings (vertex ids into V), merged by angle around the common axis.
    Returns faces (list of [i,j,k]) and the longest strip edge divided by the mean ring radius (seam stretch)."""
    A, B = np.asarray(ringA), np.asarray(ringB)
    c = (V[A].mean(0) + V[B].mean(0)) / 2
    n = ring_frame(V, A)[2]
    ang_a, ang_b = _angles(V[A], c, n), _angles(V[B], c, n)
    A, ang_a = A[np.argsort(ang_a)], np.sort(ang_a)
    B, ang_b = B[np.argsort(ang_b)], np.sort(ang_b)
    # start both at the closest angles, then walk around once
    i0 = 0
    j0 = int(np.argmin(np.abs(np.angle(np.exp(1j * (ang_b - ang_a[0]))))))
    na, nb = len(A), len(B)
    i = j = 0
    F = []
    while i < na or j < nb:
        ai, bj = A[(i0 + i) % na], B[(j0 + j) % nb]
        if i >= na:
            adv_b = True
        elif j >= nb:
            adv_b = False
        else:   # advance the side whose next point is angularly closer
            an = A[(i0 + i + 1) % na]
            bn = B[(j0 + j + 1) % nb]
            da = abs(np.angle(np.exp(1j * (ang_a[(i0 + i + 1) % na] - ang_b[(j0 + j) % nb]))))
            db = abs(np.angle(np.exp(1j * (ang_b[(j0 + j + 1) % nb] - ang_a[(i0 + i) % na]))))
            adv_b = db < da
        if adv_b:
            F.append([ai, bj, B[(j0 + j + 1) % nb]])
            j += 1
        else:
            F.append([ai, bj, A[(i0 + i + 1) % na]])
            i += 1
    F = np.array(F)
    e = np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
    longest = np.linalg.norm(V[e[:, 0]] - V[e[:, 1]], axis=1).max()
    return F, float(longest / ring_frame(V, A)[1])
