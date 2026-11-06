"""edit_api level: symmetric brush, sculpt ops through apply (journal + undo), texture/UV handlers"""
import os
import sys
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import edit_api as E
import texture

E._init()
h = E.A.parts['head']
top = int(np.argmax(h.V[:, 2]))
p = [float(x) for x in h.V[top]]
p[0] = 0.8   # off the symmetry plane

# symmetric brush covers both sides, a plain one only one
E.select({'action': 'clear'})
a = E.select({'action': 'brush', 'point': p, 'radius': 0.4})['count']
E.select({'action': 'clear'})
b = E.select({'action': 'brush', 'point': p, 'radius': 0.4, 'sym': True})
V = h.V
vs = np.array(b['vertices'])
assert b['count'] > 1.6 * a and (V[vs, 0] > 0).any() and (V[vs, 0] < 0).any()
print('symmetry ok', a, b['count'])

# every sculpt op goes through apply(): journal, only the area moves, undo restores
V0 = h.V.copy()
for op, par in [('inflate', {'amount': 0.05}), ('flatten', {'strength': 0.5}), ('pinch', {'strength': 0.3}), ('scale', {'factor': [1.3, 1, 1]})]:
    r = E.apply({'op': op, 'selection': 'draft', 'params': par, 'feather': 0.1})
    assert r['rec']['op'] == op
    moved = np.linalg.norm(E.A.parts['head'].V - V0, axis=1) > 0
    assert moved.any()
    E.history('undo')
    assert np.array_equal(E.A.parts['head'].V, V0), op
assert not E.A.log
print('sculpt via api ok')

# texture / UV handlers
assert E.tex_info()['available']
r = E.tex_paint({'points': [[0.4, 0.4]], 'radius': 0.02, 'color': [10, 20, 30], 'strength': 1})
assert r['can_undo']
u = E.uv_xform({'op': 'move', 'du': 0.01, 'dv': 0})
assert u['moved'] > 0
assert E.tex_history({'action': 'undo'})['kind'] == 'uv'
assert E.tex_history({'action': 'undo'})['kind'] == 'tex'
assert not E.tex_history({'action': 'undo'})['ok']
E.select({'action': 'clear'})
try:
    E.uv_xform({'op': 'move'})
    raise SystemExit('UV edit needs a selection')
except ValueError:
    pass
assert len(E.uv_layout()['vt']) > 1000 and len(E.mesh_uv()['uv']) == 6 * len(h.F)
print('PASS test_edit_tools_api')
