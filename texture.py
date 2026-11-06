"""Texture and UV editing of the head (ours): paint on the texture (brush, erase to the original, blur, lighten,
darken) and move/scale/rotate the UV of the selected area. Every head topology has its own state (UV, texture, history),
found by the shape of the faces: the template head, and an imported head that brought UV (register()); a head without UV
has no state and the tools refuse. One history per state for both kinds of edits.
Template: template/head_sub.obj (UV) and work/baked.png (texture); originals are never overwritten, export goes to work/head_edit.*"""
import io
import os
import numpy as np
from PIL import Image
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
OBJ = os.path.join(HERE, 'template/head_sub.obj')
TEX = os.path.join(HERE, 'work/baked.png')
S = None            # the template state
REGISTRY = {}       # topology key -> state


def _key(head):
    return (len(head.V), hash(np.ascontiguousarray(head.F).tobytes()))


def _init():
    global S
    if S is not None:
        return S
    vt, F, T, nv = [], [], [], 0
    for l in open(OBJ):
        t = l.split()
        if not t:
            continue
        if t[0] == 'v':
            nv += 1
        elif t[0] == 'vt':
            vt.append([float(t[1]), float(t[2])])
        elif t[0] == 'f':
            p = [[int(y) - 1 if y else -1 for y in (x.split('/') + ['', ''])[:2]] for x in t[1:]]
            for k in range(1, len(p) - 1):
                F.append([p[0][0], p[k][0], p[k + 1][0]])
                T.append([p[0][1], p[k][1], p[k + 1][1]])
    img = np.asarray(Image.open(TEX).convert('RGB'), np.uint8).copy()
    S = {'vt': np.array(vt), 'F': np.array(F), 'T': np.array(T), 'nv': nv, 'tex': img, 'orig': img.copy(), 'undo': [], 'redo': [],
         'rev': 0}
    REGISTRY[(nv, hash(S['F'].tobytes()))] = S
    return S


def register(head, vt, T, img=None):
    """UV of an imported head: vt (n,2) UV rows, T (faces,3) rows per corner (aligned with head.F), img PIL/array or None (grey)"""
    _init()
    if img is None:
        a = np.full((1024, 1024, 3), 200, np.uint8)
    else:
        a = np.asarray(img.convert('RGB') if hasattr(img, 'convert') else img, np.uint8).copy()
    s = {'vt': np.asarray(vt, float), 'F': np.asarray(head.F).copy(), 'T': np.asarray(T, int), 'nv': len(head.V), 'tex': a,
         'orig': a.copy(), 'undo': [], 'redo': [], 'rev': 0}
    REGISTRY[_key(head)] = s
    return s


def template_uv():
    s = _init()
    return s['vt'], s['T'], s['tex']


def state_of(head):
    """the state of this head or None"""
    _init()
    return REGISTRY.get(_key(head))


def reset():
    global S
    S = None
    REGISTRY.clear()


def available(head):
    return state_of(head) is not None


def _need(head):
    s = state_of(head)
    if s is None:
        raise ValueError('У этой головы нет развёртки (UV) и текстуры: они есть у шаблона и у импортированных голов с UV')
    return s


def _push(s, kind):
    s['undo'].append((kind, (s['tex'] if kind == 'tex' else s['vt']).copy()))
    del s['undo'][:-30]
    s['redo'].clear()
    s['rev'] += 1


def png(head):
    b = io.BytesIO()
    Image.fromarray(_need(head)['tex']).save(b, 'PNG')
    return b.getvalue()


def uv_layout(head):
    s = _need(head)
    return {'vt': np.round(s['vt'], 5).ravel().tolist(), 'f': s['T'].ravel().tolist(), 'rev': s['rev']}


def mesh_uv(head):
    """texture coordinates per face corner (the 3D view needs a non-indexed mesh because UV seams split vertices)"""
    s = _need(head)
    return {'uv': np.round(s['vt'][s['T']].reshape(-1), 5).tolist(), 'rev': s['rev']}


