#!/usr/bin/env python3
"""head-wrap-ai: one command line for the whole pipeline after the fit (ours).

headwrap.py status                 which files of the pipeline exist (what to run next)
headwrap.py texture [--from N]     baked27.png -> colormatch -> cleanneck -> padedge -> LaMa seam -> LaMa patches -> padedge -> baked29.png
headwrap.py build                  baked29.png + wrapped20.obj + ponytail + eyes -> work/hero1_eye.glb
headwrap.py game [--model hero]    glb -> the game (pdm_glb2gm.py, head part only) + render views to /tmp/hv_<model>
headwrap.py all                    texture + build + game
Every step is a script of this folder (see docs/plan.md for the why); a step is skipped when its output is newer than its
inputs. Paths: W (default: the remake-linux folder on the HDD), game = $W/corsairs-remake/pdm-game. Needs $W/lama (LaMa)
for the seam steps (see lama_seam.py)."""
import argparse
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
W = os.environ.get('W', os.path.dirname(HERE))
GAME = os.path.join(W, 'corsairs-remake', 'pdm-game')
TOOLS = os.path.join(W, 'corsairs-remake', 'tools')
WK = os.path.join(HERE, 'work')
TPL, REG = 'template/head_sub.obj', 'template/regions.json'
ORIG = os.path.join(GAME, 'data/ai_models/orig/characters/hero.gm')
# rectangles of the bake that LaMa repaints (x0,y0,x1,y1; texels of the 2048 texture): the block under the lip of THIS head
PATCHES = ['1840,1030,1900,1075', '1858,1010,1868,1100']


def run(*a, cwd=HERE):
    print('+', ' '.join(str(x) for x in a), flush=True)
    a = tuple(sys.executable if x == 'python3' else x for x in a)  # no python3 on Windows
    r = subprocess.run([str(x) for x in a], cwd=cwd)
    if r.returncode:
        sys.exit(f'step failed ({r.returncode}): {a[1] if len(a) > 1 else a[0]}')


def w(n):
    return os.path.join('work', n)


def newer(out, *ins):
    o = os.path.join(HERE, out)
    return os.path.exists(o) and all(os.path.getmtime(o) >= os.path.getmtime(os.path.join(HERE, i)) for i in ins
                                     if os.path.exists(os.path.join(HERE, i)))


STEPS = [  # (name, output, inputs, command)
    ('colormatch', 'baked28.png', ['baked27.png', 'ponytail_hair.png'],
     lambda: run('python3', 'colormatch.py', w('baked27.png'), TPL, REG, ORIG, GAME, w('baked28.png'),
                 w('ponytail_hair.png'), w('ponytail_hair28.png'))),
    ('cleanneck', 'baked28n.png', ['baked28.png'],
     lambda: run('python3', 'cleanneck.py', w('baked28.png'), TPL, REG, w('baked28n.png'))),
    ('pad', 'pad28n.png', ['baked28n.png'],
     lambda: run('python3', 'padedge.py', w('baked28n.png'), TPL, w('pad28n.png'), 24)),
    ('lama_seam', 'baked28l.png', ['pad28n.png'],
     lambda: run('python3', 'lama_seam.py', w('pad28n.png'), TPL, REG, w('baked28l.png'))),
    ('lama_patch', 'baked28m.png', ['baked28l.png'],
     lambda: run('python3', 'lama_patch.py', w('baked28l.png'), w('baked28m.png'), *PATCHES)),
    ('neckblur', 'baked28b.png', ['baked28m.png'],
     lambda: run('python3', 'neckblur.py', w('baked28m.png'), TPL, REG, w('baked28b.png'))),
    ('pad_final', 'baked29.png', ['baked28b.png'],
     lambda: run('python3', 'padedge.py', w('baked28b.png'), TPL, w('baked29.png'), 24)),
]


def texture(first=0):
    for name, out, ins, cmd in STEPS[first:]:
        if newer(w(out), *[w(i) for i in ins]) and not first:
            print('skip', name, '(up to date)')
            continue
        cmd()


def build():
    run('python3', 'export.py', w('wrapped20.obj'), TPL, w('baked29.png'), w('hero1_eye.glb'), '--ponytail',
        w('ponytail_tube.obj'), w('ponytail_hair28.png'), '--slit', w('eye_open.json'),
        '../glbcheck/hero1_head_front.png', '../glbcheck/hv4/auto.glb', '--eyes-json',
        os.environ.get('EYES_JSON', '../corsairs-remake/tools/eyes_ai.json'), 'ai_hero_head_1,ai_hero1_head_1')
    # offline gate: the eyes are scored from the meshes (eye_score.py), a table is printed, a low score is a warning
    r = subprocess.run([sys.executable, 'eye_score.py', w('hero1_eye.glb'), w('eye_open.json')], cwd=HERE)
    if r.returncode:
        print('WARNING: eye_score reports failed checks (see the table above)')
    # the whole head surface: shards and stretched texture (mesh_score.py), a picture of the flagged triangles
    r = subprocess.run([sys.executable, 'mesh_score.py', w('hero1_eye.glb'), '--png', w('mesh_score.png')], cwd=HERE)
    if r.returncode:
        print('WARNING: mesh_score reports failed checks (see work/mesh_score.png)')


def game(model):
    glb = os.path.join(GAME, 'data/ai_models/glb_wrap')
    for n in ('hero1', 'hero'):
        run('cp', w('hero1_eye.glb'), os.path.join(glb, f'{n}_head.glb'))
    run('python3', 'tools/pdm_glb2gm.py', 'pdm-game', model, '--glb', 'pdm-game/data/ai_models/glb_wrap', '--parts',
        '--only-parts', 'head', cwd=os.path.join(W, 'corsairs-remake'))
    run('python3', 'tools/pdm_model_views.py', 'pdm-game', model, '--out', f'/tmp/hv_{model}', '--size', '3072',
        cwd=os.path.join(W, 'corsairs-remake'))


def status():
    files = ['baked27.png', 'ponytail_hair.png', 'wrapped20.obj', 'ponytail_tube.obj', 'eye_open.json'] + \
            [s[1] for s in STEPS] + ['ponytail_hair28.png', 'hero1_eye.glb']
    for f in files:
        print(('ok   ' if os.path.exists(os.path.join(WK, f)) else 'MISS ') + f)
    print('lama:', 'ok' if os.path.exists(os.path.join(W, 'lama', 'big-lama.pt')) else 'MISS (see lama_seam.py)')
    print('game:', GAME, 'ok' if os.path.isdir(GAME) else 'MISS')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cmd', choices=['status', 'texture', 'build', 'game', 'all'])
    ap.add_argument('--from', dest='first', type=int, default=0, help='texture: first step number (0..7), always runs')
    ap.add_argument('--model', default='hero')
    a = ap.parse_args()
    if a.cmd == 'status':
        status()
    if a.cmd in ('texture', 'all'):
        texture(a.first)
    if a.cmd in ('build', 'all'):
        build()
    if a.cmd in ('game', 'all'):
        game(a.model)


if __name__ == '__main__':
    main()
