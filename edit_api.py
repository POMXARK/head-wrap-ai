"""State and handlers of the editing API (ours, task B1): one Asset in memory (the template head), selections, ops, undo.
Functions take/return JSON-able dicts; app.py only routes. Selection 'draft' is the one being painted."""
import json
import os
import threading
import numpy as np
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


def state():
    _init()
    m = A.parts['head']
    return {'regions': REG['names'], 'draft': int(DRAFT.count()), 'draft_vertices': DRAFT.vertices(), 'vertices': len(m.V),
            'selections': [{'id': i, 'name': meta['name'], 'count': s.count(), 'feather': meta['feather']}
                           for i, (s, meta) in A.sel.items()],
            'ops': A.log, 'can_undo': bool(A._undo), 'can_redo': bool(A._redo)}


def mesh():
    _init()
    m = A.parts['head']
    return {'v': np.round(m.V, 5).ravel().tolist(), 'f': m.F.ravel().tolist()}


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
    elif a == 'region':
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
    _init()
    return {'ok': A.undo() if action == 'undo' else A.redo()}
