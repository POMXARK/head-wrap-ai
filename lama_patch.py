#!/usr/bin/env python3
"""LaMa inpaint of rectangles of a texture (ours): lama_patch.py in.png out.png x0,y0,x1,y1 [x0,y0,x1,y1 ...]
The context window is the rectangles grown by 120 texels. Needs $W/lama (see lama_seam.py)."""
import os
import sys
import numpy as np
from PIL import Image

W = os.environ.get('W', '/media/roman/383be9ee-c114-4bf8-8956-66b985661cb4/home/remake-linux')
os.environ.setdefault('LAMA_MODEL', W + '/lama/big-lama.pt')
sys.path.insert(0, W + '/lama/pkg')
from simple_lama_inpainting import SimpleLama  # noqa: E402

t = np.array(Image.open(sys.argv[1]).convert('RGB'))
rs = [tuple(int(v) for v in a.split(',')) for a in sys.argv[3:]]
m = np.zeros(t.shape[:2], bool)
for x0, y0, x1, y1 in rs:
    m[y0:y1, x0:x1] = True
ys, xs = np.where(m)
a, b, c, d = max(ys.min() - 120, 0), ys.max() + 120, max(xs.min() - 120, 0), xs.max() + 120
sm = m[a:b, c:d]
res = np.array(SimpleLama()(Image.fromarray(t[a:b, c:d]), Image.fromarray((sm * 255).astype(np.uint8))))[:b - a, :d - c]
t[a:b, c:d][sm] = res[sm]
Image.fromarray(t).save(sys.argv[2])
