#!/usr/bin/env python3
"""Models and their parts (ours): see what a GLB is made of, import a model, swap / add / remove a part, export.

model.py list [file.glb]                        parts of a model: node, vertices, triangles, size, texture, where it sits
model.py import <file.glb|obj> [--name N]       copy a model into models/ (a library you pick parts from)
model.py library                                models in models/ and their parts
model.py replace <target.glb> <node> <source.glb> [<source node>] [-o out.glb]
                                                put the part of another model in place of a node (same place unless --keep-shape)
model.py add <target.glb> <source.glb> <source node> [--as NAME] [-o out.glb]
model.py remove <target.glb> <node> [-o out.glb]
model.py rename <target.glb> <node> <new> [-o out.glb]
model.py remesh <target.glb> <node> (--faces N | --edge E | --subdivide K) [--no-texture] [-o out.glb]
                                                new topology (quadric decimation / isotropic remesh / midpoint subdivision), then new UV + the
                                                old texture carried over
model.py uv <target.glb> <node> [--size 2048] [-o out.glb]   new UV unwrap (xatlas) and the texture carried over to it
model.py texture-get <target.glb> <node> out.png           take the texture of a part to edit it anywhere
model.py texture-set <target.glb> <node> in.png [-o out.glb]   put an edited texture back
model.py texture-fix <target.glb> <node> x0,y0,x1,y1 [...] [-o out.glb]   LaMa inpaint of texture boxes (lama_patch.py)
Every change goes to journal/model_log.jsonl (what was replaced by what) and is written to a new file (-o), the
original stays. The fixed part names of the game model (head, ponytail ...) are the nodes; the skin / hair / eyes
split of a head is in template/regions.json."""
import argparse
import json
import os
import shutil
import time
import numpy as np
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(HERE, 'models')
LOG = os.path.join(HERE, 'journal', 'model_log.jsonl')


def load(path):
    s = trimesh.load(path, force='scene')
    return s


def parts(path):
    """[{node, geometry, vertices, triangles, uv, texture, bbox_min, bbox_max, centre}] of a model."""
    s = load(path)
    out = []
    for node in s.graph.nodes_geometry:
        T, gname = s.graph[node]
        g = s.geometry[gname].copy()
        g.apply_transform(T)
        mat = getattr(g.visual, 'material', None)
        img = getattr(mat, 'baseColorTexture', None) or getattr(mat, 'image', None)
        out.append(dict(node=node, geometry=gname, vertices=len(g.vertices), triangles=len(g.faces),
                        uv=getattr(g.visual, 'uv', None) is not None,
                        texture=list(img.size) if img is not None else None,
                        bbox_min=[round(float(x), 3) for x in g.bounds[0]],
                        bbox_max=[round(float(x), 3) for x in g.bounds[1]],
                        centre=[round(float(x), 3) for x in g.centroid]))
    return out


def show(path):
    ps = parts(path)
    print(f'{path}: {len(ps)} parts, {sum(p["triangles"] for p in ps)} triangles')
    for p in ps:
        tx = 'x'.join(map(str, p['texture'])) if p['texture'] else 'no texture'
        print(f"  {p['node']:<16} {p['vertices']:>7} v {p['triangles']:>7} tri  uv={'yes' if p['uv'] else 'no'}  {tx:<10} "
              f"box {p['bbox_min']} .. {p['bbox_max']}")
    return ps


def log(**kw):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    open(LOG, 'a').write(json.dumps(dict(ts=time.strftime('%Y-%m-%dT%H:%M:%S'), **kw), ensure_ascii=False) + '\n')


def _geom(path, node=None):
    s = load(path)
    names = list(s.graph.nodes_geometry)
    node = node or (names[0] if len(names) == 1 else None)
    if node not in names:
        raise SystemExit(f'node {node!r} not in {path}: {names}')
    T, gname = s.graph[node]
    return s.geometry[gname].copy(), T


def _save(s, dst):
    s.export(dst)
    print('->', dst)


