"""any model works as a donor head: real game model gm:admiral (no neck hole, 6000 loose pieces), a closed sphere, a plain box"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import numpy as np, trimesh
import edit_api as e
e._init()
r = e.replace_prepare({'donor': 'gm:admiral', 'part': 'Hube', 'scale': 'match_ring'})
assert len(r['hF']) > 100, 'admiral Hube'
for name, m in (('sphere', trimesh.creation.icosphere(3)), ('box', trimesh.creation.box(extents=(1, 1.5, 1)))):
    V, F, u, cut = e.open_neck(np.asarray(m.vertices), np.asarray(m.faces), None)
    assert cut is not None and e.RP.boundary_loops(F), name
print('PASS test_import_any_model')
