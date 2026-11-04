#!/usr/bin/env python3
"""Tests of the review loop (python3 tests/test_review.py) in a temporary journal: the evaluator learns which image is
better from your choices, decides alone only when trained and sure, asks otherwise; the choices reach the journal and the
policy of head_agent; the focus box (text region / drawn)."""
import json
import os
import sys
import tempfile
import numpy as np
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import review  # noqa: E402
import journal  # noqa: E402

D = tempfile.mkdtemp()
review.PAIRS, review.EVAL, review.FOCUS = f'{D}/pairs.jsonl', f'{D}/eval.json', f'{D}/focus.json'
journal.PATH = f'{D}/steps.jsonl'
os.environ['HEAD_POLICY'] = f'{D}/policy.json'
bad = []


def check(name, ok, info=''):
    print('PASS' if ok else 'FAIL', name, info)
    if not ok:
        bad.append(name)


rng = np.random.default_rng(1)


def pair_imgs(i):
    base = (rng.random((96, 96, 3)) * 40 + 120).astype(np.uint8)  # "bad": noisy, thin lines
    bad_ = base.copy()
    bad_[::7, :, :] = 20
    good = np.asarray(Image.fromarray(base).filter(ImageFilter.GaussianBlur(3)))  # "good": smooth
    pa, pb = f'{D}/a{i}.png', f'{D}/b{i}.png'
    flip = i % 2
    Image.fromarray(bad_ if flip else good).save(pa)
    Image.fromarray(good if flip else bad_).save(pb)
    return pa, pb, ('b' if flip else 'a')


for i in range(12):
    pa, pb, best = pair_imgs(i)
    pid = review.add_pair('t', {'img': pa, 'tool': 'relax iters=5', 'label': 'A'}, {'img': pb, 'tool': 'despike', 'label': 'B'},
                          parts=['ear'], intent='asym')
    if i < 10:
        check(f'pair {pid} waits for you before it is trained' if i < review.MIN_VOTES else f'pair {pid}',
              review.decide(pid) is None or i >= review.MIN_VOTES)
        if review.Evaluator().n < review.MIN_VOTES or review.load_pairs()[-1]['status'] == 'pending':
            review.vote(pid, best, 'test')

st = review.stats()
check('evaluator trained on votes', st['evaluator_votes'] >= 8 and st['evaluator_acc'] == 1.0, st['evaluator_acc'])
pa, pb, best = pair_imgs(11)
pid = review.add_pair('t', {'img': pa, 'tool': 'x'}, {'img': pb, 'tool': 'y'})
c = review.decide(pid)
check('trained evaluator decides alone and right', c == best, c)
check('auto pair is marked auto', next(p for p in review.load_pairs() if p['id'] == pid)['status'] == 'auto')
pol = json.load(open(os.environ['HEAD_POLICY']))
check('choices reach the head policy', 'relax iters=5' in pol['arm'] and 'ear' in pol['part'], list(pol['arm']))
check('same image is not decided (unsure)', review.decide(review.add_pair('t', {'img': pa, 'tool': 'x'}, {'img': pa, 'tool': 'y'})) is None)

review.set_focus(review.region_box('ear'), 'ear')
b = review.get_focus()['box']
check('text region gives a UV box', b[2] > b[0] and b[3] > b[1], b)
pid = review.add_pair('t', {'img': pa, 'tool': 'x'}, {'img': pb, 'tool': 'y'})
check('new pair takes the focus box', next(p for p in review.load_pairs() if p['id'] == pid)['box'] == b)
review.set_focus(None)
check('focus off', review.get_focus() is None)
print('FAILED:' if bad else 'ALL PASS', bad)
sys.exit(1 if bad else 0)