def replace(target, node, source, snode=None, out=None, keep_shape=False):
    s = load(target)
    if node not in s.graph.nodes_geometry:
        raise SystemExit(f'node {node!r} not in {target}: {list(s.graph.nodes_geometry)}')
    T, old = s.graph[node]
    g, ST = _geom(source, snode)
    g.apply_transform(ST)
    if not keep_shape:  # the same place as the old part: move the new one to its centre
        og = s.geometry[old].copy()
        og.apply_transform(T)
        g.apply_translation(og.centroid - g.centroid)
    s.delete_geometry(old) if hasattr(s, 'delete_geometry') else s.geometry.pop(old)
    s.add_geometry(g, node_name=node, geom_name=f'{node}_geo')
    out = out or os.path.splitext(target)[0] + f'_{node}.glb'
    _save(s, out)
    log(op='replace', target=target, node=node, source=source, source_node=snode, out=out)
    return out


def add(target, source, snode, name=None, out=None):
    s = load(target)
    g, ST = _geom(source, snode)
    g.apply_transform(ST)
    name = name or snode
    s.add_geometry(g, node_name=name, geom_name=f'{name}_geo')
    out = out or os.path.splitext(target)[0] + f'_{name}.glb'
    _save(s, out)
    log(op='add', target=target, node=name, source=source, source_node=snode, out=out)
    return out


def remove(target, node, out=None):
    s = load(target)
    T, g = s.graph[node]
    s.graph.transforms.remove_node(node)
    s.geometry.pop(g, None)
    out = out or os.path.splitext(target)[0] + f'_no_{node}.glb'
    _save(s, out)
    log(op='remove', target=target, node=node, out=out)
    return out


def rename(target, node, new, out=None):
    s = load(target)
    T, g = s.graph[node]
    s.graph.transforms.remove_node(node)
    s.graph.update(frame_to=new, matrix=T, geometry=g)
    out = out or os.path.splitext(target)[0] + f'_{new}.glb'
    _save(s, out)
    log(op='rename', target=target, node=node, new=new, out=out)
    return out


def _texture(g):
    mat = getattr(g.visual, 'material', None)
    img = getattr(mat, 'baseColorTexture', None) or getattr(mat, 'image', None)
    return None if img is None else img.convert('RGB')


def _with_texture(g, uv, img):
    from trimesh.visual import TextureVisuals
    from trimesh.visual.material import PBRMaterial
    g.visual = TextureVisuals(uv=uv, material=PBRMaterial(baseColorTexture=img, metallicFactor=0.0, roughnessFactor=1.0))
    return g


def transfer_texture(old, new_V, new_F, new_uv, size):
    """Colour of the old textured mesh `old` on the UV of a new mesh (new_V, new_F, new_uv per vertex):
    every texel -> point of the new surface -> nearest point of the old one -> its UV -> its colour; seams are padded."""
    from PIL import Image
    from scipy import ndimage as ndi
    from trimesh.proximity import closest_point
    from trimesh.triangles import points_to_barycentric
    src = np.asarray(_texture(old))
    sh, sw = src.shape[:2]
    pts, texel = [], []
    for f in new_F:
        uv = new_uv[f] * [size, -size] + [0, size]  # v up -> image row down
        x0, y0 = np.floor(uv.min(0)).astype(int)
        x1, y1 = np.ceil(uv.max(0)).astype(int)
        xs, ys = np.meshgrid(np.arange(max(x0, 0), min(x1 + 1, size)), np.arange(max(y0, 0), min(y1 + 1, size)))
        P = np.c_[xs.ravel() + 0.5, ys.ravel() + 0.5]
        a, b, c = uv
        d = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(d) < 1e-9:
            continue
        l1 = ((b[1] - c[1]) * (P[:, 0] - c[0]) + (c[0] - b[0]) * (P[:, 1] - c[1])) / d
        l2 = ((c[1] - a[1]) * (P[:, 0] - c[0]) + (a[0] - c[0]) * (P[:, 1] - c[1])) / d
        l3 = 1 - l1 - l2
        ok = (l1 >= -1e-6) & (l2 >= -1e-6) & (l3 >= -1e-6)
        if ok.any():
            pts.append(l1[ok, None] * new_V[f[0]] + l2[ok, None] * new_V[f[1]] + l3[ok, None] * new_V[f[2]])
            texel.append(P[ok].astype(int))
    pts, texel = np.vstack(pts), np.vstack(texel)
    near, _, tri = closest_point(old, pts)  # once: it is the slow step
    ouv = old.visual.uv[old.faces[tri]]
    bary = points_to_barycentric(old.triangles[tri], near)
    u = (bary[:, :, None] * ouv).sum(1)
    px = np.clip(u[:, 0] * sw, 0, sw - 1).astype(int)
    py = np.clip((1 - u[:, 1]) * sh, 0, sh - 1).astype(int)
    out = np.zeros((size, size, 3), np.uint8)
    have = np.zeros((size, size), bool)
    out[texel[:, 1], texel[:, 0]] = src[py, px]
    have[texel[:, 1], texel[:, 0]] = True
    idx = ndi.distance_transform_edt(~have, return_distances=False, return_indices=True)  # pad over the seams
    out = out[idx[0], idx[1]]
    return Image.fromarray(out)


