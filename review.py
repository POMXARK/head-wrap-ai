#!/usr/bin/env python3
"""Interactive review loop (ours): pairs of variants -> your choice -> a learning evaluator and a learning edit policy.

A pair (journal/pairs.jsonl, in git) = two variants A and B of one problem, each with an image and the arm that made it
(tool + params), maybe a base image. Statuses: pending (waits for you), done (you chose), auto (the evaluator was sure).
Choices: a, b, same, both_worse, skip.
- history: every pair and your choice stay in journal/pairs.jsonl; every choice also goes to journal/steps.jsonl as
  user_verdict of the two arms (winner better, loser worse, same -> same, both_worse -> worse), so agent.py (UCB over arms,
  the edit policy) learns from it;
- evaluator: a pairwise logistic model on cheap image features (Lab mean/std, colour, gradient and thin-line energy,
  dark share, noise); P(A better) = sigmoid(score(A) - score(B)); retrained on all a/b choices after every vote
  (journal/evaluator.json). It needs MIN_VOTES choices before it may decide alone, and only decides when
  |P - 0.5| >= SURE; otherwise the pair waits for you (that is "ask me when needed")."""
import json
import math
import os
import time
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage import color

import journal

HERE = os.path.dirname(os.path.abspath(__file__))
PAIRS = os.path.join(HERE, 'journal', 'pairs.jsonl')
EVAL = os.path.join(HERE, 'journal', 'evaluator.json')
MIN_VOTES = 8
SURE = 0.3
NAMES = ['L_mean', 'L_std', 'a_mean', 'b_mean', 'chroma_std', 'sat_mean', 'grad_energy', 'line_energy', 'dark_share',
         'noise', 'bright_share', 'warmth']


def features(path, box=None):
    """Feature vector of an image (box = x0,y0,x1,y1 crop)."""
    im = Image.open(path).convert('RGB')
    if box:
        im = im.crop(box)
    im.thumbnail((384, 384))
    lab = color.rgb2lab(np.asarray(im) / 255.0)
    L, a, b = lab[..., 0], lab[..., 1], lab[..., 2]
    gy, gx = ndi.sobel(L, 0), ndi.sobel(L, 1)
    g = np.hypot(gx, gy)
    lap = np.abs(ndi.laplace(ndi.gaussian_filter(L, 0.7)))
    hp = L - ndi.gaussian_filter(L, 2.0)
    hsv = np.asarray(im.convert('HSV')) / 255.0
    return np.array([L.mean(), L.std(), a.mean(), b.mean(), np.hypot(a, b).std(), hsv[..., 1].mean(), g.mean(),
                     np.percentile(lap, 99), (L < 20).mean(), hp.std(), (L > 80).mean(), (a - b).mean()])


def _sig(x):
    return 1 / (1 + math.exp(-max(-30, min(30, x))))


class Evaluator:
    def __init__(self):
        self.w = np.zeros(len(NAMES))
        self.mu = np.zeros(len(NAMES))
        self.sd = np.ones(len(NAMES))
        self.n = 0
        self.acc = None
        if os.path.exists(EVAL):
            d = json.load(open(EVAL))
            self.w, self.mu, self.sd = (np.array(d[k]) for k in ('w', 'mu', 'sd'))
            self.n, self.acc = d['n'], d.get('acc')

    def score(self, f):
        return float(self.w @ ((f - self.mu) / self.sd))

    def prob_a(self, fa, fb):
        return _sig(self.score(fa) - self.score(fb))

    def fit(self, pairs, epochs=300, lr=0.2, l2=0.05):
        """pairs: [(feature of the winner, feature of the loser)]"""
        self.n = len(pairs)
        if not pairs:
            return
        allf = np.array([f for p in pairs for f in p])
        self.mu, self.sd = allf.mean(0), allf.std(0) + 1e-6
        D = np.array([(w - l) / self.sd for w, l in pairs])
        w = np.zeros(len(NAMES))
        for _ in range(epochs):
            p = 1 / (1 + np.exp(-np.clip(D @ w, -30, 30)))
            w += lr * (D.T @ (1 - p) / len(D) - l2 * w)
        self.w = w
        self.acc = float(((D @ w) > 0).mean())
        json.dump({'w': self.w.tolist(), 'mu': self.mu.tolist(), 'sd': self.sd.tolist(), 'n': self.n, 'acc': self.acc,
                   'names': NAMES}, open(EVAL, 'w'))


