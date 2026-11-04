#!/usr/bin/env python3
"""Eye opening polygons in head units (ours). The opening of the R eye was read by hand on the Qwen front view
(4096 px) in a crop whose corner is the pixel of the head point (0, 0.10) of the old frame (bbox of the target over
the whole image); the points are in pixels of that crop. They are turned into pixels of the image, then into head
units by the frame of the figure in the view (pdm_project_views.load_view, as bake.py projects). The L eye is the
mirror of the R eye about x = 0. The automatic segmentation of the sclera failed (the sclera is in shadow).
eye_open.py target.glb front.png -> work/eye_open.json {'R': [[x, y] ...], 'L': [...]}"""
import json
import sys
import numpy as np
import trimesh
sys.path.insert(0, '../corsairs-remake/tools')
import pdm_project_views as pv  # noqa: E402

CROP = [(215, 205), (330, 120), (450, 105), (560, 170), (500, 205), (380, 225), (260, 222)]
OLD_WIN = (0.0, 0.10)  # head x, y of the crop corner in the old frame


def head_units(P, view, lo, hi):
    _, (x0, x1, y0, y1), _ = view
    x = lo[0] + (P[:, 0] - x0) / (x1 - x0) * (hi[0] - lo[0])
    y = lo[1] + (y1 - P[:, 1]) / (y1 - y0) * (hi[1] - lo[1])
    return np.stack([x, y], 1)


def main():
    tgt = trimesh.load(sys.argv[1], force='mesh')
    lo, hi = tgt.bounds
    view = pv.load_view(sys.argv[2])
    S = view[0].shape[0]
    ox = (OLD_WIN[0] - lo[0]) / (hi[0] - lo[0]) * S
    oy = (1 - (OLD_WIN[1] - lo[1]) / (hi[1] - lo[1])) * S
    P = np.array(CROP, float) + [ox, oy]
    R = head_units(P, view, lo, hi)
    L = R * [-1, 1]
    json.dump({'R': R.tolist(), 'L': L[::-1].tolist()}, open('work/eye_open.json', 'w'))
    print('R x', R[:, 0].min().round(3), R[:, 0].max().round(3), 'y', R[:, 1].min().round(3), R[:, 1].max().round(3))


if __name__ == '__main__':
    main()
