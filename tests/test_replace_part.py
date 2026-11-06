"""replace_part: a 'head' tube of another size/pose is put on the open ring of a 'body'; rings meet, scale = ring ratio."""
import os, sys
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import replace_part as RP


def tube(r, h, n=24, m=6, origin=(0, 0, 0)):
    """open tube along y from y=0 to h (rings at both ends are the open boundary)"""
    V = [(r * np.cos(2 * np.pi * i / n), y * h / (m - 1), r * np.sin(2 * np.pi * i / n)) for y in range(m) for i in range(n)]
    F = []
    for y in range(m - 1):
        for i in range(n):
            a, b = y * n + i, y * n + (i + 1) % n
            F += [[a, b, a + n], [b, b + n, a + n]]
    return np.array(V) + origin, np.array(F)


def cap(V, F, ring):
    """close one boundary with a fan: only to leave ONE open ring"""
    c = V[ring].mean(0)
    V = np.vstack([V, c])
    F = np.vstack([F] + [[[ring[i], ring[(i + 1) % len(ring)], len(V) - 1]] for i in range(len(ring))])
    return V, F


def test_loops():
    V, F = tube(1, 2)
    assert len(RP.boundary_loops(F)) == 2 and len(RP.ring_of(V, F)) == 24


def test_replace_scale_and_gap():
    bV, bF = tube(1.0, 5)                       # body 0..5 in y; top ring is the socket (y = 5)
    loops = RP.boundary_loops(bF)
    top = [l for l in loops if bV[l][:, 1].mean() > 2][0]
    bot = [l for l in loops if bV[l][:, 1].mean() < 2][0]
    bV, bF = cap(bV, bF, bot)                   # leave only the top ring open
    # donor: smaller (r=0.5) tube, rotated 90 deg about x, shifted away; its open ring is the one at the end
    hV, hF = tube(0.5, 2)
    hl = RP.boundary_loops(hF)
    hdon = hl[0]
    other = hl[1]
    hV, hF = cap(hV, hF, other)
    R = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]])
    hV = hV @ R.T + np.array([7, -3, 2])
    V, F, rep = RP.replace(bV, bF, RP.ring_of(bV, bF), hV, hF, RP.ring_of(hV, hF), 'match_ring')
    assert abs(rep['scale'] - 2.0) < 1e-6
    assert rep['ring_gap'] < 0.1, rep
    # the donor body must extend away from the body (y > 5), not into it
    donor = V[rep['donor_offset']:]
    assert donor[:, 1].max() > 5 + 3.5 and donor[:, 1].min() > 4.9


def test_keep_scale():
    bV, bF = tube(1.0, 5)
    hV, hF = tube(0.5, 2)
    hV, hF = cap(hV, hF, RP.boundary_loops(hF)[1])
    bl = RP.boundary_loops(bF)
    bV, bF = cap(bV, bF, bl[1])
    V, F, rep = RP.replace(bV, bF, RP.ring_of(bV, bF), hV, hF, RP.ring_of(hV, hF), 'keep')
    assert rep['scale'] == 1.0


if __name__ == '__main__':
    for k, f in list(globals().items()):
        if k.startswith('test_'):
            f(); print('ok', k)
