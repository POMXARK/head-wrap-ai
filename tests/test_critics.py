"""critics: real eye/mesh score files and a replace report convert to the common schema; worst() orders by badness."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import critics as C


def test_real_files():
    e, m = C.load('eye'), C.load('mesh')
    assert e['critic'] == 'eye' and e['score'] == 65.0 and len(e['metrics']) > 10
    assert m['score'] == 75.0 and {x['zone'] for x in m['metrics']} == {'head', 'face', 'neck', 'ear_side'}
    assert all(x['better'] in ('higher', 'lower') for x in e['metrics'] + m['metrics'])


def test_replace_and_worst():
    r = C.validate(C.from_replace({'after': {'ring_gap': 0.28, 'scale': 2.41, 'seam_stretch': 0.431, 'other': 1}}))
    assert r['score'] is None and [x['name'] for x in r['metrics']] == ['ring_gap', 'scale', 'seam_stretch']
    w = C.worst(C.from_mesh({'score': 1, 'zones': {'z': {'shard': 0.5, 'stretch': 0.1, 'seam': 0.01}}}), 1)
    assert w[0]['name'] == 'shard'


def test_schema_rejects():
    try:
        C.validate({'critic': 'x', 'version': 1, 'score': 150, 'metrics': []})
        assert False
    except Exception as ex:
        assert 'maximum' in str(ex) or '150' in str(ex)


if __name__ == '__main__':
    for k, f in list(globals().items()):
        if k.startswith('test_'):
            f(); print('ok', k)
