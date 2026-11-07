"""preview of a donor part before import: API returns a thinned mesh, the dialog has the canvas and uses it"""
import sys, os
D = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, D)
import edit_api as e
e._init()
r = e.part_mesh('file:work/hero1_head2.glb', 'geometry_0')
assert 0 < r['faces'] and len(r['v']) % 3 == 0 and (r['tex'] or max(r['f']) < len(r['v']) // 3)
h = open(os.path.join(D, 'edit.html'), encoding='utf-8').read()
for k in ('id="ppv"', 'function previewPart', '/api/edit/part_mesh'):
    assert k in h, k
print('PASS test_part_preview')
