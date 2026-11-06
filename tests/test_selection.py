"""selection.py: brush works along the surface (not through), grow/shrink/invert, feather weights, json round trip."""
import os, sys, json
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from selection import Mesh, Selection, load_obj

HERE = os.path.join(os.path.dirname(__file__), '..')


def two_sheets():
    """two parallel grids 0.01 apart in z, not connected: a brush on one must not take the other"""
    n = 10
    g = [(x, y) for y in range(n) for x in range(n)]
    V = [(x, y, 0) for x, y in g] + [(x, y, 0.01) for x, y in g]
    F = []
    for off in (0, n * n):
        for y in range(n - 1):
            for x in range(n - 1):
                a = off + y * n + x
                F += [[a, a + 1, a + n], [a + 1, a + n + 1, a + n]]
    return Mesh(V, F)


def test_brush_not_through():
    m = two_sheets()
    s = Selection(m).brush([5, 5, 0], 2.1)
    assert s.mask[:100].sum() > 0 and s.mask[100:].sum() == 0


def test_grow_shrink_invert():
    m = two_sheets()
    s = Selection(m).brush([5, 5, 0], 1.1)
    c = s.count()
    assert s.grow(1).count() > c
    assert s.shrink(1).count() == c
    n = len(m.V)
    assert Selection(m, s.mask).invert().count() == n - c


def test_weights():
    m = two_sheets()
    s = Selection(m).brush([5, 5, 0], 1.1)
    w = s.weights(2.0)
    assert w[s.mask].min() == 1 and 0 <= w.min() and (w[~s.mask] < 1).all()
    assert w[~s.mask].max() > 0 and w[100:].max() == 0
    assert np.all(s.weights(0)[~s.mask] == 0)


def test_json_roundtrip_and_head():
    m = load_obj(os.path.join(HERE, 'template/head_sub.obj'))
    r = json.load(open(os.path.join(HERE, 'template/regions.json')))
    s = Selection.from_region(m, r, 'neck')
    j = s.to_json('sel_neck', 'шея', 'head', 2)
    assert Selection.from_json(m, j).count() == s.count() > 0
    assert 'eyelid' in r['names'] and Selection.from_region(m, r, 'eyelid').count() > 0
    p = m.V[np.where(s.mask)[0][0]]
    b = Selection(m).brush(p, 0.3)
    assert 0 < b.count() < len(m.V) // 2


if __name__ == '__main__':
    for k, f in list(globals().items()):
        if k.startswith('test_'):
            f(); print('ok', k)
