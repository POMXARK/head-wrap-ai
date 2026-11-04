#!/usr/bin/env python3
"""Tests of model.py on work/hero1_head.glb (python3 tests/test_model.py): every operation, the texture carried over
(colour of the new texture near the old one), the original file untouched. Prints PASS/FAIL per check."""
import hashlib
import os
import sys
import tempfile
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import model  # noqa: E402

model.LOG = os.path.join(tempfile.mkdtemp(), 'model_log.jsonl')
SRC = os.path.join(HERE, 'work', 'hero1_head.glb')
D = tempfile.mkdtemp()
bad = []


def check(name, ok, info=''):
    print('PASS' if ok else 'FAIL', name, info)
    if not ok:
        bad.append(name)


def part(path, node):
    return next(p for p in model.parts(path) if p['node'] == node)


md5 = hashlib.md5(open(SRC, 'rb').read()).hexdigest()
p0 = part(SRC, 'ponytail')

o = model.remesh(SRC, 'ponytail', faces=800, size=512, out=f'{D}/r.glb')
p = part(f'{D}/r.glb', 'ponytail')
check('remesh faces', 600 <= p['triangles'] <= 900, p['triangles'])
check('remesh keeps uv and texture', p['uv'] and p['texture'] == [512, 512])
check('remesh keeps other parts', part(f'{D}/r.glb', 'head')['triangles'] == part(SRC, 'head')['triangles'])
check('remesh keeps place', np.allclose(p['centre'], p0['centre'], atol=0.02), f"{p['centre']} {p0['centre']}")

model.texture_get(f'{D}/r.glb', 'ponytail', f'{D}/t.png')
new = np.asarray(Image.open(f'{D}/t.png')).reshape(-1, 3)
model.texture_get(SRC, 'ponytail', f'{D}/t0.png')
old = np.asarray(Image.open(f'{D}/t0.png')).reshape(-1, 3)
check('texture colour carried over', np.abs(new.mean(0) - old.mean(0)).max() < 25, f'{new.mean(0)} vs {old.mean(0)}')

model.remesh(SRC, 'ponytail', subdivide=1, size=512, out=f'{D}/s.glb')
check('subdivide x4', part(f'{D}/s.glb', 'ponytail')['triangles'] == 4 * p0['triangles'])

model.remesh(SRC, 'ponytail', edge=0.02, size=512, out=f'{D}/e.glb')
check('isotropic remesh', part(f'{D}/e.glb', 'ponytail')['triangles'] > 100)

model.new_uv(SRC, 'ponytail', size=512, out=f'{D}/u.glb')
pu = part(f'{D}/u.glb', 'ponytail')
check('new uv', pu['uv'] and pu['texture'] == [512, 512] and pu['bbox_min'] == p0['bbox_min'], pu['vertices'])

model.texture_set(SRC, 'ponytail', f'{D}/t0.png', out=f'{D}/ts.glb')
check('texture set', part(f'{D}/ts.glb', 'ponytail')['texture'] == [512, 512])

model.texture_fix(SRC, 'ponytail', ['100,100,160,160'], out=f'{D}/tf.glb')
model.texture_get(f'{D}/tf.glb', 'ponytail', f'{D}/tf.png')
a, b = np.asarray(Image.open(f'{D}/t0.png')), np.asarray(Image.open(f'{D}/tf.png'))
check('texture fix changes only the box', (a != b).any() and not (a[:80] != b[:80]).any(), int((a != b).any(2).sum()))

check('original untouched', hashlib.md5(open(SRC, 'rb').read()).hexdigest() == md5)
print('FAILED:' if bad else 'ALL PASS', bad)
sys.exit(1 if bad else 0)