def load_pairs():
    return [json.loads(l) for l in open(PAIRS)] if os.path.exists(PAIRS) else []


def save_pairs(P):
    os.makedirs(os.path.dirname(PAIRS), exist_ok=True)
    open(PAIRS, 'w').write(''.join(json.dumps(p, ensure_ascii=False) + '\n' for p in P))


def _feat(v, box):
    return features(v['img'] if os.path.isabs(v['img']) else os.path.join(HERE, v['img']), box)


def add_pair(problem, a, b, base=None, question='Какой вариант лучше?', box=None, parts=None, intent=None):
    """a, b = {'img': path, 'tool': ..., 'params': {...}, 'label': text}; returns the id."""
    box = box or (get_focus() or {}).get('box')
    P = load_pairs()
    pid = (P[-1]['id'] + 1) if P else 1
    ev = Evaluator()
    pred = ev.prob_a(_feat(a, box), _feat(b, box)) if ev.n else None
    P.append({'id': pid, 'ts': time.strftime('%Y-%m-%dT%H:%M:%S'), 'problem': problem, 'a': a, 'b': b, 'base': base,
              'box': box, 'question': question, 'parts': parts or [], 'intent': intent, 'status': 'pending', 'pred_a': pred})
    save_pairs(P)
    return pid


def retrain():
    ev, win = Evaluator(), []
    for p in load_pairs():
        if p.get('choice') in ('a', 'b') and p['status'] == 'done':
            w, l = (p['a'], p['b']) if p['choice'] == 'a' else (p['b'], p['a'])
            win.append((_feat(w, p.get('box')), _feat(l, p.get('box'))))
    ev.fit(win)
    return ev


def _journal(p, choice, user):
    verdict = {'a': ('better', 'worse'), 'b': ('worse', 'better'), 'same': ('same', 'same'),
               'both_worse': ('worse', 'worse')}.get(choice)
    if not verdict:
        return
    for v, vd in zip((p['a'], p['b']), verdict):
        r = dict(stage=9, problem=p['problem'], tool=v.get('tool'), params=v.get('params', {}), image=v['img'],
                 verdict=vd, note=f"pair {p['id']} {choice}")
        if user:
            r['user_verdict'] = vd
        journal.add(**r)


HEAD_AGENT = os.path.join(os.environ.get('W', '/media/roman/383be9ee-c114-4bf8-8956-66b985661cb4/home/remake-linux'),
                          'corsairs-remake', 'tools', 'model3d')
REWARD = 2.0  # score points: the scale of the gains head_auto.py puts into the policy (-20..20)


def to_policy(p, choice):
    """Your choice is a reward of the arms in the policy of head_auto.py / head_agent.py (tool = arm id there, like
    'relax iters=5'; p['parts'] and p['intent'] give the context): winner +REWARD, loser and both_worse -REWARD."""
    import sys
    if not p.get('parts') or choice not in ('a', 'b', 'both_worse'):
        return 0
    sys.path.insert(0, HEAD_AGENT)
    try:
        import head_agent as ha
    except Exception:
        return 0
    path = os.environ.get('HEAD_POLICY', ha.POLICY)
    pol = ha.load_policy(path)
    ck = '|'.join(ha.context(p['parts'], [p['intent']] if p.get('intent') else []))
    n = 0
    for v, r in ((p['a'], REWARD if choice == 'a' else -REWARD), (p['b'], REWARD if choice == 'b' else -REWARD)):
        aid = v.get('tool')
        if choice == 'both_worse':
            r = -REWARD
        if not aid:
            continue
        pol['ctx'].setdefault(ck, {})[aid] = ha.update(pol['ctx'].get(ck, {}).get(aid, [0, 0.]), r)
        for q in p['parts']:
            pol['part'].setdefault(q, {})[aid] = ha.update(pol['part'].get(q, {}).get(aid, [0, 0.]), r)
        pol['arm'][aid] = ha.update(pol['arm'].get(aid, [0, 0.]), r)
        n += 1
    ha.save_policy(pol, path)
    return n