def auto_size(g, size=None):
    """texture size of the result: asked, else that of the old texture (2048 at most) - no point in more texels than there were"""
    t = _texture(g)
    return int(size) if size else (min(2048, max(t.size)) if t is not None else 1024)


def _unwrap(V, F, size):
    import xatlas
    vmap, nf, uv = xatlas.parametrize(V.astype(np.float32), F.astype(np.uint32))
    return V[vmap], nf.astype(int), uv.astype(np.float64)


def _edit_part(target, node, fn, out, suffix, **logkw):
    s = load(target)
    T, name = s.graph[node]
    g = s.geometry[name].copy()
    g.apply_transform(T)
    new = fn(g)
    s.delete_geometry(name) if hasattr(s, 'delete_geometry') else s.geometry.pop(name)
    s.add_geometry(new, node_name=node, geom_name=f'{node}_geo')
    out = out or os.path.splitext(target)[0] + f'_{suffix}.glb'
    _save(s, out)
    log(op=suffix, target=target, node=node, out=out, **logkw)
    return out


def remesh(target, node, faces=None, edge=None, subdivide=0, texture=True, size=None, out=None):
    """New topology of a part; with texture=True a new UV (xatlas) and the old texture carried over."""
    def fn(g):
        import fast_simplification
        V, F = np.asarray(g.vertices), np.asarray(g.faces)
        old = g.copy()
        for _ in range(subdivide):
            m = trimesh.Trimesh(V, F, process=False).subdivide()
            V, F = np.asarray(m.vertices), np.asarray(m.faces)
        if edge:
            import pymeshlab
            ms = pymeshlab.MeshSet()
            ms.add_mesh(pymeshlab.Mesh(V, F))
            ms.meshing_isotropic_explicit_remeshing(iterations=3, targetlen=pymeshlab.PureValue(edge))
            V, F = ms.current_mesh().vertex_matrix(), ms.current_mesh().face_matrix()
        if faces and len(F) > faces:
            V, F = fast_simplification.simplify(V.astype(np.float32), F.astype(np.int32), target_reduction=1 - faces / len(F))
        print(f'{len(g.faces)} -> {len(F)} triangles')
        if not texture or _texture(old) is None:
            return trimesh.Trimesh(V, F, process=False)
        size_ = auto_size(old, size)
        V2, F2, uv = _unwrap(V, F, size_)
        img = transfer_texture(old, V2, F2, uv, size_)
        return _with_texture(trimesh.Trimesh(V2, F2, process=False), uv, img)
    return _edit_part(target, node, fn, out, 'remesh', faces=faces, edge=edge, subdivide=subdivide)


