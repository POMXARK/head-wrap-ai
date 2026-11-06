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
        before = m.V.copy()
        after = ops.apply(name, m.V, m.F, w, params)
        self._undo.append((part, before, len(self.log)))
        self._redo.clear()
        m.V = after
        rec = {'op': name, 'target': part, 'params': params or {}, 'by': by}
        if selection:
            rec['selection'] = selection
        if scores:
            rec['scores'] = scores
        rec['ts'] = time.strftime('%Y-%m-%dT%H:%M:%S')
        self.log.append(rec)
        return rec

    def undo(self):
        if not self._undo:
            return False
        part, before, n = self._undo.pop()
        m = self.parts[part]
        self._redo.append((part, m.V.copy(), self.log.pop()))
        m.V = before
        return True

    def redo(self):
        if not self._redo:
            return False
        part, after, rec = self._redo.pop()
        m = self.parts[part]
        self._undo.append((part, m.V.copy(), len(self.log)))
        m.V = after
        self.log.append(rec)
        return True

    def to_json(self, source_file='', fmt='glb', outputs=('glb',)):
        return {'id': self.id, 'category': self.category, 'source': {'file': source_file, 'format': fmt},
                'outputs': list(outputs),
                'parts': [{'id': k, 'kind': k, 'mesh': k} for k in self.parts],
                'selections': [s.to_json(i, meta['name'], meta['part'], meta['feather'], meta['by'])
                               for i, (s, meta) in self.sel.items()],
                'ops': [{k: v for k, v in r.items() if k != 'ts'} for r in self.log]}
