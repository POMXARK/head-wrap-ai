"""State and handlers of the editing API (ours, task B1): one Asset in memory (the template head), selections, ops, undo.
Functions take/return JSON-able dicts; app.py only routes. Selection 'draft' is the one being painted."""
import json
import os
import threading
import time
import numpy as np
import replace_part as RP
from asset import Asset
from selection import Selection, load_obj

HERE = os.path.dirname(os.path.abspath(__file__))
LOCK = threading.Lock()
A = None
SESSION = __import__('uuid').uuid4().hex[:6]
_IDS, _REDO_IDS = [], []      # edit_log ids parallel to the undo stack of A (None for ops that are not logged)
DRAFT = None
REG = json.load(open(os.path.join(HERE, 'template/regions.json')))


def _init():
    global A, DRAFT
    if A is None:
        m = load_obj(os.path.join(HERE, 'template/head_sub.obj'))
        A = Asset('head_template')
        A.add_part('head', m.V, m.F)
        DRAFT = Selection(A.parts['head'])
        A.add_part('body', *_mannequin(m))


def _body_visible():
    """the mannequin is shown unless the last replace_part opened a model as is (scale 'open')"""
    last = [r for r in A.log if r['op'] == 'replace_part']
    return not (last and last[-1]['params'].get('scale') == 'open')


def _body():
    if _body_visible():
        b = A.parts['body']
        return b.V, b.F
    return np.zeros((0, 3)), np.zeros((0, 3), int)


def _mannequin(head):
    """a simple body (ours, a stand-in until a real torso asset exists): a tube under the neck ring of the template head,
    its top ring IS the neck ring, widening to shoulders"""
    ring = RP.ring_of(head.V, head.F)
    P = head.V[ring]
    c = P.mean(0)
    n = len(ring)
    rings = []
    prof = [(0.0, 1.0), (0.6, 1.5), (1.6, 3.2), (3.0, 3.8), (6.0, 3.4), (9.0, 3.2)]
    for dy, k in prof:
        Q = c + (P - c) * k
        Q[:, 1] = P[:, 1] - dy
        rings.append(Q)
    V = np.vstack(rings)
    F = []
    for r in range(len(prof) - 1):
        for i in range(n):
            a, b = r * n + i, r * n + (i + 1) % n
            F += [[a, a + n, b], [b, a + n, b + n]]
    return V, np.array(F)


DONORS = {'template': 'шаблон головы (вернуть исходную)', 'hero1': 'голова hero1 (work/hero1_head2.glb)'}


GAME_GM = os.path.join(os.environ.get('W', os.path.dirname(HERE)), 'corsairs-remake', 'pdm-game', 'data/ai_models/orig/characters')
GAME_DIR = os.path.join(os.environ.get('W', os.path.dirname(HERE)), 'corsairs-remake')
EXT = ('.glb', '.gltf', '.obj')


def model_dirs():
    """folders with ready GLB models of the game (corsairs-remake/chars_rig/models): HEADWRAP_MODELS (os.pathsep list) + usual places"""
    c = [d for d in os.environ.get('HEADWRAP_MODELS', '').split(os.pathsep) if d]
    for base in (os.path.dirname(HERE), os.path.expanduser('~'), 'C:\\', os.path.join(os.environ.get('W', ''), '')):
        if base:
            c.append(os.path.join(base, 'corsairs-remake', 'chars_rig', 'models'))
    out = []
    for d in c:
        d = os.path.realpath(d)
        if os.path.isdir(d) and d not in out:
            out.append(d)
    return out


