"""Log of edits for training data (ours, task C3). Append-only JSONL (journal/edits.jsonl, not in git: it is the user's data):
 {"event":"edit", id, ts, by: user|agent, op, params, feather, area:{count, centroid, bbox, regions}, metrics:{before, after}}
 {"event":"verdict", id, verdict: accepted|undone, ts}      <- undo/redo of the edit appends a verdict, nothing is rewritten
export_sft() folds the file: kept edits (last verdict accepted) -> {'prompt': state description, 'completion': op json} pairs;
export_pref() -> pairs (kept, undone) of edits with the same op in the same session as a preference signal for D1."""
import json
import os
import time
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT = os.path.join(HERE, 'journal', 'edits.jsonl')
PATH = os.environ.get('HW_EDIT_LOG', DEFAULT)


def _test_run():
    """other tests (python3 tests/test_*.py) exercise the API; they must not write into the user's real journal"""
    import sys
    return PATH == DEFAULT and os.path.basename(sys.argv[0]).startswith('test_')


def _w(rec):
    if _test_run():
        return
    os.makedirs(os.path.dirname(PATH), exist_ok=True)
    with open(PATH, 'a', encoding='utf-8') as f:
        f.write(json.dumps(rec, ensure_ascii=False) + '\n')


def record(by, op, params, feather, area, metrics, session=''):
    i = uuid.uuid4().hex[:10]
    _w({'event': 'edit', 'id': i, 'ts': time.strftime('%Y-%m-%dT%H:%M:%S'), 'session': session, 'by': by, 'op': op,
        'params': params, 'feather': feather, 'area': area, 'metrics': metrics})
    return i


def verdict(i, v):
    _w({'event': 'verdict', 'id': i, 'verdict': v, 'ts': time.strftime('%Y-%m-%dT%H:%M:%S')})


def load():
    """edits folded with their last verdict, in file order"""
    E, order = {}, []
    if not os.path.exists(PATH):
        return []
    for line in open(PATH, encoding='utf-8'):
        r = json.loads(line)
        if r['event'] == 'edit':
            E[r['id']] = dict(r, verdict='accepted')
            order.append(r['id'])
        elif r['id'] in E:
            E[r['id']]['verdict'] = r['verdict']
    return [E[i] for i in order]


def _prompt(e):
    a = e['area']
    return ('Область: %d вершин, центр %s, части %s. Растушёвка %.3g. Шероховатость до: %s.' %
            (a['count'], [round(x, 2) for x in a['centroid']], ', '.join(a.get('regions') or ['—']), e['feather'],
             e['metrics'].get('before', {}).get('roughness')))


def export_sft():
    return [{'prompt': _prompt(e), 'completion': json.dumps({'op': e['op'], 'params': e['params']}, ensure_ascii=False),
             'by': e['by'], 'metrics': e['metrics']} for e in load() if e['verdict'] == 'accepted']


def export_pref():
    out = []
    es = load()
    for k, e in enumerate(es):
        if e['verdict'] != 'undone':
            continue
        for g in es[k + 1:]:      # the next kept edit of the same op in the same session replaced the undone one
            if g['verdict'] == 'accepted' and g['op'] == e['op'] and g['session'] == e['session']:
                out.append({'prompt': _prompt(e), 'rejected': e['params'], 'chosen': g['params'], 'op': e['op']})
                break
    return out


if __name__ == '__main__':
    import sys
    kind = sys.argv[1] if len(sys.argv) > 1 else 'sft'
    for r in (export_sft() if kind == 'sft' else export_pref()):
        print(json.dumps(r, ensure_ascii=False))