def paint(d, head):
    """d: {points:[[u,v],..], radius (UV units), strength 0..1, mode paint|erase|blur|lighten|darken, color [r,g,b]}"""
    s = _need(head)
    pts = np.asarray(d['points'], float).reshape(-1, 2)
    if not len(pts):
        raise ValueError('нет точек мазка')
    mode = d.get('mode', 'paint')
    if mode not in ('paint', 'erase', 'blur', 'lighten', 'darken'):
        raise ValueError('unknown texture mode ' + mode)
    color = np.asarray(d.get('color', [200, 60, 60]), float)
    st = float(d.get('strength', 0.5))
    H, W = s['tex'].shape[:2]
    rp = max(float(d.get('radius', 0.02)) * W, 1.0)
    _push(s, 'tex')
    for u, v in pts:
        cx, cy = u * W, (1 - v) * H
        x0, x1 = int(max(cx - rp, 0)), int(min(cx + rp + 1, W))
        y0, y1 = int(max(cy - rp, 0)), int(min(cy + rp + 1, H))
        if x1 <= x0 or y1 <= y0:
            continue
        yy, xx = np.mgrid[y0:y1, x0:x1]
        dist = np.hypot(xx - cx, yy - cy) / rp
        a = (st * np.clip(2 * (1 - dist), 0, 1))[..., None]
        P = s['tex'][y0:y1, x0:x1].astype(np.float32)
        if mode == 'paint':
            Q = color[None, None, :]
        elif mode == 'erase':
            Q = s['orig'][y0:y1, x0:x1].astype(np.float32)
        elif mode == 'blur':
            Q = ndimage.uniform_filter(P, size=(5, 5, 1), mode='nearest')
        elif mode == 'lighten':
            Q = P + 0.25 * (255 - P)
        else:
            Q = P * 0.75
        s['tex'][y0:y1, x0:x1] = np.clip(P + a * (Q - P), 0, 255).astype(np.uint8)
    return {'rev': s['rev'], 'points': int(len(pts))}


def uv_xform(d, head, w):
    """d: {op: move|scale|rotate, du, dv, factor [su,sv] or number, angle (deg)}; w: per-vertex weights of the area.
    Only the UV of the area move (blended by w), pivot = the weighted centre of the area's UV."""
    s = _need(head)
    wt = np.zeros(len(s['vt']))
    np.maximum.at(wt, s['T'].ravel(), w[s['F'].ravel()])
    if not (wt > 0).any():
        raise ValueError('область пуста')
    op = d['op']
    P = s['vt']
    c = (P * wt[:, None]).sum(0) / wt.sum()
    if op == 'move':
        Q = P + np.array([float(d.get('du', 0)), float(d.get('dv', 0))])
    elif op == 'scale':
        f = np.broadcast_to(np.asarray(d.get('factor', 1.2), float), (2,))
        Q = c + (P - c) * f
    elif op == 'rotate':
        a = np.radians(float(d.get('angle', 15)))
        R = np.array([[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]])
        Q = c + (P - c) @ R.T
    else:
        raise ValueError('unknown uv op ' + str(op))
    _push(s, 'uv')
    s['vt'] = np.where((wt > 0)[:, None], P + wt[:, None] * (Q - P), P)
    return {'rev': s['rev'], 'moved': int((wt > 0).sum())}


def history(action, head):
    s = _need(head)
    a, b = ('undo', 'redo') if action == 'undo' else ('redo', 'undo')
    if not s[a]:
        return {'ok': False}
    kind, snap = s[a].pop()
    s[b].append((kind, (s['tex'] if kind == 'tex' else s['vt']).copy()))
    s['tex' if kind == 'tex' else 'vt'] = snap
    s['rev'] += 1
    return {'ok': True, 'kind': kind, 'rev': s['rev']}


def status(head):
    s = state_of(head)
    if s is None:
        return {'can_undo': False, 'can_redo': False, 'rev': 0}
    return {'can_undo': bool(s['undo']), 'can_redo': bool(s['redo']), 'rev': s['rev']}


def pil(head):
    return Image.fromarray(_need(head)['tex'])


def obj_text(head):
    """OBJ bytes: current vertices, edited UV"""
    s = _need(head)
    out = ['# head with edited UV (head-wrap-ai)']
    out += ['v %.5f %.5f %.5f' % tuple(v) for v in head.V]
    out += ['vt %.5f %.5f' % tuple(t) for t in s['vt']]
    out += ['f %d/%d %d/%d %d/%d' % (a + 1, ta + 1, b + 1, tb + 1, c + 1, tc + 1) for (a, b, c), (ta, tb, tc) in zip(s['F'], s['T'])]
    return ('\n'.join(out) + '\n').encode()


def export(head):
    """work/head_edit.png + work/head_edit.obj (current vertices, edited UV)"""
    s = _need(head)
    os.makedirs(os.path.join(HERE, 'work'), exist_ok=True)
    Image.fromarray(s['tex']).save(os.path.join(HERE, 'work/head_edit.png'))
    with open(os.path.join(HERE, 'work/head_edit.obj'), 'wb') as f:
        f.write(obj_text(head))
    return {'files': ['work/head_edit.png', 'work/head_edit.obj']}
