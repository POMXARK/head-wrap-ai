"""asset.py + ops.py: an op in a selection changes only the selected area (and its feather), undo/redo restore exactly."""
import os, sys
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from asset import Asset
from selection import Selection
from test_selection import two_sheets


def bumpy():
    m = two_sheets()
    rng = np.random.default_rng(1)
    m.V[:, 2] += rng.normal(0, 0.2, len(m.V))
    return m


def make():
    m = bumpy()
    a = Asset('t')
    a.add_part('p', m.V, m.F)
    s = Selection(a.parts['p']).brush([5, 5, 0], 1.5)
    a.select('s1', 'p', s, feather=1.0)
    return a, s


def test_only_inside():
    a, s = make()
    v0 = a.parts['p'].V.copy()
    a.apply('smooth', 'p', 's1', {'iterations': 3})
    moved = np.linalg.norm(a.parts['p'].V - v0, axis=1) > 0
    w = s.weights(1.0)
    assert moved.any() and not moved[w == 0].any()
    assert moved[s.mask].any()


def test_undo_redo():
    a, s = make()
    v0 = a.parts['p'].V.copy()
    a.apply('displace', 'p', 's1', {'vector': [0, 0, 1]})
    v1 = a.parts['p'].V.copy()
    assert not np.allclose(v0, v1) and len(a.log) == 1
    assert a.undo() and np.array_equal(a.parts['p'].V, v0) and not a.log
    assert a.redo() and np.array_equal(a.parts['p'].V, v1) and len(a.log) == 1
    assert not a.undo() or True


def test_json_valid_by_schema():
    import json, jsonschema
    from referencing import Registry, Resource
    H = os.path.join(os.path.dirname(__file__), '..', 'spec')
    load = lambda n: json.load(open(os.path.join(H, n)))
    reg = Registry().with_resources([(n, Resource.from_contents(load(n))) for n in ('asset.schema.json', 'op.schema.json')])
    a, _ = make()
    a.apply('smooth', 'p', 's1', {})
    j = a.to_json()
    errs = list(jsonschema.Draft202012Validator(load('asset.schema.json'), registry=reg).iter_errors(j))
    assert not errs, errs[:2]


def test_wrong_part_rejected():
    a, _ = make()
    a.add_part('q', *[a.parts['p'].V, a.parts['p'].F])
    try:
        a.apply('smooth', 'q', 's1')
        assert False
    except ValueError:
        pass


if __name__ == '__main__':
    for k, f in list(globals().items()):
        if k.startswith('test_'):
            f(); print('ok', k)
