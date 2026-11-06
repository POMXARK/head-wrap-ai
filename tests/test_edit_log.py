"""edit_log: apply -> logged with area+metrics; undo -> verdict undone; redo -> accepted; SFT/pref export; user and agent."""
import os, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import edit_log as L
L.PATH = os.path.join(tempfile.mkdtemp(), 'edits.jsonl')      # tests never touch the user's journal
import edit_api as E


def brush():
    E.select({'action': 'clear'})
    E.select({'action': 'brush', 'point': list(E.A.parts['head'].V[100]), 'radius': 0.8})


def test_log_flow():
    E._init()
    while E.A._undo:
        E.history('undo')
    open(L.PATH, 'w').close()
    del E._IDS[:]
    del E._REDO_IDS[:]
    brush()
    E.apply({'op': 'smooth', 'selection': 'draft', 'params': {'iterations': 3}, 'feather': 0.1})
    es = L.load()
    assert len(es) == 1 and es[0]['by'] == 'user' and es[0]['op'] == 'smooth' and es[0]['verdict'] == 'accepted'
    assert es[0]['area']['count'] > 0 and es[0]['area']['regions'] and 'roughness' in es[0]['metrics']['before']
    assert es[0]['metrics']['after']['roughness'] < es[0]['metrics']['before']['roughness']
    E.history('undo')
    assert L.load()[0]['verdict'] == 'undone' and L.export_sft() == []
    E.history('redo')
    assert L.load()[0]['verdict'] == 'accepted' and len(L.export_sft()) == 1
    s = L.export_sft()[0]
    assert 'Область:' in s['prompt'] and '"op": "smooth"' in s['completion']


def test_preference_pair_and_agent():
    E._init()
    brush()
    E.apply({'op': 'smooth', 'selection': 'draft', 'params': {'iterations': 30}, 'feather': 0.1})
    E.history('undo')                      # too strong: undone
    E.apply({'op': 'smooth', 'selection': 'draft', 'params': {'iterations': 2, 'lam': 0.3}, 'feather': 0.1, 'by': 'agent'})
    p = L.export_pref()
    assert len(p) == 1 and p[0]['rejected']['iterations'] == 30 and p[0]['chosen']['iterations'] == 2
    assert L.load()[-1]['by'] == 'agent'
    E.history('undo')
    E.history('undo') if E.A._undo else None


def test_replace_logged():
    E._init()
    n = len(L.load())
    E.replace_head({'donor': 'template'})
    assert L.load()[-1]['op'] == 'replace_part' and len(L.load()) == n + 1
    E.history('undo')
    assert L.load()[-1]['verdict'] == 'undone'


if __name__ == '__main__':
    for k, f in list(globals().items()):
        if k.startswith('test_'):
            f(); print('ok', k)
