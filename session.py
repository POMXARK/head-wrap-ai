#!/usr/bin/env python3
"""Command line of the review loop (see review.py).

session.py add <problem> --a img [--a-tool T --a-params JSON --a-label S] --b img [...] [--base img] [--box x0,y0,x1,y1] [--ask]
session.py list [--all]          pending pairs (all: with history)
session.py wait <id> [--timeout S]   block until you voted in http://127.0.0.1:8770/review (or `session.py vote`), print the choice
session.py vote <id> a|b|same|both_worse|skip [--note S]
session.py decide <id>           let the evaluator choose when it is trained and sure (else the pair stays pending)
session.py focus [region|x0,y0,x1,y1|off]   the part we work on (new pairs take it; also draggable in /review)
session.py stats | retrain
`add --ask` = add, try the evaluator, and if it is not sure wait for you (the edit model asking "better or worse?")."""
import argparse
import json
import sys
import time

import review


def variant(a, p):
    return {'img': getattr(a, p), 'tool': getattr(a, p + '_tool'), 'params': json.loads(getattr(a, p + '_params')),
            'label': getattr(a, p + '_label') or getattr(a, p + '_tool') or p.upper()}


def wait(pid, timeout):
    t0 = time.time()
    while time.time() - t0 < timeout:
        p = next(x for x in review.load_pairs() if x['id'] == pid)
        if p['status'] != 'pending':
            return p['choice'], p.get('note', '')
        time.sleep(2)
    return None, 'timeout'


def main():
    ap = argparse.ArgumentParser(usage=__doc__)
    ap.add_argument('cmd', choices=['focus', 'add', 'list', 'wait', 'vote', 'decide', 'stats', 'retrain'])
    ap.add_argument('x', nargs='?')
    ap.add_argument('y', nargs='?')
    for p in 'ab':
        ap.add_argument(f'--{p}')
        ap.add_argument(f'--{p}-tool')
        ap.add_argument(f'--{p}-params', default='{}')
        ap.add_argument(f'--{p}-label')
    ap.add_argument('--base')
    ap.add_argument('--box')
    ap.add_argument('--region', help='part by name from template/regions.json (face, ear, neck, lips, nose, eyelid, scalp)')
    ap.add_argument('--question', default='Какой вариант лучше?')
    ap.add_argument('--ask', action='store_true')
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--note', default='')
    ap.add_argument('--timeout', type=float, default=3600)
    a = ap.parse_args()
    if a.cmd == 'add':
        box = [int(v) for v in a.box.split(',')] if a.box else (review.region_box(a.region) if a.region else None)
        pid = review.add_pair(a.x, variant(a, 'a'), variant(a, 'b'), a.base, a.question, box)
        print('pair', pid)
        if a.ask:
            c = review.decide(pid)
            if c:
                print('auto', c)
            else:
                print(f'waiting for your choice: http://127.0.0.1:8770/review', flush=True)
                print('choice', *wait(pid, a.timeout))
    elif a.cmd == 'focus':
        if a.x:
            box = None if a.x == 'off' else ([int(v) for v in a.x.split(',')] if ',' in a.x else review.region_box(a.x))
            review.set_focus(box, a.x)
        print(review.get_focus())
    elif a.cmd == 'list':
        for p in review.load_pairs():
            if a.all or p['status'] == 'pending':
                print(p['id'], p['status'], p.get('choice', ''), p['problem'], p['a']['label'], 'vs', p['b']['label'])
    elif a.cmd == 'wait':
        print(*wait(int(a.x), a.timeout))
    elif a.cmd == 'vote':
        print('evaluator acc on votes:', review.vote(int(a.x), a.y, a.note))
    elif a.cmd == 'decide':
        print(review.decide(int(a.x)))
    elif a.cmd == 'retrain':
        print(review.retrain().acc)
    else:
        print(json.dumps(review.stats(), ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
