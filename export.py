#!/usr/bin/env python3
"""Stage 8: one glb from the layers: export.py wrapped.obj template.obj baked.png out.glb [--ponytail tube.obj hair.png] [--slit eye_open.json front.png target.glb]
The head keeps the constant UV of the template (the texture is baked into it); the ponytail is a second mesh with its own
material. Vertices are split per (v, vt) pair by hand, the order of the template is kept."""
import sys
import numpy as np
import trimesh
from PIL import Image
from bake import read_v, read_uv_faces


def obj_mesh(vpath, tpath, tex, polys=None):
    W = read_v(vpath)
    vt, F = read_uv_faces(tpath)
    if polys:
        import eye_slit
        drop = eye_slit.drop_mask(W, F, polys)
        print('slit: faces dropped', int(drop.sum()))
        F = [f for f, d in zip(F, drop) if not d]
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
    polys = None
    if '--slit' in a:  # --slit eye_open.json front.png target.glb: slit in the lids and an eyeball behind each
        import json
        import eye_slit
        i = a.index('--slit')
        polys = json.load(open(a[i + 1]))
        tgt = trimesh.load(a[i + 3], force='mesh')
        import pdm_project_views  # noqa: F401
        view = eye_slit.pv.load_view(a[i + 2])
    sc.add_geometry(obj_mesh(a[0], a[1], a[2], polys), node_name='head')
    if polys:
        W = read_v(a[0])
        for k, p in polys.items():
            m, _ = eye_slit.eyeball(p, W, view, *tgt.bounds)
            sc.add_geometry(m, node_name='eye_' + k)
    if '--ponytail' in a:
        i = a.index('--ponytail')
        pm = obj_mesh(a[i + 1], a[i + 1], a[i + 2])
        if pm.volume < 0:  # the tube was wound inside out: the engine culled its outside and showed its inside
            pm.invert()
        sc.add_geometry(pm, node_name='ponytail')
    sc.export(a[3])
    g = trimesh.load(a[3])
    print('exported', a[3], {k: (len(v.vertices), len(v.faces)) for k, v in g.geometry.items()})


if __name__ == '__main__':
    main()
