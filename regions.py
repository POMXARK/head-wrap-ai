#!/usr/bin/env python3
"""Regions of the template by geometry (base units of the MakeHuman head, y up, face to +z):
regions.py template/head.obj template/eyes.obj template/regions.json preview.png
Regions: eyelid, ear, neck, scalp, lips, nose, face (the rest). Rules are ours; the preview colours them for checking."""
import json
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from bake import read_v, read_uv_faces

EYE_R = 0.2  # eyelid radius around the eyeball centre (the eyeball itself has r ~0.15)
NAMES = ['face', 'eyelid', 'ear', 'neck', 'scalp', 'lips', 'nose']
COL = ['#d9b08c', '#3366cc', '#cc3333', '#33aa55', '#222222', '#ff66aa', '#ffcc33']


def classify(V, eyes):
    r = np.zeros(len(V), int)
    r[(V[:, 1] > 7.85) | ((V[:, 2] < 0.2) & (V[:, 1] > 7.0))] = 4  # scalp: top, and the back above the ears
    r[(V[:, 1] < 6.15)] = 3  # neck under the chin
    r[(V[:, 2] > 1.25) & (V[:, 1] > 6.7) & (V[:, 1] < 7.1) & (np.abs(V[:, 0]) < 0.25)] = 6  # nose
    r[(V[:, 2] > 1.0) & (V[:, 1] > 6.35) & (V[:, 1] < 6.7) & (np.abs(V[:, 0]) < 0.6)] = 5  # lips (to be checked)
    r[(np.abs(V[:, 0]) > 0.8) & (V[:, 1] > 6.45) & (V[:, 1] < 7.6) & (V[:, 2] < 0.9)] = 2
    for sgn in (1, -1):
        c = eyes[sgn * eyes[:, 0] > 0].mean(0)
        r[np.linalg.norm(V - c, axis=1) < EYE_R] = 1
    return r


def main():
    V = read_v(sys.argv[1])
    r = classify(V, read_v(sys.argv[2]))
    json.dump({'names': NAMES, 'vertex': r.tolist()}, open(sys.argv[3], 'w'))
    print({n: int((r == i).sum()) for i, n in enumerate(NAMES)})
    _, F = read_uv_faces(sys.argv[1])
    fig, ax = plt.subplots(1, 2, figsize=(10, 6))
    for a, (i, j) in zip(ax, [(0, 1), (2, 1)]):
        a.scatter(V[:, i], V[:, j], s=1.5, c=[COL[k] for k in r])
        a.set_aspect('equal')
    plt.savefig(sys.argv[4], dpi=70)


if __name__ == '__main__':
    main()
