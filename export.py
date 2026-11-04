#!/usr/bin/env python3
"""Stage 8: one glb from the layers: export.py wrapped.obj template.obj baked.png out.glb [--ponytail tube.obj hair.png]
The head keeps the constant UV of the template (the texture is baked into it); the ponytail is a second mesh with its own
material. Vertices are split per (v, vt) pair by hand, the order of the template is kept."""
import sys
import numpy as np
import trimesh
from PIL import Image
from bake import read_v, read_uv_faces


def obj_mesh(vpath, tpath, tex):
    W = read_v(vpath)
    vt, F = read_uv_faces(tpath)
    pairs, idx, faces = {}, [], []
    for f in F:
        t = []
        for v, u in f:
            k = (v, u)
            if k not in pairs:
                pairs[k] = len(pairs)
                idx.append(k)
            t.append(pairs[k])
        faces.append(t)
    V = np.array([W[v] for v, _ in idx])
    UV = np.array([vt[u] for _, u in idx])
    m = trimesh.Trimesh(V, np.array(faces), process=False)
    m.visual = trimesh.visual.TextureVisuals(uv=UV, material=trimesh.visual.material.PBRMaterial(
        baseColorTexture=Image.open(tex).convert('RGB'), metallicFactor=0.0, roughnessFactor=0.9))
    return m


def main():
    a = sys.argv[1:]
    sc = trimesh.Scene()
    sc.add_geometry(obj_mesh(a[0], a[1], a[2]), node_name='head')
    if '--ponytail' in a:
        i = a.index('--ponytail')
        sc.add_geometry(obj_mesh(a[i + 1], a[i + 1], a[i + 2]), node_name='ponytail')
    sc.export(a[3])
    g = trimesh.load(a[3])
    print('exported', a[3], {k: (len(v.vertices), len(v.faces)) for k, v in g.geometry.items()})


if __name__ == '__main__':
    main()
