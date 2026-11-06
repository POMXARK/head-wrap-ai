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


def test_replace_head_and_undo():
    import json, jsonschema
    from referencing import Registry, Resource
    E._init()
    n0 = len(E.A.parts['head'].V)
    n_log = len(E.A.log)
    v_before = E.A.parts['head'].V.copy()
    E.select({'action': 'region', 'name': 'neck'})
    r = E.replace_head({'donor': 'hero1'})['report']
    assert E.DRAFT.count() == 0   # ids of the old head mean nothing on the new one
    assert r['seam_stretch'] < 1.5, r   # the strip closes the 28% ring gap without long triangles
    assert r['ring_gap'] < 0.35 and r['scale'] > 1       # hero1 head is ~1 high, the template ~8 -> scaled up
    body, head = E.A.parts['body'], E.A.parts['head']
    assert head.V[:, 1].min() > body.V[:, 1].max() - 1.0   # head sits on top of the body ring
    assert E.A.log[-1]['op'] == 'replace_part'
    H = os.path.join(os.path.dirname(__file__), '..', 'spec')
    load = lambda n: json.load(open(os.path.join(H, n)))
    reg = Registry().with_resources([(n, Resource.from_contents(load(n))) for n in ('asset.schema.json', 'op.schema.json')])
    assert not list(jsonschema.Draft202012Validator(load('op.schema.json'), registry=reg).iter_errors(
        {k: v for k, v in E.A.log[-1].items() if k != 'ts'}))
    E.select({'action': 'brush', 'point': list(E.A.parts['head'].V[0]), 'radius': 0.5})
    try:
        E.select({'action': 'region', 'name': 'neck'})
        assert False
    except ValueError:
        pass
    assert E.DRAFT.count() > 0
    assert E.history('undo')['ok'] and len(E.A.parts['head'].V) == n0 and len(E.A.log) == n_log
    assert E.DRAFT.count() == 0   # regression found in the visible test: stale ids lit up random vertices
    assert E.history('redo')['ok'] and not np.array_equal(E.A.parts['head'].V, v_before)
    E.history('undo')


if __name__ == '__main__':
    for k, f in list(globals().items()):
        if k.startswith('test_'):
            f(); print('ok', k)
