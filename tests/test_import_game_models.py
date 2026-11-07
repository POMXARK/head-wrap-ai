"""Import of a head from a game model folder (own test): the folder is listed, parts are read, replace_job finishes, dialog holds all 3 steps.
Runs its own server from a temporary copy so the real work/ and journal stay untouched."""
import json, os, shutil, subprocess, sys, tempfile, time, urllib.request
H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
e = open(os.path.join(H, 'edit.html'), encoding='utf-8').read()
d = e[e.index('<dialog id="dlg"'):e.index('</dialog>')]
for i in ('ifile', 'dn', 'dpart', 'sc', 'brp', 'prog', 'rrep'):
    assert 'id="%s"' % i in d, 'dialog lacks ' + i
tmp = tempfile.mkdtemp()
try:
    for n in os.listdir(H):
        p = os.path.join(H, n)
        if n in ('work', 'journal', '.git', '__pycache__', 'models'): continue
        (shutil.copytree if os.path.isdir(p) else shutil.copy)(p, os.path.join(tmp, n))
    os.makedirs(tmp + '/work'); os.makedirs(tmp + '/journal'); os.makedirs(tmp + '/gm/corsairs-remake/chars_rig/models')
    for f in ('baked.png', 'hero1_eye.glb', 'eye_open.json'): shutil.copy(os.path.join(H, 'work', f), tmp + '/work/')
    shutil.copy(os.path.join(H, 'work', 'hero1_eye.glb'), tmp + '/gm/corsairs-remake/chars_rig/models/admiral.glb')
    env = dict(os.environ, HEADWRAP_MODELS=tmp + '/gm/corsairs-remake/chars_rig/models')
    pr = subprocess.Popen([sys.executable, 'app.py', '--port', '8784'], cwd=tmp, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(3)
    u = 'http://localhost:8784/api/edit/'
    get = lambda p: json.load(urllib.request.urlopen(u + p, timeout=60))
    post = lambda p, x: json.load(urllib.request.urlopen(urllib.request.Request(u + p, json.dumps(x).encode()), timeout=60))
    src = get('state')['sources']
    ids = [x['id'] for x in src]
    assert 'ext:0:admiral.glb' in ids, ids
    parts = get('parts?src=ext:0:admiral.glb')['parts']; assert parts, parts
    big = max(parts, key=lambda p: p['vertices'])['name']
    r = post('replace_job', {'donor': 'ext:0:admiral.glb', 'part': big, 'scale': 'match_ring'}); assert 'job' in r, r
    t = time.time()
    while time.time() - t < 240:
        j = get('job?id=' + r['job'])
        if j['status'] != 'running': break
        time.sleep(1)
    assert j['status'] == 'done', j
    assert get('state')['ops'][-1]['op'], 'no op logged'
    print('OK test_import_game_models, %.0fs' % (time.time() - t))
finally:
    try: pr.terminate()
    except Exception: pass
    shutil.rmtree(tmp, ignore_errors=True)