def new_uv(target, node, size=None, out=None):
    def fn(g):
        size_ = auto_size(g, size)
        V2, F2, uv = _unwrap(np.asarray(g.vertices), np.asarray(g.faces), size_)
        img = transfer_texture(g, V2, F2, uv, size_) if _texture(g) is not None else None
        n = trimesh.Trimesh(V2, F2, process=False)
        return _with_texture(n, uv, img) if img is not None else n
    return _edit_part(target, node, fn, out, 'uv', size=size)


def texture_get(target, node, dst):
    s = load(target)
    T, name = s.graph[node]
    img = _texture(s.geometry[name])
    if img is None:
        raise SystemExit('no texture')
    img.save(dst)
    print('->', dst, img.size)


def texture_set(target, node, src, out=None):
    from PIL import Image
    def fn(g):
        return _with_texture(g, np.asarray(g.visual.uv), Image.open(src).convert('RGB'))
    return _edit_part(target, node, fn, out, 'texture', source=src)


def texture_fix(target, node, boxes, out=None):
    import subprocess
    import sys
    import tempfile
    d = tempfile.mkdtemp()
    a, b = os.path.join(d, 'a.png'), os.path.join(d, 'b.png')
    texture_get(target, node, a)
    subprocess.run([sys.executable, os.path.join(HERE, 'lama_patch.py'), a, b] + boxes, check=True)
    return texture_set(target, node, b, out)


def import_model(path, name=None):
    os.makedirs(LIB, exist_ok=True)
    name = name or os.path.splitext(os.path.basename(path))[0]
    dst = os.path.join(LIB, name + '.glb')
    if path.lower().endswith('.glb'):
        shutil.copy(path, dst)
    else:  # obj / ply / stl ... -> glb
        load(path).export(dst)
    log(op='import', source=path, out=dst)
    show(dst)
    return dst


def library():
    out = {}
    for f in sorted(os.listdir(LIB)) if os.path.isdir(LIB) else []:
        if f.endswith('.glb'):
            out[f] = parts(os.path.join(LIB, f))
    return out


def main():
    ap = argparse.ArgumentParser(usage=__doc__)
    ap.add_argument('cmd', choices=['list', 'import', 'library', 'replace', 'add', 'remove', 'rename', 'remesh', 'uv', 'texture-get', 'texture-set', 'texture-fix'])
    ap.add_argument('args', nargs='*')
    ap.add_argument('-o', '--out')
    ap.add_argument('--name')
    ap.add_argument('--as', dest='as_')
    ap.add_argument('--keep-shape', action='store_true')
    ap.add_argument('--faces', type=int)
    ap.add_argument('--edge', type=float)
    ap.add_argument('--subdivide', type=int, default=0)
    ap.add_argument('--size', type=int, default=None)
    ap.add_argument('--no-texture', action='store_true')
    a = ap.parse_args()
    x = a.args
    if a.cmd == 'list':
        show(x[0] if x else os.path.join(HERE, 'work', 'hero1_head.glb'))
    elif a.cmd == 'import':
        import_model(x[0], a.name)
    elif a.cmd == 'library':
        for f, ps in library().items():
            print(f, [p['node'] for p in ps])
    elif a.cmd == 'replace':
        replace(x[0], x[1], x[2], x[3] if len(x) > 3 else None, a.out, a.keep_shape)
    elif a.cmd == 'add':
        add(x[0], x[1], x[2], a.as_, a.out)
    elif a.cmd == 'remove':
        remove(x[0], x[1], a.out)
    elif a.cmd == 'rename':
        rename(x[0], x[1], x[2], a.out)
    elif a.cmd == 'remesh':
        remesh(x[0], x[1], a.faces, a.edge, a.subdivide, not a.no_texture, a.size, a.out)
    elif a.cmd == 'uv':
        new_uv(x[0], x[1], a.size, a.out)
    elif a.cmd == 'texture-get':
        texture_get(x[0], x[1], x[2])
    elif a.cmd == 'texture-set':
        texture_set(x[0], x[1], x[2], a.out)
    elif a.cmd == 'texture-fix':
        texture_fix(x[0], x[1], x[2:], a.out)


if __name__ == '__main__':
    main()
