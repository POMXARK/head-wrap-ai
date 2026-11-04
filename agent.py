#!/usr/bin/env python3
"""Stage 7: the agent that learns from the journal. agent.py propose <problem> [--top 3] | agent.py table
The arms are (tool, params) from CATALOG: what can be tried for a problem. Every journal record of the same problem, tool
and params is a pull: better +1, partial +0.4, same 0, worse -1, deadend -1.5 (unknown is skipped). The score of an arm is
the mean reward + an exploration bonus c / sqrt(pulls + 1) (UCB), untried arms get the maximum bonus, so the agent
tries what was never tried first and does not return to dead ends. A tool of the same problem that was a dead end with
other params still counts a little (tool level mean, weight 0.3). The agent only proposes: the command line of the arm is
printed, the result goes back through journal.py add (the loop of stage 7). The user's verdict (`journal.py add --verdict`)
is a pull too: that is the training signal of "the eye is concave"."""
import argparse
import json
import math
import os
import sys
from collections import defaultdict

import journal

REWARD = {'better': 1.0, 'partial': 0.4, 'same': 0.0, 'worse': -1.0, 'deadend': -1.5}
C = 0.8
# problem -> [(tool, params, command template)]
CATALOG = {
    'eye_disc': [
        ('wrap_fit.py', {'FLAT': 1.0}, 'edit FLAT in wrap_fit.py; wrap_fit + bake + render'),
        ('eye_slit.py', {'mode': 'open_slit'}, 'open the eye slit along the lid landmarks and show the eyeball (to write)'),
        ('eye_iris.py', {'mode': 'iris_on_ball'}, 'iris texture on the eyeball from the front view (to write)'),
        ('inpaint.py', {'region': 'eye', 'model': 'comfyui'}, 'ComfyUI inpainting of the eye texels (to write)'),
    ],
    'chin_spot': [
        ('bake.py', {'HAIR_V': 0.30, 'SKIN_ON_HAIR': 0.1}, 'colour segmentation of views'),
        ('beard_mask.py', {'mode': 'saturation'}, 'beard mask by saturation/colour (to write)'),
        ('inpaint.py', {'region': 'chin', 'model': 'comfyui'}, 'inpainting under the chin (to write)'),
    ],
    'ponytail': [
        ('ponytail.py', {'mode': 'tube', 'scale': 0.65}, 'clean tube'),
        ('ponytail.py', {'mode': 'curl_tip'}, 'curl the tip back as in the Qwen left view (to write)'),
        ('ponytail.py', {'mode': 'strand_texture_from_view'}, 'strand texture from the back/left view (to write)'),
        ('ponytail.py', {'mode': 'band'}, 'hair band at the root (to write)'),
    ],
    'judge': [
        ('judge.py', {'model': 'ministral-3:14b', 'mode': 'AB'}, 'A/B with VLM'),
        ('judge.py', {'model': 'ministral-3:14b', 'mode': 'metric_only'}, 'distance, silhouette IoU, no VLM (to write)'),
        ('judge.py', {'model': 'qwen3:32b', 'mode': 'score_one'}, 'one plan, calibrated score, other model (to write)'),
    ],
    'chin_line': [
        ('fillgaps.py', {}, 'fill pure-black texels (cracks)'),
        ('seamblend.py', {}, 'blend colour across UV seams'),
        ('lip_mesh_check.py', {}, 'cut parts of the lips mesh out of the render one by one (to write)'),
    ],
}


def key(tool, params):
    return tool + ' ' + json.dumps(params, sort_keys=True)


def stats(path=journal.PATH):
    arm, tool = defaultdict(list), defaultdict(list)
    for l in open(path):
        r = json.loads(l)
        v = REWARD.get(r.get('verdict'))
        u = REWARD.get(r.get('user_verdict'))
        if (v is None and u is None) or not r.get('problem') or not r.get('tool'):
            continue
        # the user's verdict counts twice and replaces the automatic one
        vals = [u, u] if u is not None else [v]
        arm[(r['problem'], key(r['tool'], r.get('params', {})))].extend(vals)
        tool[(r['problem'], r['tool'])].extend(vals)
    return arm, tool


def score(problem, tool, params, arm, tool_stats):
    pulls = arm.get((problem, key(tool, params)), [])
    mean = sum(pulls) / len(pulls) if pulls else 0.0
    t = tool_stats.get((problem, tool), [])
    prior = 0.3 * (sum(t) / len(t)) if t and not pulls else 0.0
    return mean + prior + C / math.sqrt(len(pulls) + 1), len(pulls)


def propose(problem, top=3):
    arm, tool = stats()
    rows = []
    for t, p, cmd in CATALOG[problem]:
        s, n = score(problem, t, p, arm, tool)
        rows.append((s, n, t, p, cmd))
    return sorted(rows, key=lambda x: -x[0])[:top]


def main():
    ap = argparse.ArgumentParser(usage=__doc__)
    ap.add_argument('cmd', choices=['propose', 'table'])
    ap.add_argument('problem', nargs='?')
    ap.add_argument('--top', type=int, default=3)
    a = ap.parse_args()
    if a.cmd == 'table':
        arm, _ = stats()
        for (p, k), v in sorted(arm.items()):
            print(f'{p:12} n={len(v)} mean={sum(v) / len(v):+.2f}  {k}')
        return
    if a.problem not in CATALOG:
        sys.exit('problems: ' + ', '.join(CATALOG))
    for s, n, t, p, cmd in propose(a.problem, a.top):
        print(f'{s:+.2f} (pulls {n})  {t} {json.dumps(p)}  -- {cmd}')


if __name__ == '__main__':
    main()