def vlm_hint(pid):
    """The VLM judge (judge.py, Ollama) as a second opinion on the crops: stored in the pair as 'vlm' = 'a'|'b'|None."""
    P = load_pairs()
    p = next(x for x in P if x['id'] == pid)
    try:
        import judge
        w, _ = judge.compare(os.path.join(HERE, p['a']['img']) if not os.path.isabs(p['a']['img']) else p['a']['img'],
                          os.path.join(HERE, p['b']['img']) if not os.path.isabs(p['b']['img']) else p['b']['img'])
        p['vlm'] = {'A': 'a', 'B': 'b'}.get(w)
    except Exception as e:
        p['vlm'] = None
        p['vlm_error'] = str(e)[:120]
    save_pairs(P)
    return p['vlm']


def vote(pid, choice, note='', auto=False):
    if choice not in ('a', 'b', 'same', 'both_worse', 'skip'):
        raise ValueError(choice)
    P = load_pairs()
    p = next(x for x in P if x['id'] == pid)
    p.update(status='auto' if auto else 'done', choice=choice, note=note, voted=time.strftime('%Y-%m-%dT%H:%M:%S'))
    save_pairs(P)
    if choice != 'skip':
        _journal(p, choice, user=not auto)
        if not auto:
            to_policy(p, choice)
    return retrain().acc if not auto else None


def decide(pid):
    """The evaluator picks when it is trained and sure; otherwise the pair stays pending. Returns the choice or None."""
    ev = Evaluator()
    p = next(x for x in load_pairs() if x['id'] == pid)
    if ev.n < MIN_VOTES:
        return None
    pa = ev.prob_a(_feat(p['a'], p.get('box')), _feat(p['b'], p.get('box')))
    if abs(pa - 0.5) < SURE:
        return None
    c = 'a' if pa > 0.5 else 'b'
    vote(pid, c, note=f'auto, P(A)={pa:.2f}', auto=True)
    return c


def stats():
    P = load_pairs()
    ev = Evaluator()
    done = [p for p in P if p['status'] == 'done']
    return {'pairs': len(P), 'pending': sum(p['status'] == 'pending' for p in P), 'voted': len(done),
            'auto': sum(p['status'] == 'auto' for p in P), 'evaluator_votes': ev.n,
            'evaluator_acc': ev.acc, 'weights': dict(zip(NAMES, [round(float(x), 2) for x in ev.w]))}


FOCUS = os.path.join(HERE, 'journal', 'focus.json')


def region_box(name, S=2048, pad=16):
    """UV box (x0,y0,x1,y1 texels) of a named region of template/regions.json (text way of choosing the part)."""
    import bake
    r = json.load(open(os.path.join(HERE, 'template', 'regions.json')))
    k = r['names'].index(name)
    vt, F = bake.read_uv_faces(os.path.join(HERE, 'template', 'head_sub.obj'))
    pts = [(vt[p[1]][0] * S, (1 - vt[p[1]][1]) * S) for f in F if sum(r['vertex'][p[0]] == k for p in f) >= 2 for p in f]
    a = np.array(pts)
    return [int(max(0, a[:, 0].min() - pad)), int(max(0, a[:, 1].min() - pad)),
            int(min(S, a[:, 0].max() + pad)), int(min(S, a[:, 1].max() + pad))]


def get_focus():
    return json.load(open(FOCUS)) if os.path.exists(FOCUS) else None


def set_focus(box, name=''):
    """The part we work on now (image way: dragged on the picture in /review); new pairs take it unless --box/--region."""
    json.dump({'box': box, 'name': name} if box else None, open(FOCUS, 'w'))
