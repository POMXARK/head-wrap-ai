"""suggest: on a noisy patch proposes smoothing that lowers roughness; on a smooth patch the best cost is not much better than
doing little; proposals never change the asset; empty area rejected."""
import os, sys
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import suggest as S
import edit_api as E


def grid(n=20, noise=0.0, seed=0):
    ii, jj = np.meshgrid(np.arange(n), np.arange(n))
    V = np.c_[ii.ravel(), jj.ravel(), np.random.RandomState(seed).randn(n * n) * noise].astype(float)
    F = []
    for i in range(n - 1):
        for j in range(n - 1):
            a = i * n + j
            F += [[a, a + 1, a + n], [a + 1, a + n + 1, a + n]]
    return V, np.array(F)


def test_noisy():
    V, F = grid(noise=0.3)
    w = np.ones(len(V))
    r = S.suggest(V, F, w)
    b = r['proposals'][0]
    assert b['after']['roughness'] < 0.6 * r['baseline_roughness'], r
    assert r['proposals'][0]['cost'] <= r['proposals'][-1]['cost']


def test_flat_prefers_gentle():
    V, F = grid(noise=0.0)
    r = S.suggest(V, F, np.ones(len(V)))
    assert r['baseline_roughness'] < 0.5 and r['proposals'][0]['params']['iterations'] <= 2   # edge shrink penalises strong ones


def test_api_no_side_effects():
    E._init()
    v0 = E.A.parts['head'].V.copy()
    n = len(E.A.log)
    E.select({'action': 'clear'})
    try:
        E.suggest_area({'selection': 'draft'})
        assert False
    except ValueError:
        pass
    E.select({'action': 'region', 'name': 'neck'})
    r = E.suggest_area({'selection': 'draft', 'feather': 0.1})
    assert len(r['proposals']) == 3 and np.array_equal(E.A.parts['head'].V, v0) and len(E.A.log) == n
    E.select({'action': 'clear'})


if __name__ == '__main__':
    for k, f in list(globals().items()):
        if k.startswith('test_'):
            f(); print('ok', k)