def sources():
    """what a head can be imported from: the template, model files of this folder (work/, models/), game models (.gm)"""
    import glob
    out = [{'id': 'template', 'label': 'шаблон головы (вернуть исходную)'}]
    for d in ('work', 'work/imported', 'models'):
        for f in sorted(glob.glob(os.path.join(HERE, d, '*'))):
            if f.lower().endswith(EXT):
                out.append({'id': 'file:' + os.path.relpath(f, HERE), 'label': os.path.relpath(f, HERE)})
    for i, d in enumerate(model_dirs()):
        for f in sorted(glob.glob(os.path.join(d, '*.glb'))):
            out.append({'id': 'ext:%d:%s' % (i, os.path.basename(f)), 'label': 'игра: ' + os.path.basename(f)})
    for f in sorted(glob.glob(os.path.join(GAME_GM, '*.gm'))):
        n = os.path.basename(f)[:-3]
        out.append({'id': 'gm:' + n, 'label': 'из игры: %s.gm' % n})
    return out


def _gm_to_glb(name):
    """a game model (.gm) as a GLB in work/imported/ with the game's own converter (tools/pdm_gm2glb.py); returns the path relative to this folder"""
    import re
    import subprocess
    import sys
    if not re.fullmatch(r'[\w.-]+', name) or not os.path.isfile(os.path.join(GAME_GM, name + '.gm')):
        raise ValueError('нет такой модели игры: ' + name)
    rel = 'work/imported/%s.glb' % name
    out = os.path.join(HERE, rel)
    if not os.path.exists(out):
        os.makedirs(os.path.dirname(out), exist_ok=True)
        r = subprocess.run([sys.executable, 'tools/pdm_gm2glb.py', 'pdm-game', name, '--out', out, '--no-rig'], cwd=GAME_DIR,
                           capture_output=True, text=True, timeout=300)
        if r.returncode or not os.path.exists(out):
            raise ValueError('конвертер .gm не отработал: ' + (r.stderr or r.stdout)[-300:])
    return rel


def _resolve(name):
    """donor id -> (path of a model file | None for the template)"""
    if name == 'template':
        return None
    if name == 'hero1':
        return 'work/hero1_head2.glb'
    if name.startswith('gm:'):
        return _gm_to_glb(name[3:])
    if name.startswith('ext:'):  # a game model from a model folder: copy into work/imported/ (the project reads only its own folder)
        import re
        import shutil
        _, i, base = name.split(':', 2)
        dirs = model_dirs()
        if not i.isdigit() or int(i) >= len(dirs) or not re.fullmatch(r'[\w.-]+\.glb', base):
            raise ValueError('нет такой модели: ' + name)
        src = os.path.join(dirs[int(i)], base)
        if not os.path.isfile(src):
            raise ValueError('нет такой модели: ' + name)
        rel = 'work/imported/' + base
        os.makedirs(os.path.join(HERE, 'work', 'imported'), exist_ok=True)
        if not os.path.exists(os.path.join(HERE, rel)):
            shutil.copy(src, os.path.join(HERE, rel))
        return rel
    if name.startswith('file:'):
        f = os.path.realpath(os.path.join(HERE, name[5:]))
        if not f.startswith(HERE + os.sep) or not f.lower().endswith(EXT) or not os.path.isfile(f):
            raise ValueError('файл недоступен: ' + name)
        return os.path.relpath(f, HERE)
    raise ValueError('unknown donor ' + name)


def _geoms(path):
    """name -> mesh of a donor file with the node transforms applied (game GLBs keep scale/rotation in nodes)"""
    import trimesh
    sc = trimesh.load(path, force='scene')
    out = {}
    for node in sc.graph.nodes_geometry:
        T, gname = sc.graph[node]
        m = sc.geometry[gname].copy()
        m.apply_transform(T)
        out.setdefault(gname, m)
    for k, v in sc.geometry.items():
        out.setdefault(k, v)
    return out


ALL = '__all__'      # the whole file as one donor: every part merged


