"""State and handlers of the editing API (ours, task B1): one Asset in memory (the template head), selections, ops, undo.
Functions take/return JSON-able dicts; app.py only routes. Selection 'draft' is the one being painted."""
import json
import os
import threading
import numpy as np
import replace_part as RP
from asset import Asset
from selection import Selection, load_obj

HERE = os.path.dirname(os.path.abspath(__file__))
LOCK = threading.Lock()
A = None
DRAFT = None
REG = json.load(open(os.path.join(HERE, 'template/regions.json')))


def _init():
    global A, DRAFT
    if A is None:
        m = load_obj(os.path.join(HERE, 'template/head_sub.obj'))
        A = Asset('head_template')
        A.add_part('head', m.V, m.F)
        DRAFT = Selection(A.parts['head'])
        A.add_part('body', *_mannequin(m))


def _mannequin(head):
    """a simple body (ours, a stand-in until a real torso asset exists): a tube under the neck ring of the template head,
    its top ring IS the neck ring, widening to shoulders"""
    ring = RP.ring_of(head.V, head.F)
    P = head.V[ring]
    c = P.mean(0)
    n = len(ring)
    rings = []
    prof = [(0.0, 1.0), (0.6, 1.5), (1.6, 3.2), (3.0, 3.8), (6.0, 3.4), (9.0, 3.2)]
    for dy, k in prof:
        Q = c + (P - c) * k
        Q[:, 1] = P[:, 1] - dy
        rings.append(Q)
    V = np.vstack(rings)
    F = []
    for r in range(len(prof) - 1):
        for i in range(n):
            a, b = r * n + i, r * n + (i + 1) % n
            F += [[a, a + n, b], [b, a + n, b + n]]
    return V, np.array(F)


DONORS = {'template': 'шаблон головы (этот же)', 'hero1': 'голова hero1 (work/hero1_head2.glb)'}


def _donor(name):
    if name == 'template':
        m = load_obj(os.path.join(HERE, 'template/head_sub.obj'))
        return m.V, m.F
    if name == 'hero1':
        import trimesh
        g = trimesh.load(os.path.join(HERE, 'work/hero1_head2.glb'), force='scene').geometry['geometry_0']
        V, inv = np.unique(g.vertices.round(6), axis=0, return_inverse=True)
        return V, inv.ravel()[g.faces]
    raise ValueError('unknown donor ' + name)


def replace_head(d):
    """d: {donor: template|hero1, scale: match_ring|keep}: put the donor head on the neck socket of the body"""
    global DRAFT
    _init()
    body = A.parts['body']
    bl = RP.boundary_loops(body.F)
    t_ring = max(bl, key=lambda l: body.V[l][:, 1].mean())
    dV, dF = _donor(d['donor'])
    d_ring = max(RP.boundary_loops(dF), key=len)
    V, F, rep = RP.replace(body.V, body.F, t_ring, dV, dF, d_ring, d.get('scale', 'match_ring'), outward=[0, 1, 0])
    off = rep['donor_offset']
    seam = d.get('seam', 'bridge')
    hV, hF = V[off:], F[len(body.F):] - off
    if seam == 'bridge':
        # copies of the body ring join the head part; the strip runs from the donor ring to them
        ring_copy = np.arange(len(hV), len(hV) + len(t_ring))
        hV = np.vstack([hV, body.V[t_ring]])
        strip, stretch = RP.bridge(hV, d_ring, ring_copy)
        hF = np.vstack([hF, strip])
        rep['seam_stretch'] = round(stretch, 3)
    A.replace_mesh('head', hV, hF,
                   {'donor': {'asset': d['donor'], 'part': 'head'}, 'socket': 'neck', 'scale': d.get('scale', 'match_ring'),
                    'seam': seam}, scores={'after': {'ring_gap': round(rep['ring_gap'], 4), 'scale': round(rep['scale'], 4),
                                                     **({'seam_stretch': rep['seam_stretch']} if 'seam_stretch' in rep else {})}})
    DRAFT = Selection(A.parts['head'])
    return {'report': rep, 'donors': DONORS}


