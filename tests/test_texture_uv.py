"""texture paint + UV edit + history (ours): works on a copy of the state, the originals in template/ and work/ stay as they were"""
import hashlib
import os
import sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
import edit_api
import texture

md5 = lambda p: hashlib.md5(open(os.path.join(HERE, '..', p), 'rb').read()).hexdigest()
before = (md5('work/baked.png'), md5('template/head_sub.obj'))
edit_api._init()
head = edit_api.A.parts['head']
S = texture._init()
assert texture.available(head)
t0 = S['tex'].copy()

# paint: changes only pixels in the disc, to the colour
r = texture.paint({'points': [[0.5, 0.5]], 'radius': 0.02, 'strength': 1.0, 'color': [255, 0, 0]}, head)
cx = int(0.5 * 1024)
assert tuple(S['tex'][512, cx]) == (255, 0, 0)
diff = np.any(S['tex'] != t0, axis=2)
ys, xs = np.nonzero(diff)
assert diff.sum() > 100 and np.hypot(xs - 512, ys - 512).max() <= 0.02 * 1024 + 1.5
# erase brings the original back, blur/lighten/darken change in the right direction
painted = S['tex'].astype(int)
texture.paint({'points': [[0.5, 0.5]], 'radius': 0.03, 'strength': 1.0, 'mode': 'erase'}, head)
assert np.array_equal(S['tex'][512, cx], t0[512, cx])
assert np.abs(S['tex'].astype(int) - t0).sum() < np.abs(painted - t0).sum() / 5
texture.paint({'points': [[0.3, 0.3]], 'radius': 0.02, 'strength': 1.0, 'mode': 'lighten'}, head)
assert S['tex'][717, 307].sum() >= t0[717, 307].sum()
texture.paint({'points': [[0.3, 0.3]], 'radius': 0.02, 'strength': 1.0, 'mode': 'darken'}, head)
texture.paint({'points': [[0.3, 0.3]], 'radius': 0.02, 'strength': 1.0, 'mode': 'blur'}, head)
# history: back to the original, forward again
n = len(S['undo'])
for _ in range(n):
    assert texture.history('undo', head)['ok']
assert np.array_equal(S['tex'], t0) and not texture.history('undo', head)['ok']
assert texture.history('redo', head)['ok']
print('texture paint ok')

# png is a valid image of the same size
from PIL import Image
import io
assert Image.open(io.BytesIO(texture.png(head))).size == (1024, 1024)
try:
    texture.paint({'points': [], 'radius': 0.02}, head)
    raise SystemExit('empty stroke must fail')
except ValueError:
    pass

# UV: move/scale/rotate only the area, the rest stays
vt0 = S['vt'].copy()
sel = edit_api.DRAFT
sel.clear()
sel.brush(head.V[np.argmax(head.V[:, 2])], 0.5)
w = sel.weights(0.2)
wt = np.zeros(len(vt0))
np.maximum.at(wt, S['T'].ravel(), w[S['F'].ravel()])
texture.uv_xform({'op': 'move', 'du': 0.01, 'dv': -0.02}, head, w)
d = S['vt'] - vt0
assert np.abs(d[wt == 0]).max() == 0 and np.allclose(d[wt == 1], [0.01, -0.02])
vt1 = S['vt'].copy()
texture.uv_xform({'op': 'scale', 'factor': [2, 1]}, head, w)
e = lambda P, k: np.ptp(P[wt == 1][:, k])
assert abs(e(S['vt'], 0) / e(vt1, 0) - 2) < 1e-6 and abs(e(S['vt'], 1) / e(vt1, 1) - 1) < 1e-6
vt2 = S['vt'].copy()
texture.uv_xform({'op': 'rotate', 'angle': 30}, head, w)
assert np.allclose(np.ptp(S['vt'][wt == 1], 0).sum(), np.ptp(vt2[wt == 1], 0).sum(), rtol=0.5) and not np.allclose(S['vt'], vt2)
assert np.abs((S['vt'] - vt2)[wt == 0]).max() == 0
try:
    texture.uv_xform({'op': 'move'}, head, np.zeros(len(head.V)))
    raise SystemExit('empty area must fail')
except ValueError:
    pass
while texture.history('undo', head)['ok']:
    pass
assert np.array_equal(S['vt'], vt0)
print('uv ok')

# the layout / per-corner UV have the sizes the 3D view needs
assert len(texture.uv_layout(head)['f']) == 3 * len(head.F) and len(texture.mesh_uv(head)['uv']) == 6 * len(head.F)
# after replace-like topology change the tools refuse
class Fake:
    V = head.V[:10]
    F = head.F[:3]
try:
    texture.paint({'points': [[0.5, 0.5]]}, Fake)
    raise SystemExit('must refuse')
except ValueError:
    pass
assert (md5('work/baked.png'), md5('template/head_sub.obj')) == before
print('PASS test_texture_uv')
