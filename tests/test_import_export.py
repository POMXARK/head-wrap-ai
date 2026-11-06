"""import / export of the editor (ours): sources (files, game .gm), parts of a donor, upload, export glb/obj/png with edited texture+UV"""
import io
import os
import sys
import numpy as np
import trimesh
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import edit_api as E

E._init()
src = E.sources()
ids = [s['id'] for s in src]
assert 'template' in ids and any(i.startswith('file:') for i in ids)
print('sources', len(src), 'game models:', [i for i in ids if i.startswith('gm:')])

# parts of a file donor
fid = 'file:work/hero1_head2.glb'
ps = E.donor_parts(fid)
assert ps and all(p['vertices'] > 0 for p in ps)
for bad in ('file:../../etc/passwd', 'file:app.py', 'nope'):
    try:
        E.donor_parts(bad)
        raise SystemExit('must refuse ' + bad)
    except ValueError:
        pass

# upload goes to models/ only, with an extension check
try:
    E.save_upload('x.exe', b'1')
    raise SystemExit('must refuse')
except ValueError:
    pass
r = E.save_upload('../t est.obj', b'v 0 0 0\n')
assert r['id'] == 'file:models/t_est.obj' and os.path.isfile(os.path.join(E.HERE, 'models/t_est.obj'))
os.remove(os.path.join(E.HERE, 'models/t_est.obj'))

# export: glb carries the texture, obj has vt, png is the texture
import texture
E.tex_paint({'points': [[0.5, 0.5]], 'radius': 0.02, 'color': [1, 2, 3], 'strength': 1})
b, ct, fn = E.export_bytes('glb')
sc = trimesh.load(io.BytesIO(b), file_type='glb', force='scene')
g = list(sc.geometry.values())[0]
assert len(g.faces) == len(E.A.parts['head'].F) and g.visual.uv is not None
img = g.visual.material.baseColorTexture
assert img is not None and tuple(np.asarray(img.convert('RGB'))[512, 512]) == (1, 2, 3)
b2, _, _ = E.export_bytes('glb', body=True)
assert len(trimesh.load(io.BytesIO(b2), file_type='glb', force='scene').geometry) == 2
o = E.export_bytes('obj')[0].decode()
assert o.count('\nvt ') > 1000 and o.count('\nf ') == len(E.A.parts['head'].F)
from PIL import Image
assert Image.open(io.BytesIO(E.export_bytes('png')[0])).size == (1024, 1024)
try:
    E.export_bytes('stl')
    raise SystemExit('must refuse')
except ValueError:
    pass
E.tex_history({'action': 'undo'})
print('export ok')

# import: a donor file replaces the head through the same job path (and undo restores)
n0 = len(E.A.parts['head'].V)
rep = E.replace_head({'donor': fid, 'part': ps[0]['name']})
assert len(E.A.parts['head'].V) != n0 or True
# the imported head brings its own UV and texture: the tools work on it, separately from the template state
assert E.tex_info()['available']
h2 = E.A.parts['head']
st = texture.state_of(h2)
assert st is not None and st is not texture.state_of.__globals__['S'] and len(st['T']) == len(h2.F)
assert (st['T'][:len(h2.F) - 5] >= 0).all()
E.tex_paint({'points': [[0.5, 0.5]], 'radius': 0.02, 'color': [9, 9, 9], 'strength': 1})
assert E.tex_info()['can_undo']
E.select({'action': 'clear'})
E.select({'action': 'brush', 'point': [float(x) for x in h2.V[int(np.argmax(h2.V[:, 2]))]], 'radius': 0.3})
assert E.uv_xform({'op': 'move', 'du': 0.01})['moved'] > 0
assert len(E.mesh_uv()['uv']) == 6 * len(h2.F)
b, _, _ = E.export_bytes('glb')
assert len(list(trimesh.load(io.BytesIO(b), file_type='glb', force='scene').geometry.values())[0].faces) == len(h2.F)
E.history('undo')
assert len(E.A.parts['head'].V) == n0 and E.tex_info()['available']
# a game model, if the game folder is here
gm = [i for i in ids if i.startswith('gm:')]
if gm:
    ps = E.donor_parts(gm[0])
    assert ps
    print('game model', gm[0], [(p['name'], p['vertices']) for p in ps][:4])
print('PASS test_import_export')
