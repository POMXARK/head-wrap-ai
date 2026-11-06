"""before(): shows the state before the last op; equals the pre-op vertices; nothing after undo of everything."""
import os, sys
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import edit_api as E


def test_before_after():
    E._init()
    while E.A._undo:
        E.history('undo')
    assert E.before() == {'none': True}
    v0 = E.A.parts['head'].V.copy()
    E.select({'action': 'clear'})
    E.select({'action': 'region', 'name': 'neck'})
    E.apply({'op': 'displace', 'selection': 'draft', 'params': {'vector': [0, 0, 0.1]}})
    b = E.before()
    nh = b['nhead']
    assert nh == len(v0) and b['op'] == 'displace'
    assert np.allclose(np.array(b['v'][:nh * 3]).reshape(-1, 3), v0, atol=1e-4)      # before == original
    assert not np.allclose(E.A.parts['head'].V, v0) and abs(b['max_move'] - 0.1) < 1e-3
    E.history('undo')
    assert E.before() == {'none': True}


def test_before_after_replace():
    E._init()
    n = len(E.A.parts['head'].V)
    E.replace_head({'donor': 'hero1'})
    b = E.before()
    assert b['op'] == 'replace_part' and b['nhead'] == n and b['max_move'] is None
    E.history('undo')


if __name__ == '__main__':
    for k, f in list(globals().items()):
        if k.startswith('test_'):
            f(); print('ok', k)
