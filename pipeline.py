#!/usr/bin/env python3
"""The pipeline page of the head-wrap-ai panel (ours): buttons for the steps of headwrap.py, the live log of the running
step, the eye score table (eye_score.py) with its render, and the 3D view of the built head (model-viewer from a CDN,
the page works without it). One step runs at a time; the logic stays in headwrap.py / eye_score.py (this is a thin shell).
Works the same on Windows and Linux (sys.executable, no shell)."""
import json
import os
import subprocess
import sys
import threading
import shutil
import time

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(HERE, 'work')
STEPS = {
    'status': ['headwrap.py', 'status'],
    'texture': ['headwrap.py', 'texture'],
    'build': ['headwrap.py', 'build'],
    'game': ['headwrap.py', 'game'],
    'all': ['headwrap.py', 'all'],
    'mesh': ['mesh_score.py', 'work/hero1_eye.glb', '--png', 'work/mesh_score.png', '--json', 'work/mesh_score.json'],
    'eyes': ['eye_score.py', 'work/hero1_eye.glb', 'work/eye_open.json', '--png', 'work/eye_score.png', '--json',
             'work/eye_score.json'],
}
STATE = {'running': None, 'lines': [], 'rc': None}
LOCK = threading.Lock()


def run(step, model='hero1'):
    """Start a step in the background; returns an error text or None."""
    if step not in STEPS:
        return 'unknown step'
    with LOCK:
        if STATE['running']:
            return 'busy: ' + STATE['running']
        STATE.update(running=step, lines=[], rc=None)
    cmd = [sys.executable, '-u'] + STEPS[step]
    if step == 'game':
        cmd += ['--model', model if model in ('hero', 'hero1') else 'hero1']

    def work():
        try:
            p = subprocess.Popen(cmd, cwd=HERE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                 encoding='utf-8', errors='replace')
            for line in p.stdout:
                STATE['lines'].append(line.rstrip())
                del STATE['lines'][:-400]
            STATE['rc'] = p.wait()
        except Exception as e:  # noqa: BLE001
            STATE['lines'].append('error: %s' % e)
            STATE['rc'] = -1
        STATE['running'] = None

    threading.Thread(target=work, daemon=True).start()
    return None


def variants():
    d = os.path.join(WORK, 'variants')
    out = []
    for f in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        if f.endswith('.glb'):
            try:
                info = json.load(open(os.path.join(d, f[:-4] + '.json')))
            except (OSError, ValueError):
                info = {}
            out.append({'name': f[:-4], 'eye': info.get('eye'), 'mesh': info.get('mesh'), 'options': info.get('options', {})})
    return out


def _score(cmd, out):
    p = os.path.join(WORK, out)
    try:
        subprocess.run([sys.executable] + cmd + ['--json', 'work/' + out], cwd=HERE, capture_output=True, timeout=120)
        return json.load(open(p)).get('score')
    except Exception:  # noqa: BLE001
        return None


def save_variant(name):
    """Copy the built head under a name with the options and both scores: compare several, side by side in 3D."""
    import re
    import options
    name = re.sub(r'[^0-9A-Za-zА-Яа-я_-]+', '_', name or '').strip('_') or time.strftime('%H%M%S')
    src = os.path.join(WORK, 'hero1_eye.glb')
    if not os.path.exists(src):
        return None, 'сначала соберите голову'
    d = os.path.join(WORK, 'variants')
    os.makedirs(d, exist_ok=True)
    shutil.copy(src, os.path.join(d, name + '.glb'))
    info = {'options': options.load(),
            'eye': _score(['eye_score.py', 'work/variants/%s.glb' % name, 'work/eye_open.json'], 'var_eye.json'),
            'mesh': _score(['mesh_score.py', 'work/variants/%s.glb' % name], 'var_mesh.json')}
    json.dump(info, open(os.path.join(d, name + '.json'), 'w'), indent=1)
    return name, None


def stale_reason(score_file, inputs=('hero1_eye.glb', 'options.json'), work=None):
    """why a score file is out of date (ours, B3.3): None if fresh, else a text; inputs are names in work/ whose mtime is newer"""
    work = work or WORK
    f = os.path.join(work, score_file)
    if not os.path.exists(f):
        return 'нет оценки'
    t = os.path.getmtime(f)
    names = {'hero1_eye.glb': 'модель пересобрана после оценки', 'options.json': 'настройки изменены после оценки'}
    for n in inputs:
        q = os.path.join(work, n)
        if os.path.exists(q) and os.path.getmtime(q) > t + 1e-6:
            return names.get(n, n + ' новее оценки')
    return None


def state():
    out = {'running': STATE['running'], 'rc': STATE['rc'], 'lines': STATE['lines'][-200:]}
    try:
        out['eyes'] = json.load(open(os.path.join(WORK, 'eye_score.json')))
    except (OSError, ValueError):
        out['eyes'] = None
    out['eyes_stale'] = stale_reason('eye_score.json') if out['eyes'] else None
    out['glb'] = 'work/hero1_eye.glb' if os.path.exists(os.path.join(WORK, 'hero1_eye.glb')) else None
    out['variants'] = variants()
    out['has_png'] = os.path.exists(os.path.join(WORK, 'eye_score.png'))
    return out


PAGE = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pipeline.html'), encoding='utf-8').read()
