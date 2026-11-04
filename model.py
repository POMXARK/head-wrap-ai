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
    ap.add_argument('cmd', choices=['list', 'import', 'library', 'replace', 'add', 'remove', 'rename'])
    ap.add_argument('args', nargs='*')
    ap.add_argument('-o', '--out')
    ap.add_argument('--name')
    ap.add_argument('--as', dest='as_')
    ap.add_argument('--keep-shape', action='store_true')
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


if __name__ == '__main__':
    main()
