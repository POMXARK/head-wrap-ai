#!/usr/bin/env python3
"""Cut the head + neck (with UV) and the eyes out of the MakeHuman base mesh (CC0): make_template.py base.obj template/
Neck cut at NECK_Y (below the chin ~6.2 in base units); writes head.obj (body above the cut, UV kept), eyes.obj."""
import os
import sys
import numpy as np

NECK_Y = 5.9


def read(path):
    v, vt, groups, cur = [], [], {}, None
    for l in open(path):
        t = l.split()
        if not t:
            continue
        if t[0] == 'v':
            v.append(list(map(float, t[1:4])))
        elif t[0] == 'vt':
            vt.append(list(map(float, t[1:3])))
        elif t[0] == 'g':
            cur = t[1]
            groups.setdefault(cur, [])
        elif t[0] == 'f':
            groups[cur].append([tuple(int(x) - 1 for x in p.split('/')[:2]) for p in t[1:]])
    return np.array(v), np.array(vt), groups


def write(path, v, vt, faces):
    """faces: list of [(vi, ti)...]; only used vertices/uvs are kept."""
    vs = sorted({p[0] for f in faces for p in f})
    ts = sorted({p[1] for f in faces for p in f})
    vm = {a: i + 1 for i, a in enumerate(vs)}
    tm = {a: i + 1 for i, a in enumerate(ts)}
    with open(path, 'w') as o:
        for a in vs:
            o.write('v %.5f %.5f %.5f\n' % tuple(v[a]))
        for a in ts:
            o.write('vt %.6f %.6f\n' % tuple(vt[a]))
        for f in faces:
            o.write('f ' + ' '.join(f'{vm[p[0]]}/{tm[p[1]]}' for p in f) + '\n')
    return len(vs), len(faces)


def main():
    src, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    v, vt, g = read(src)
    head = [f for f in g['body'] if all(v[p[0], 1] > NECK_Y for p in f)]
    print('head', write(os.path.join(out, 'head.obj'), v, vt, head))
    eyes = g['helper-l-eye'] + g['helper-r-eye']
    print('eyes', write(os.path.join(out, 'eyes.obj'), v, vt, eyes))


if __name__ == '__main__':
    main()
