"""edit_api: draft selection -> save -> op in area -> undo; outside vertices untouched; empty draft rejected."""
import os, sys
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import edit_api as E


def test_flow():
    E._init()
    v0 = E.A.parts['head'].V.copy()
    E.select({'action': 'clear'})
    r = E.select({'action': 'region', 'name': 'neck'})
    assert r['count'] > 0
    E.select({'action': 'shrink', 'steps': 2})
    sid = E.save_selection({'name': 'шея', 'feather': 0.05})['id']
    E.apply({'op': 'displace', 'selection': sid, 'params': {'vector': [0, 0, 0.1]}})
    moved = np.linalg.norm(E.A.parts['head'].V - v0, axis=1) > 0
    w = E.A.sel[sid][0].weights(0.05)
    assert moved.any() and not moved[w == 0].any()
    assert E.history('undo')['ok'] and np.array_equal(E.A.parts['head'].V, v0)


def test_empty_draft():
    E._init()
    E.select({'action': 'clear'})
    try:
        E.apply({'op': 'smooth', 'selection': 'draft'})
        assert False
    except ValueError:
        pass


if __name__ == '__main__':
    for k, f in list(globals().items()):
        if k.startswith('test_'):
            f(); print('ok', k)
