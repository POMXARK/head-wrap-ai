#!/usr/bin/env python3
"""Structured journal of every step (the training data of the future local agent): one JSON line per step in
journal/steps.jsonl (in git, unlike work/).
journal.py add --stage 3 --problem eye_disc --tool wrap_fit --params '{"FLAT":1.0}' --metric mean_dist=0.0054 \
           --image work/render18.png --verdict partial --note "text"
Fields: ts, stage, problem (P1-P10 of docs/plan.md), tool (script), params, metrics, image, verdict (better|same|worse|partial|deadend), note.
`journal.py show` prints the table. The agent reads this file to choose the next tool for a problem (as head_agent.py does in corsairs-remake)."""
import argparse
import json
import os
import time

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'journal', 'steps.jsonl')


def add(**r):
    os.makedirs(os.path.dirname(PATH), exist_ok=True)
    r.setdefault('ts', time.strftime('%Y-%m-%dT%H:%M:%S'))
    with open(PATH, 'a') as f:
        f.write(json.dumps(r, ensure_ascii=False) + '\n')


def main():
    ap = argparse.ArgumentParser(usage=__doc__)
    ap.add_argument('cmd', choices=['add', 'show', 'rate', 'auto'])
    ap.add_argument('--n', type=int, default=-1, help='rate: step number from `show` (default: the last)')
    ap.add_argument('--before'); ap.add_argument('--after'); ap.add_argument('--target')
    ap.add_argument('--views', nargs=4)
    ap.add_argument('--stage', type=int)
    ap.add_argument('--problem')
    ap.add_argument('--tool')
    ap.add_argument('--params', default='{}')
    ap.add_argument('--metric', action='append', default=[])
    ap.add_argument('--image')
    ap.add_argument('--verdict', choices=['better', 'same', 'worse', 'partial', 'deadend', 'unknown'])
    ap.add_argument('--note', default='')
    a = ap.parse_args()
    if a.cmd == 'rate':  # the user's verdict on a step: stronger than the automatic one (agent.stats)
        L = open(PATH).read().splitlines()
        i = a.n if a.n >= 0 else len(L) - 1
        r = json.loads(L[i])
        r['user_verdict'] = a.verdict
        if a.note:
            r['user_note'] = a.note
        L[i] = json.dumps(r, ensure_ascii=False)
        open(PATH, 'w').write('\n'.join(L) + '\n')
        print('step', i, r.get('problem'), r.get('tool'), '->', a.verdict)
        return
    if a.cmd == 'auto':  # the verdict comes from the silhouette IoU of the result before and after (metrics.py)
        import metrics
        b = metrics.evaluate(a.before, a.target, a.views)
        c = metrics.evaluate(a.after, a.target, a.views)
        v = metrics.verdict_for(b, c)
        add(stage=a.stage, problem=a.problem, tool=a.tool, params=json.loads(a.params),
            metrics={'iou_before': b['mean_iou'], 'iou_after': c['mean_iou']}, image=a.image, verdict=v, note=a.note)
        print(v, round(b['mean_iou'], 4), '->', round(c['mean_iou'], 4))
        return
    if a.cmd == 'show':
        for i, l in enumerate(open(PATH)):
            r = json.loads(l)
            print(i, r['ts'][5:16], r.get('stage'), r.get('problem'), r.get('tool'), r.get('params'), r.get('metrics'), r.get('verdict'))
        return
    add(stage=a.stage, problem=a.problem, tool=a.tool, params=json.loads(a.params),
        metrics={k: float(v) for k, v in (m.split('=') for m in a.metric)}, image=a.image, verdict=a.verdict, note=a.note)


if __name__ == '__main__':
    main()
