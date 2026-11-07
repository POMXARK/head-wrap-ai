"""preview with texture (part, whole model, current export) and Blender-like shading (solid/texture/wire) independent of the view mode"""
import sys, os
D = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, D)
import edit_api as e
e._init()
for src, part in (('file:work/hero1_head2.glb', 'geometry_0'), ('file:work/hero1_eye.glb', '__all__'), (e.CUR, 'head'), (e.CUR, 'body')):
    r = e.part_mesh(src, part)
    assert r['tex'] and len(r['uv']) * 3 == len(r['v']) * 2 and 'f' not in r and r['faces'] > 0, (src, part)
    assert len(r['n']) == len(r['v']), 'smooth normals per corner'
    assert 0 <= min(r['uv']) and max(r['uv']) <= 1.0001, 'uv in 0..1'
    png = e.part_texture_png(src, part)
    assert png and png[:4] == b'\x89PNG', (src, part)
r = e.part_mesh('file:work/nricp.obj', '')
assert not r['tex'] and 'f' in r and e.part_texture_png('file:work/nricp.obj', '') is None, 'obj has no texture'
h = open(os.path.join(D, 'edit.html'), encoding='utf-8').read()
for k in ('id="msh-solid"', 'id="msh-tex"', 'id="msh-wire"', 'id="mov"', 'function setShade', 'id="psh-tex"', 'id="pov"', 'id="psm"', 'id="msm"', 'function pvShade',
          '/api/edit/part_texture'):
    assert k in h, k
print('PASS test_viewport_shading')
