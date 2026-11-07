"""a whole file (all parts) can be a donor: pseudo-part '__all__' is listed first, merges every part, imports as is"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import edit_api as e
e._init()
parts = e.donor_parts('file:work/hero1_eye.glb')
assert parts[0]['name'] == '__all__' and parts[0]['ok'] and len(parts) > 2, parts
n_all = e.part_mesh('file:work/hero1_eye.glb', '__all__')['faces']
n_parts = sum(e.part_mesh('file:work/hero1_eye.glb', p['name'])['faces'] for p in parts[1:])
assert abs(n_all - n_parts) < 0.05 * n_parts, (n_all, n_parts)
e.replace_head({'donor': 'file:work/hero1_eye.glb', 'part': '__all__', 'scale': 'open'})
assert e.mesh()['nhead'] * 3 == len(e.mesh()['v'])
print('PASS test_import_whole_model')