def state():
    _init()
    m = A.parts['head']
    return {'regions': REG['names'], 'draft': int(DRAFT.count()), 'draft_vertices': DRAFT.vertices(), 'vertices': len(m.V),
            'selections': [{'id': i, 'name': meta['name'], 'count': s.count(), 'feather': meta['feather']}
                           for i, (s, meta) in A.sel.items()],
            'ops': A.log, 'donors': DONORS, 'can_undo': bool(A._undo), 'can_redo': bool(A._redo)}


def mesh():
    """head first (its vertex ids are the selection ids), then the body; nhead tells where the head ends"""
    _init()
    h, b = A.parts['head'], A.parts['body']
    V = np.vstack([h.V, b.V])
    F = np.vstack([h.F, b.F + len(h.V)])
    return {'v': np.round(V, 5).ravel().tolist(), 'f': F.ravel().tolist(), 'nhead': len(h.V), 'nfhead': len(h.F)}


def select(d):
    """d: {action: brush|box|region|grow|shrink|invert|clear|load, ...}; returns the draft mask as vertex list"""
    global DRAFT
    _init()
    a = d['action']
    m = A.parts['head']
    if a == 'brush':
        DRAFT.brush(d['point'], float(d['radius']), add=d.get('mode', 'add') == 'add')
    elif a == 'box':
        DRAFT.box(d['lo'], d['hi'], add=d.get('mode', 'add') == 'add', visible_from=d.get('visible_from'))
    elif a == 'ids':    # vertex ids picked by the client (screen rectangle, front faces only)
        ids = np.asarray(d['ids'], int)
        ids = ids[(ids >= 0) & (ids < len(DRAFT.mask))]
        if d.get('mode', 'add') == 'add':
            DRAFT.mask[ids] = True
        else:
            DRAFT.mask[ids] = False
    elif a == 'region':
        if len(m.V) != len(REG['vertex']):
            raise ValueError('Части (по списку) заданы только для шаблона головы; на другой голове выделяйте кистью')
        r = Selection.from_region(m, REG, d['name'])
        DRAFT.union(r) if d.get('mode', 'add') == 'add' else DRAFT.subtract(r)
    elif a == 'grow':
        DRAFT.grow(int(d.get('steps', 1)))
    elif a == 'shrink':
        DRAFT.shrink(int(d.get('steps', 1)))
    elif a == 'invert':
        DRAFT.invert()
    elif a == 'clear':
        DRAFT.clear()
    elif a == 'load':
        DRAFT = Selection(m, A.sel[d['id']][0].mask)
    else:
        raise ValueError('unknown selection action ' + a)
    return {'count': DRAFT.count(), 'vertices': DRAFT.vertices()}


def save_selection(d):
    _init()
    sid = 'sel_' + str(len(A.sel) + 1) if not d.get('id') else d['id']
    A.select(sid, 'head', Selection(A.parts['head'], DRAFT.mask), d.get('name') or sid, float(d.get('feather', 0)))
    return {'id': sid}


def delete_selection(sid):
    _init()
    A.sel.pop(sid, None)


def apply(d):
    """d: {op, selection (id | 'draft' | None), params, feather}"""
    _init()
    sel = d.get('selection')
    if sel == 'draft':
        if not DRAFT.count():
            raise ValueError('the draft selection is empty')
        A.select('draft', 'head', Selection(A.parts['head'], DRAFT.mask), 'draft', float(d.get('feather', 0)))
    rec = A.apply(d['op'], 'head', sel, d.get('params'), by=d.get('by', 'user'))
    if sel == 'draft':
        rec['selection'] = 'draft'
        A.sel.pop('draft', None)
    return {'rec': rec}


def history(action):
    """undo/redo; a replace_part changes the vertex order, so the draft selection (vertex ids) is dropped then"""
    global DRAFT
    _init()
    nxt = (A.log[-1] if A.log else None) if action == 'undo' else (A._redo[-1][2] if A._redo else None)
    r = A.undo() if action == 'undo' else A.redo()
    if (nxt and nxt['op'] == 'replace_part') or len(DRAFT.mask) != len(A.parts['head'].V):
        DRAFT = Selection(A.parts['head'])
    return {'ok': r}
