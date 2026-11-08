"""a whole model opened from a file keeps its parts, one-sided drawing and file normals after an edit (edits only move vertices);
the moved vertices get their normals recomputed by the editor (vn_moved), undo brings the untouched state back"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import numpy as np
import edit_api as e
e._init()
e.replace_head({'donor': 'file:work/hero1_eye.glb', 'part': '__all__', 'scale': 'open'})
m = e.mesh()
assert m.get('cull') and len(m.get('parts', [])) > 1 and 'vn_moved' not in m, 'opened: parts, cull, file normals'
assert len(m['vn']) == m['nhead'] * 3
p = max(m['parts'], key=lambda p: p[2] - p[1])          # the biggest part
assert len(p) >= 4 and p[3], 'part has a readable title'
e.select({'action': 'ids', 'ids': list(range(p[1], p[2])), 'mode': 'add'})
e.apply({'op': 'smooth', 'selection': 'draft', 'params': {'iterations': 3}})
m2 = e.mesh()
assert m2.get('cull') and m2.get('parts') == m['parts'], 'parts and cull survive an edit'
mv = np.asarray(m2.get('vn_moved', []))
assert len(mv) and mv.min() >= 0 and mv.max() < m2['nhead'], 'moved vertices are listed for normal recomputation'
e.history('undo')
m3 = e.mesh()
assert m3.get('parts') == m['parts'] and 'vn_moved' not in m3, 'undo: untouched again'
e.replace_head({'donor': 'template', 'part': 'head', 'scale': 'match_ring'})
assert 'parts' not in e.mesh() and e.file_model_state() is None, 'another head: no file parts'
print('PASS test_parts_after_edit')
e.history('undo')
assert e.mesh().get('parts') == m['parts'], 'undo of the other head: the file parts are back'
print('PASS undo back to the file model')
e.select({'action': 'ids', 'ids': list(range(p[1], p[2])), 'mode': 'add'})
e.apply({'op': 'smooth', 'selection': 'draft', 'params': {'iterations': 3}})
b = e.before()
assert b.get('parts') == m['parts'] and b.get('cull') and 'vn_moved' not in b, '«до» keeps the parts (hidden parts stay hidden)'
print('PASS before keeps parts')
