"""edit_api.select action 'set': exact restore of a draft selection (undo/redo of selection steps in /edit)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import edit_api as E

if __name__ == '__main__':
    E.select({'action': 'clear'})
    a = E.select({'action': 'region', 'name': 'nose'})['vertices']
    b = E.select({'action': 'grow', 'steps': 2})['vertices']
    assert len(b) > len(a) > 0
    r = E.select({'action': 'set', 'ids': a})
    assert r['vertices'] == sorted(a) and r['count'] == len(a), 'set restores the previous step'
    assert E.select({'action': 'set', 'ids': []})['count'] == 0
    assert E.select({'action': 'set', 'ids': b})['vertices'] == sorted(b)
    E.select({'action': 'clear'})
    print('test_selection_undo OK')
