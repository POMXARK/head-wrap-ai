"""sculpt ops (ours): inflate / flatten / pinch / scale act inside the area, never outside, and do what their names say"""
import os
import sys
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import ops
from selection import Selection, load_obj

m = load_obj(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../template/head_sub.obj'))
V, F = m.V, m.F
sel = Selection(m).brush(V[np.argmax(V[:, 2])], 0.6)
w = sel.weights(0.3)
inside = w > 0
n = ops.vertex_normals(V, F)

# inflate: moves along the normal by amount, nothing outside
o = ops.apply('inflate', V, F, w, {'amount': 0.1})
d = o - V
assert np.abs(d[~inside]).max() == 0
assert np.allclose(d[w == 1], 0.1 * n[w == 1], atol=1e-9)
o2 = ops.apply('inflate', V, F, w, {'amount': -0.1})
assert np.allclose(o2 - V, -(o - V))
print('inflate ok')

# flatten: the spread along the mean normal shrinks
nm = (n * w[:, None]).sum(0)
nm /= np.linalg.norm(nm)
spread = lambda X: np.std((X[w == 1] - X[w == 1].mean(0)) @ nm)
o = ops.apply('flatten', V, F, w, {'strength': 1.0})
assert spread(o) < 0.05 * spread(V) + 1e-9 and np.abs((o - V)[~inside]).max() == 0
assert spread(ops.apply('flatten', V, F, w, {'strength': 0.5})) < spread(V)
print('flatten ok')

# pinch: the area contracts towards its centre
c = (V * w[:, None]).sum(0) / w.sum()
r = lambda X: np.linalg.norm(X[w == 1] - c, axis=1).mean()
o = ops.apply('pinch', V, F, w, {'strength': 0.5})
assert r(o) < r(V) and np.abs((o - V)[~inside]).max() == 0
print('pinch ok')

# scale: per-axis stretch about the centre; x only
o = ops.apply('scale', V, F, w, {'factor': [1.5, 1, 1]})
ex = lambda X, k: np.ptp(X[w == 1][:, k])
assert abs(ex(o, 0) / ex(V, 0) - 1.5) < 1e-6 and abs(ex(o, 1) / ex(V, 1) - 1) < 1e-6
assert np.abs((o - V)[~inside]).max() == 0
assert np.allclose(ops.apply('scale', V, F, w, {'factor': 1.0}), V)
print('scale ok')
for k in ('inflate', 'flatten', 'pinch', 'scale'):
    assert k in ops.REG
print('PASS test_sculpt_ops')
