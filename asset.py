"""Asset in memory (ours): parts with meshes, named selections, a reversible journal of ops (spec/*.schema.json).

a = Asset('hero'); a.add_part('head', V, F); a.select('sel_eye', 'head', mask, feather=0.02)
a.apply('smooth', 'head', selection='sel_eye', params={...}, by='user'); a.undo(); a.redo(); a.to_json() -> asset.json dict"""
import json
import os
import time
import numpy as np
import ops
from selection import Mesh, Selection

HERE = os.path.dirname(os.path.abspath(__file__))


class Asset:
    def __init__(self, aid, category='character'):
        self.id, self.category = aid, category
        self.parts = {}      # name -> Mesh
        self.sel = {}        # id -> (Selection, dict(name, part, feather, by))
        self.log = []        # applied ops (dicts of op.schema.json)
        self._undo, self._redo = [], []

    def add_part(self, name, V, F):
        self.parts[name] = Mesh(V, F)

    def select(self, sid, part, selection, name=None, feather=0.0, by='user'):
        self.sel[sid] = (selection, {'name': name or sid, 'part': part, 'feather': feather, 'by': by})

    def apply(self, name, part, selection=None, params=None, by='user', scores=None):
        m = self.parts[part]
        if selection is None:
            w = np.ones(len(m.V))
        else:
            s, meta = self.sel[selection]
            if meta['part'] != part:
                raise ValueError('selection %s belongs to %s, not %s' % (selection, meta['part'], part))
            w = s.weights(meta['feather'])
        before = (m.V.copy(), m.F.copy())
        after = ops.apply(name, m.V, m.F, w, params)
        self._push(part, before)
        m.V = after
        return self._record(name, part, params, by, selection, scores)

    def _push(self, part, before):
        self._undo.append((part, before))
        self._redo.clear()

    def _record(self, name, part, params, by, selection=None, scores=None):
        rec = {'op': name, 'target': part, 'params': params or {}, 'by': by}
        if selection:
            rec['selection'] = selection
        if scores:
            rec['scores'] = scores
        rec['ts'] = time.strftime('%Y-%m-%dT%H:%M:%S')
        self.log.append(rec)
        return rec

    def replace_mesh(self, part, V, F, params, by='user', scores=None):
        """topology-changing op (replace_part): the old (V, F) goes to the undo stack; selections of the part are dropped"""
        m = self.parts[part]
        self._push(part, (m.V.copy(), m.F.copy()))
        self.parts[part] = Mesh(V, F)
        for k in [k for k, (s, meta) in self.sel.items() if meta['part'] == part]:
            self.sel.pop(k)
        return self._record('replace_part', part, params, by, None, scores)

    def _swap(self, part, snap):
        m = self.parts[part]
        cur = (m.V.copy(), m.F.copy())
        self.parts[part] = Mesh(*snap) if len(snap[0]) != len(m.V) or not np.array_equal(snap[1], m.F) else m
        if self.parts[part] is m:
            m.V = snap[0]
        return cur

    def undo(self):
        if not self._undo:
            return False
        part, snap = self._undo.pop()
        self._redo.append((part, self._swap(part, snap), self.log.pop()))
        return True

    def redo(self):
        if not self._redo:
            return False
        part, snap, rec = self._redo.pop()
        self._undo.append((part, self._swap(part, snap)))
        self.log.append(rec)
        return True

    def to_json(self, source_file='', fmt='glb', outputs=('glb',)):
        return {'id': self.id, 'category': self.category, 'source': {'file': source_file, 'format': fmt},
                'outputs': list(outputs),
                'parts': [{'id': k, 'kind': k, 'mesh': k} for k in self.parts],
                'selections': [s.to_json(i, meta['name'], meta['part'], meta['feather'], meta['by'])
                               for i, (s, meta) in self.sel.items()],
                'ops': [{k: v for k, v in r.items() if k != 'ts'} for r in self.log]}
