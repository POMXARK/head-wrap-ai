"""a model opened in /edit as is: no mannequin in the mesh, undo brings the mannequin back"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import edit_api as e
e._init()
n0 = len(e.mesh()['v']) // 3
r = e.replace_head({'donor': 'file:work/ponytail.glb', 'part': 'geometry_0', 'scale': 'open'})
m = e.mesh()
assert m['nhead'] * 3 == len(m['v']), 'body must be hidden'
assert len(e.export_bytes('glb', True)[0]) > 100
e.history('undo')
assert len(e.mesh()['v']) // 3 == n0, 'undo restores the original with the mannequin'
print('PASS test_open_model_as_is')
