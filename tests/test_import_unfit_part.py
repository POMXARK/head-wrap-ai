"""real game model gm:admiral has no head with a neck hole: parts are marked 'not a head' and import gives a clear error"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import edit_api as e
e._init()
parts = e.donor_parts('gm:admiral')
assert parts and all('ok' in p for p in parts) and not any(p['ok'] for p in parts), parts
try:
    e.replace_prepare({'donor': 'gm:admiral', 'part': 'Hube', 'scale': 'match_ring'})
    raise SystemExit('FAIL: expected error')
except ValueError as x:
    assert 'нет головы' in str(x) and 'max()' not in str(x), x
ok = [p for p in e.donor_parts('hero1') if p['ok']]
assert ok, 'hero1 must have a fitting part'
print('PASS test_import_unfit_part')