def donor_parts(name):
    """[{name, vertices}] of the meshes inside a donor file (the user picks the head among them)"""
    import trimesh
    rel = _resolve(name)
    if rel is None:
        return [{'name': 'head', 'vertices': len(A.parts['head'].V) if A else 0}]
    g = _geoms(os.path.join(HERE, rel))
    out = []
    if len(g) > 1:
        out.append({'name': ALL, 'vertices': int(sum(len(v.vertices) for v in g.values())), 'ok': True,
                    'label': '★ Вся модель (%d частей, текстуры в одном атласе)' % len(g)})
    for k, v in g.items():
        ok = False
        if len(v.vertices) >= 30:
            try:
                _donor_ring(*_donor(name, k)[:2])
                ok = True
            except Exception:
                pass
        out.append({'name': k, 'vertices': int(len(v.vertices)), 'ok': ok})
    return out


def _donor_ring(dV, dF):
    """the neck hole of a donor head (opens a closed head at the bottom if needed); ValueError if there is none"""
    try:
        dV, dF, _, _ = open_neck(dV, dF, None)
        loops = RP.boundary_loops(dF)
    except ValueError:
        loops = []
    if not loops:
        raise ValueError('в этой части нет головы с отверстием шеи (это волосы, одежда или деталь). Выберите в списке часть, помеченную «подходит»')
    return max(loops, key=len)


def _merge_all(ms):
    """every part of a file as one mesh with ONE texture: part textures go into a grid atlas (the editor holds one texture);
    a part without texture gets a flat cell of its colour. Returns (V, F, uvinfo)"""
    from PIL import Image
    n = len(ms)
    cols = int(np.ceil(np.sqrt(n)))
    rows = int(np.ceil(n / cols))
    cell = 1024 if n <= 4 else 512
    atlas = Image.new('RGB', (cols * cell, rows * cell), (200, 200, 200))
    Vs, Fs, vts, Ts, o, ov = [], [], [], [], 0, 0
    for i, m in enumerate(ms):
        c, r = i % cols, i // cols
        mat = getattr(m.visual, 'material', None)
        img = getattr(mat, 'baseColorTexture', None) or getattr(mat, 'image', None)
        uv = getattr(m.visual, 'uv', None)
        box = (c * cell, (rows - 1 - r) * cell)
        if uv is not None and len(uv) == len(m.vertices) and img is not None:
            atlas.paste(img.convert('RGB').resize((cell, cell)), box)
            u = np.asarray(uv, float)
            if u.min() < 0 or u.max() > 1:
                u = np.mod(u, 1.0)
        else:
            col = (200, 200, 200)
            try:
                col = tuple(int(x) for x in mat.main_color[:3])
            except Exception:
                pass
            atlas.paste(Image.new('RGB', (cell, cell), col), box)
            u = np.full((len(m.vertices), 2), 0.5)
        vts.append(np.c_[(c + u[:, 0]) / cols, (r + u[:, 1]) / rows])
        Vs.append(np.asarray(m.vertices, float))
        f = np.asarray(m.faces, int)
        Fs.append(f + o)
        Ts.append(f + o)
        o += len(m.vertices)
    V, inv = np.unique(np.vstack(Vs).round(6), axis=0, return_inverse=True)
    F = np.vstack(Fs)
    return V, inv.ravel()[F], {'vt': np.vstack(vts), 'T': np.vstack(Ts), 'img': atlas}


def _donor(name, part=None):
    rel = _resolve(name)
    if rel is None:
        import texture
        m = load_obj(os.path.join(HERE, 'template/head_sub.obj'))
        vt, T, tex = texture.template_uv()
        return m.V, m.F, {'vt': vt, 'T': T, 'img': tex}
    import trimesh
    geoms = _geoms(os.path.join(HERE, rel))
    if part == ALL and len(geoms) > 1:     # all parts in one mesh; their textures are packed into one atlas, UV remapped
        return _merge_all(list(geoms.values()))
    g = geoms[part] if part in geoms else (geoms['geometry_0'] if name == 'hero1' else max(geoms.values(), key=lambda x: len(x.vertices)))
    V, inv = np.unique(g.vertices.round(6), axis=0, return_inverse=True)
    uv = getattr(g.visual, 'uv', None)
    info = None
    if uv is not None and len(uv) == len(g.vertices):
        mat = getattr(g.visual, 'material', None)
        img = getattr(mat, 'baseColorTexture', None) or getattr(mat, 'image', None)
        info = {'vt': np.asarray(uv, float), 'T': np.asarray(g.faces, int), 'img': img}
    return V, inv.ravel()[g.faces], info


