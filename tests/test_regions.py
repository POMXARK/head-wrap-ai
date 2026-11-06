"""regions.py: the nose region holds only what stands out of the cheek plane, not the cheek strip beside it."""
import os, sys, json
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from selection import load_obj

HERE = os.path.join(os.path.dirname(__file__), '..')

if __name__ == '__main__':
    V = load_obj(os.path.join(HERE, 'template/head_sub.obj')).V
    d = json.load(open(os.path.join(HERE, 'template/regions.json')))
    r = np.array(d['vertex'])
    nose = d['names'].index('nose')
    n = V[r == nose]
    assert 300 < len(n) < 1300, len(n)
    # wing edge (|x| 0.2..0.25): only vertices clearly in front of the cheek (z ~1.45)
    edge = n[np.abs(n[:, 0]) > 0.2]
    assert len(edge) == 0 or edge[:, 2].min() > 1.46, edge[:, 2].min()
    # cheek strip beside the nose stays out
    cheek = (np.abs(V[:, 0]) > 0.15) & (np.abs(V[:, 0]) < 0.25) & (V[:, 1] > 6.7) & (V[:, 1] < 7.1) & (V[:, 2] < 1.46)
    assert not (r[cheek] == nose).any()
    # the ridge is still nose
    ridge = (np.abs(V[:, 0]) < 0.05) & (V[:, 1] > 6.8) & (V[:, 1] < 7.0) & (V[:, 2] > 1.6)
    assert ridge.any() and (r[ridge] == nose).all()
    print('test_regions OK, nose vertices:', len(n))
