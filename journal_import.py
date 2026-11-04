#!/usr/bin/env python3
"""Backfill journal/steps.jsonl from the git history of corsairs-remake: every commit on the way from the Qwen views to
the generated head (tools/model3d, view projection, ComfyUI graphs). The commit is the action, its subject the note;
the verdict is not known from a commit, so it is "unknown" (a revert is "deadend"). Run once: journal_import.py [repo]"""
import json
import os
import subprocess
import sys

import journal

PATHS = ['tools/model3d', 'docs/head-model-fix.md', 'tools/pdm_project_views.py', 'tools/pdm_comfy_refine_graph.py',
         'tools/comfy_view_refine.py', 'tools/pdm_model_views.py', 'tools/pdm_models_all.py']
# (keyword in the subject, phase, problem); the first match wins
RULES = [('revert', 'revert', 'undo'), ('qwen refine', 'qwen-views', 'views'), ('qwen image', 'qwen-views', 'views'), ('qwen', 'qwen-views', 'views'),
         ('despill', 'views-prep', 'views'), ('align', 'views-prep', 'views'), ('green', 'views-prep', 'views'),
         ('pixal3d', 'model-generation', 'model'), ('graph', 'model-generation', 'model'), ('workflow', 'model-generation', 'model'),
         ('remesh', 'solid-mesh', 'double_surface'), ('solid', 'solid-mesh', 'double_surface'), ('hollow', 'solid-mesh', 'double_surface'),
         ('3dcoat', 'uv', 'uv'), ('unwrap', 'uv', 'uv'), ('uv', 'uv', 'uv'), ('seam', 'uv', 'uv'),
         ('project', 'texture-projection', 'texture'), ('view', 'texture-projection', 'texture'), ('tone', 'texture-projection', 'texture'),
         ('texture', 'texture-projection', 'texture'), ('numba', 'texture-projection', 'texture'),
         ('twelve', 'twelve-view-check', 'shape'), ('autonomous', 'twelve-view-check', 'shape'),
         ('head check', 'checker-agent', 'defects'), ('agent', 'checker-agent', 'defects'), ('gui', 'checker-agent', 'defects'),
         ('docs', 'docs', 'docs'), ('chore', 'notes', 'notes')]


def classify(subject):
    s = subject.lower()
    for k, phase, problem in RULES:
        if k in s:
            return phase, problem
    return 'other', 'other'


def main():
    repo = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'corsairs-remake')
    out = subprocess.check_output(['git', '-C', repo, 'log', '--reverse', '--date=format:%Y-%m-%dT%H:%M:%S',
                                   '--format=%ad\t%h\t%s', '--'] + PATHS, text=True)
    seen = {json.loads(l).get('commit') for l in open(journal.PATH)} if os.path.exists(journal.PATH) else set()
    n = 0
    for line in out.splitlines():
        ts, h, subj = line.split('\t', 2)
        if h in seen:
            continue
        phase, problem = classify(subj)
        journal.add(ts=ts, stage=0, phase=phase, problem=problem, tool='corsairs-remake', params={}, metrics={}, image=None,
                    verdict='deadend' if phase == 'revert' else 'unknown', note=subj, commit=h)
        n += 1
    print('imported', n)


if __name__ == '__main__':
    main()