def part_mesh(src, part):
    """a donor part for the preview before import: {v, f, size}; nothing is changed, big meshes are thinned to ~40k faces"""
    V, F, _ = _donor(src, part or None)
    V = np.asarray(V, float)
    F = np.asarray(F, int)
    if len(F) > 40000:
        try:
            import fast_simplification
            V, F = fast_simplification.simplify(V, F.astype(np.int32), target_reduction=1 - 40000 / len(F))
        except Exception:
            F = F[::max(1, len(F) // 40000)]
    used = np.unique(F)
    remap = np.full(len(V), -1)
    remap[used] = np.arange(len(used))
    V, F = V[used], remap[F]
    ext = V.max(0) - V.min(0)
    return {'v': np.round(V - (V.max(0) + V.min(0)) / 2, 4).ravel().tolist(), 'f': F.ravel().tolist(), 'size': [round(float(x), 3) for x in ext],
            'faces': int(len(F))}


def save_upload(name, data):
    """a model file picked by the user, into models/ (the library)"""
    import re
    base = re.sub(r'[^\w.-]+', '_', os.path.basename(name or 'upload.glb'))
    if not base.lower().endswith(EXT):
        raise ValueError('нужен файл .glb, .gltf или .obj')
    if len(data) > 64 << 20:
        raise ValueError('файл больше 64 МБ')
    os.makedirs(os.path.join(HERE, 'models'), exist_ok=True)
    with open(os.path.join(HERE, 'models', base), 'wb') as f:
        f.write(data)
    return {'id': 'file:models/' + base}


def export_bytes(fmt, body=False):
    """(bytes, content type, file name) of the current head: glb | obj | png; with the edited texture and UV while they exist"""
    _init()
    import texture
    h = A.parts['head']
    if fmt == 'png':
        return texture.png(h), 'image/png', 'head_texture.png'
    uvok = texture.available(h)
    if fmt == 'obj':
        plain = ('\n'.join('v %.5f %.5f %.5f' % tuple(v) for v in h.V) + '\n' +
                 '\n'.join('f %d %d %d' % (a + 1, b + 1, c + 1) for a, b, c in h.F) + '\n').encode()
        return (texture.obj_text(h) if uvok else plain), 'text/plain', 'head_edit.obj'
    if fmt != 'glb':
        raise ValueError('unknown format ' + fmt)
    import trimesh
    sc = trimesh.Scene()
    if uvok:
        S = texture.state_of(h)
        mh = trimesh.Trimesh(h.V[S['F']].reshape(-1, 3), np.arange(3 * len(S['F'])).reshape(-1, 3), process=False)
        mh.visual = trimesh.visual.TextureVisuals(uv=S['vt'][S['T']].reshape(-1, 2), material=trimesh.visual.material.PBRMaterial(
            baseColorTexture=texture.pil(h)))
    else:
        mh = trimesh.Trimesh(h.V, h.F, process=False)
    sc.add_geometry(mh, node_name='head', geom_name='head')
    if body and _body_visible():
        b = A.parts['body']
        sc.add_geometry(trimesh.Trimesh(b.V, b.F, process=False), node_name='body', geom_name='body')
    return sc.export(file_type='glb'), 'model/gltf-binary', 'head_edit.glb'


def _slice_open(dV, dF, cut):
    """geometry cut by the plane y=cut (keeps the part above, leaves an open edge along the cut); UV is dropped"""
    import trimesh
    m = trimesh.Trimesh(dV, dF, process=False)
    m = m.slice_plane([0, cut, 0], [0, 1, 0], cap=False)
    if len(m.faces) < 3:
        return None
    m.merge_vertices()
    m.remove_unreferenced_vertices()
    return np.asarray(m.vertices, float), np.asarray(m.faces, int)


def open_neck(dV, dF, uvinfo, frac=0.12):
    """any model can be a donor head. No neck opening (closed head, scan, loose pieces)? cut it off at the bottom (ours):
    first dropping faces (UV stays valid), then by a real plane cut (UV lost). Returns (V, F, uvinfo, cut_y or None)."""
    if RP.boundary_loops(dF):
        return dV, dF, uvinfo, None
    y = dV[:, 1]
    lo, h = float(y.min()), float(y.max() - y.min())
    for fr in (frac, 0.2, 0.3):
        cut = lo + fr * h
        keep = dV[dF][:, :, 1].mean(1) >= cut
        if keep.sum() < 3:
            continue
        nF = dF[keep]
        used = np.unique(nF)
        remap = np.full(len(dV), -1)
        remap[used] = np.arange(len(used))
        nV, nF = dV[used], remap[nF]
        if RP.boundary_loops(nF):
            if uvinfo is not None:
                uvinfo = dict(uvinfo, T=np.asarray(uvinfo['T'])[keep])
            return nV, nF, uvinfo, cut
    for fr in (frac, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7):
        r = _slice_open(dV, dF, lo + fr * h)
        if r is not None and RP.boundary_loops(r[1]):
            return r[0], r[1], None, lo + fr * h
    raise ValueError('не удалось получить отверстие шеи: в модели нет подходящей поверхности')


def replace_prepare(d, step=lambda msg, frac: None):
    """the heavy part of replace_head: builds the new head mesh without touching the asset; step() may raise Cancelled"""
    _init()
    slow = float(os.environ.get('HW_SLOW_STEP', 0))     # debug: pause per step, to watch progress/cancel in the UI

    def step(msg, frac, _s=step):
        _s(msg, frac)
        time.sleep(slow)
    step('читаю донора', 0.1)
    dV, dF, uvinfo = _donor(d['donor'], d.get('part'))
    if d.get('scale') == 'open':      # show the model in the editor as it is: no mannequin, no neck, nothing is cut or scaled
        uv = {'vt': uvinfo['vt'], 'T': uvinfo['T'], 'img': uvinfo['img']} if uvinfo is not None else None
        return {'hV': dV, 'hF': dF, 'rep': {'ring_gap': 0.0, 'scale': 1.0}, 'd': d, 'seam': 'none', 'uv': uv}
    dV, dF, uvinfo, cut = open_neck(dV, dF, uvinfo)
    body = A.parts['body']
    step('ищу кольца розетки', 0.35)
    bl = RP.boundary_loops(body.F)
    t_ring = max(bl, key=lambda l: body.V[l][:, 1].mean())
    d_ring = _donor_ring(dV, dF)
    step('совмещаю голову с шеей', 0.55)
    V, F, rep = RP.replace(body.V, body.F, t_ring, dV, dF, d_ring, d.get('scale', 'match_ring'), outward=[0, 1, 0])
    off = rep['donor_offset']
    seam = d.get('seam', 'bridge')
    hV, hF = V[off:], F[len(body.F):] - off
    if seam == 'bridge':
        step('сшиваю шов', 0.8)
        # copies of the body ring join the head part; the strip runs from the donor ring to them
        ring_copy = np.arange(len(hV), len(hV) + len(t_ring))
        hV = np.vstack([hV, body.V[t_ring]])
        strip, stretch = RP.bridge(hV, d_ring, ring_copy)
        hF = np.vstack([hF, strip])
        rep['seam_stretch'] = round(stretch, 3)
    if cut is not None:
        rep['neck_cut'] = 1
    step('готово к применению', 0.95)
    uv = None
    if uvinfo is not None and np.array_equal(hF[:len(dF)], dF):    # donor faces keep their order; the bridge strip gets a dummy UV
        vt = np.vstack([uvinfo['vt'], [[0.0, 0.0]]])
        T = np.vstack([uvinfo['T'], np.full((len(hF) - len(dF), 3), len(uvinfo['vt']), int)])
        uv = {'vt': vt, 'T': T, 'img': uvinfo['img']}
    return {'hV': hV, 'hF': hF, 'rep': rep, 'd': d, 'seam': seam, 'uv': uv}


def replace_commit(p):
    global DRAFT
    rep, d, seam = p['rep'], p['d'], p['seam']
    A.replace_mesh('head', p['hV'], p['hF'],
                   {'donor': {'asset': d['donor'], 'part': 'head'}, 'socket': 'neck', 'scale': d.get('scale', 'match_ring'),
                    'seam': seam}, scores={'after': {'ring_gap': round(rep['ring_gap'], 4), 'scale': round(rep['scale'], 4),
                                                     **({'seam_stretch': rep['seam_stretch']} if 'seam_stretch' in rep else {})}})
    DRAFT = Selection(A.parts['head'])
    if p.get('uv'):
        import texture
        texture.register(A.parts['head'], p['uv']['vt'], p['uv']['T'], p['uv']['img'])
    import edit_log
    _IDS.append(edit_log.record('user', 'replace_part', {'donor': d['donor'], 'scale': d.get('scale', 'match_ring'), 'seam': seam}, 0,
                                {'count': len(A.parts['head'].V), 'centroid': [0, 0, 0], 'bbox': None, 'regions': ['head']},
                                {'after': {k: v for k, v in rep.items() if k in ('ring_gap', 'scale', 'seam_stretch')}}, SESSION))
    _REDO_IDS.clear()
    return {'report': rep, 'donors': DONORS}


def replace_head(d):
    """d: {donor: template|hero1, scale: match_ring|keep}: put the donor head on the neck socket of the body"""
    return replace_commit(replace_prepare(d))


def replace_job(d):
    """same as replace_head but in the background: progress, ETA, cancel; the asset changes only at the final commit"""
    import jobs

    def work(step):
        p = replace_prepare(d, step)
        step('применяю', 0.97)      # last cancel point; after it the commit is atomic
        with LOCK:
            r = replace_commit(p)
        return {'report': {k: (float(v) if isinstance(v, (np.floating, float)) else v) for k, v in r['report'].items()
                           if isinstance(v, (int, float, np.floating))}}
    return {'job': jobs.start(work).id}


def state():
    _init()
    m = A.parts['head']
    return {'regions': REG['names'], 'draft': int(DRAFT.count()), 'draft_vertices': DRAFT.vertices(), 'vertices': len(m.V),
            'selections': [{'id': i, 'name': meta['name'], 'count': s.count(), 'feather': meta['feather']}
                           for i, (s, meta) in A.sel.items()],
            'ops': [dict(o, stale_scores=bool(o.get('scores')) and i < len(A.log) - 1) for i, o in enumerate(A.log)], 'donors': DONORS, 'sources': sources(), 'can_undo': bool(A._undo), 'can_redo': bool(A._redo)}


def mesh():
    """head first (its vertex ids are the selection ids), then the body; nhead tells where the head ends"""
    _init()
    h = A.parts['head']
    bV, bF = _body()
    V = np.vstack([h.V, bV])
    F = np.vstack([h.F, bF + len(h.V)])
    return {'v': np.round(V, 5).ravel().tolist(), 'f': F.ravel().tolist(), 'nhead': len(h.V), 'nfhead': len(h.F)}


def suggest_area(d):
    """d: {selection: 'draft'|id, feather}: ranked smoothing proposals for the area; changes nothing"""
    import suggest
    _init()
    sel = d.get('selection', 'draft')
    s = DRAFT if sel == 'draft' else A.sel[sel][0]
    feather = float(d.get('feather', 0)) if sel == 'draft' else A.sel[sel][1]['feather']
    m = A.parts['head']
    return suggest.suggest(m.V, m.F, s.weights(feather), int(d.get('top', 3)))


def before():
    """the model as it was before the last op ('до'), in the format of mesh(); None if there is nothing to compare"""
    _init()
    if not A._undo or A._undo[-1][0] != 'head':
        return {'none': True}
    V0, F0 = A._undo[-1][1]
    bV, bF = _body()
    h = A.parts['head']
    moved = float(np.linalg.norm(V0 - h.V, axis=1).max()) if len(V0) == len(h.V) else None
    V = np.vstack([V0, bV])
    F = np.vstack([F0, bF + len(V0)])
    return {'v': np.round(V, 5).ravel().tolist(), 'f': F.ravel().tolist(), 'nhead': len(V0), 'nfhead': len(F0),
            'op': A.log[-1]['op'], 'max_move': moved}


def select(d):
    """d: {action: brush|box|region|grow|shrink|invert|clear|load, ...}; returns the draft mask as vertex list"""
    global DRAFT
    _init()
    a = d['action']
    m = A.parts['head']
    if a == 'brush':
        DRAFT.brush(d['point'], float(d['radius']), add=d.get('mode', 'add') == 'add')
        if d.get('sym'):    # mirror across the X=0 plane (the template head is symmetric)
            p = list(d['point'])
            DRAFT.brush([-p[0], p[1], p[2]], float(d['radius']), add=d.get('mode', 'add') == 'add')
    elif a == 'box':
        DRAFT.box(d['lo'], d['hi'], add=d.get('mode', 'add') == 'add', visible_from=d.get('visible_from'))
    elif a == 'ids':    # vertex ids picked by the client (screen rectangle, front faces only)
        ids = np.asarray(d['ids'], int)
        ids = ids[(ids >= 0) & (ids < len(DRAFT.mask))]
        if d.get('mode', 'add') == 'add':
            DRAFT.mask[ids] = True
        else:
            DRAFT.mask[ids] = False
    elif a == 'set':    # exact restore of a draft (undo/redo of selection steps in the UI)
        DRAFT.mask[:] = False
        ids = np.asarray(d['ids'], int)
        DRAFT.mask[ids[(ids >= 0) & (ids < len(DRAFT.mask))]] = True
    elif a == 'region':
        if len(m.V) != len(REG['vertex']):
            raise ValueError('Части (по списку) заданы только для шаблона головы; на другой голове выделяйте кистью')
        r = Selection.from_region(m, REG, d['name'])
        DRAFT.union(r) if d.get('mode', 'add') == 'add' else DRAFT.subtract(r)
    elif a == 'grow':
        DRAFT.grow(int(d.get('steps', 1)))
    elif a == 'shrink':
        DRAFT.shrink(int(d.get('steps', 1)))
    elif a == 'invert':
        DRAFT.invert()
    elif a == 'clear':
        DRAFT.clear()
    elif a == 'load':
        DRAFT = Selection(m, A.sel[d['id']][0].mask)
    else:
        raise ValueError('unknown selection action ' + a)
    return {'count': DRAFT.count(), 'vertices': DRAFT.vertices()}


def save_selection(d):
    _init()
    sid = 'sel_' + str(len(A.sel) + 1) if not d.get('id') else d['id']
    A.select(sid, 'head', Selection(A.parts['head'], DRAFT.mask), d.get('name') or sid, float(d.get('feather', 0)))
    return {'id': sid}


def delete_selection(sid):
    _init()
    A.sel.pop(sid, None)


def _regions_of(ids):
    """names of template regions the area mostly touches (only when the head is the template)"""
    m = A.parts['head']
    if len(m.V) != len(REG['vertex']) or not len(ids):
        return []
    v = np.asarray(REG['vertex'])[ids]
    cnt = np.bincount(v, minlength=len(REG['names']))
    return [REG['names'][k] for k in range(len(cnt)) if cnt[k] >= 0.1 * len(ids)]


def apply(d):
    """d: {op, selection (id | 'draft' | None), params, feather}"""
    _init()
    sel = d.get('selection')
    if sel == 'draft':
        if not DRAFT.count():
            raise ValueError('the draft selection is empty')
        A.select('draft', 'head', Selection(A.parts['head'], DRAFT.mask), 'draft', float(d.get('feather', 0)))
    import edit_log
    import suggest
    m = A.parts['head']
    s = DRAFT if sel == 'draft' else A.sel[sel][0]
    feather = float(d.get('feather', 0)) if sel == 'draft' else A.sel[sel][1]['feather']
    w = s.weights(feather) if sel else np.ones(len(m.V))
    ids = np.flatnonzero(w > 0)
    area = {'count': int(len(ids)), 'centroid': [round(float(x), 4) for x in m.V[ids].mean(0)] if len(ids) else [0, 0, 0],
            'bbox': [[round(float(x), 4) for x in m.V[ids].min(0)], [round(float(x), 4) for x in m.V[ids].max(0)]] if len(ids) else None,
            'regions': _regions_of(ids)}
    r0, _ = suggest.area_metrics(m.V, m.V, m.F, w)
    V0 = m.V.copy()
    rec = A.apply(d['op'], 'head', sel, d.get('params'), by=d.get('by', 'user'))
    r1, sh = suggest.area_metrics(V0, A.parts['head'].V, A.parts['head'].F, w)
    _IDS.append(edit_log.record(rec['by'], d['op'], d.get('params') or {}, feather, area,
                                {'before': {'roughness': round(r0, 5)}, 'after': {'roughness': round(r1, 5), 'shrink': round(sh, 4)}}, SESSION))
    _REDO_IDS.clear()
    if sel == 'draft':
        rec['selection'] = 'draft'
        A.sel.pop('draft', None)
    return {'rec': rec}


def history(action):
    """undo/redo; a replace_part changes the vertex order, so the draft selection (vertex ids) is dropped then"""
    global DRAFT
    _init()
    nxt = (A.log[-1] if A.log else None) if action == 'undo' else (A._redo[-1][2] if A._redo else None)
    r = A.undo() if action == 'undo' else A.redo()
    import edit_log
    if r and action == 'undo' and _IDS:
        _REDO_IDS.append(_IDS.pop())
        edit_log.verdict(_REDO_IDS[-1], 'undone')
    elif r and action == 'redo' and _REDO_IDS:
        _IDS.append(_REDO_IDS.pop())
        edit_log.verdict(_IDS[-1], 'accepted')
    if (nxt and nxt['op'] == 'replace_part') or len(DRAFT.mask) != len(A.parts['head'].V):
        DRAFT = Selection(A.parts['head'])
    return {'ok': r}


# --- texture and UV (texture.py): the head must be the template
def tex_info():
    _init()
    import texture
    ok = texture.available(A.parts['head'])
    return dict(texture.status(A.parts['head']), available=ok)


def tex_paint(d):
    _init()
    import texture
    r = texture.paint(d, A.parts['head'])
    return dict(r, **texture.status(A.parts['head']))


def uv_xform(d):
    _init()
    import texture
    if not DRAFT.count():
        raise ValueError('Сначала выделите место на модели')
    r = texture.uv_xform(d, A.parts['head'], DRAFT.weights(float(d.get('feather', 0))))
    return dict(r, **texture.status(A.parts['head']))


def tex_history(d):
    _init()
    import texture
    return dict(texture.history(d['action'], A.parts['head']), **texture.status(A.parts['head']))


def tex_export(d):
    _init()
    import texture
    return texture.export(A.parts['head'])


def uv_layout():
    _init()
    import texture
    return texture.uv_layout(A.parts['head'])


def mesh_uv():
    _init()
    import texture
    return texture.mesh_uv(A.parts['head'])
