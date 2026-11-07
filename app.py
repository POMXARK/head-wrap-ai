#!/usr/bin/env python3
"""head-wrap-ai: local web UI (stdlib only) for fitting a clean head template onto a generated head.

python app.py [--port 8770]   ->  http://127.0.0.1:8770
Stage 0 of docs/plan.md: model profiles (Ollama / OpenAI-compatible) with a check button, a log panel, a cache of
AI answers. Only 127.0.0.1 is served. Pictures never leave the machines of the user (see README, privacy).
"""
import argparse
import hashlib
import glob
import json
import os
import threading
import time
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOME = os.path.join(os.path.expanduser('~'), '.head-wrap-ai')
CONF = os.path.join(HOME, 'config.json')
HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, 'work', 'cache')
DEFAULT = {'profiles': [{'name': 'Ollama (ПК)', 'kind': 'ollama', 'url': 'http://127.0.0.1:11434',
                         'model': 'ministral-3:14b', 'role': 'judge'}], 'active': 0}
LOG = []
LOCK = threading.Lock()


def log(s):
    line = time.strftime('%H:%M:%S ') + s
    with LOCK:
        LOG.append(line)
        del LOG[:-500]
    print(line, flush=True)


def load():
    try:
        return json.load(open(CONF, encoding='utf-8'))
    except Exception:
        return json.loads(json.dumps(DEFAULT))


def save(c):
    os.makedirs(HOME, exist_ok=True)
    json.dump(c, open(CONF, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


def is_local(url):
    h = url.split('//', 1)[-1].split('/')[0].split(':')[0]
    return h in ('127.0.0.1', 'localhost') or h.startswith(('192.168.', '10.')) or h.endswith('.local')


def http(url, data=None, headers=None, timeout=60):
    req = urllib.request.Request(url, data=json.dumps(data).encode() if data is not None else None,
                                 headers={'Content-Type': 'application/json', **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def check(p):
    """List of models of the profile; raises on failure."""
    if p['kind'] == 'ollama':
        return [m['name'] for m in http(p['url'].rstrip('/') + '/api/tags', timeout=10)['models']]
    return [m['id'] for m in http(p['url'].rstrip('/') + '/models', headers={'Authorization': 'Bearer ' + p.get('key', '')},
                                  timeout=10)['data']]


def ask(p, prompt, image_b64=None):
    """image_b64: one picture or a list of pictures (A, B ...)"""
    imgs = [image_b64] if isinstance(image_b64, str) else image_b64
    """Ask the model of the profile; answers are cached by (model, prompt, picture)."""
    key = hashlib.sha1(json.dumps([p['model'], prompt, image_b64]).encode()).hexdigest()
    path = os.path.join(CACHE, key + '.json')
    if os.path.exists(path):
        return json.load(open(path, encoding='utf-8'))['answer']
    if not is_local(p['url']):
        log(f"ВНИМАНИЕ: профиль {p['name']} не локальный ({p['url']}), запрос с картинкой не отправлен")
        raise RuntimeError('external service blocked')
    if p['kind'] == 'ollama':
        m = {'role': 'user', 'content': prompt, **({'images': imgs} if imgs else {})}
        ans = http(p['url'].rstrip('/') + '/api/chat', {'model': p['model'], 'messages': [m], 'stream': False},
                   timeout=300)['message']['content']
    else:
        c = [{'type': 'text', 'text': prompt}] + [{'type': 'image_url', 'image_url': {'url': 'data:image/png;base64,' + i}} for i in imgs or []]
        ans = http(p['url'].rstrip('/') + '/chat/completions', {'model': p['model'], 'messages': [{'role': 'user', 'content': c}]},
                   {'Authorization': 'Bearer ' + p.get('key', '')}, 300)['choices'][0]['message']['content']
    os.makedirs(CACHE, exist_ok=True)
    json.dump({'answer': ans}, open(path, 'w', encoding='utf-8'), ensure_ascii=False)
    return ans


PAGE = open(os.path.join(HERE, 'index.html'), encoding='utf-8').read()


REVIEW = open(os.path.join(HERE, 'review.html'), encoding='utf-8').read()
MODEL = open(os.path.join(HERE, 'model.html'), encoding='utf-8').read()


JOBS = {}


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, body, ctype='application/json'):
        b = body if isinstance(body, bytes) else (body if isinstance(body, str) else json.dumps(body, ensure_ascii=False)).encode()
        if ctype == 'text/html':  # interactive guide on every window (tour.js)
            b += b'<script src="/tour.js"></script>'
        self.send_response(200)
        self.send_header('Content-Type', ctype + '; charset=utf-8')
        self.send_header('Content-Length', str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        path, _, q = self.path.partition('?')
        if path == '/':
            self.send(PAGE, 'text/html')
        elif path == '/api/config':
            self.send(load())
        elif path == '/api/log':
            self.send(LOG)
        elif path == '/proto':  # clickable prototypes of the editor (static, explained)
            self.send(open(os.path.join(HERE, 'proto', 'index.html'), encoding='utf-8').read(), 'text/html')
        elif path == '/pipeline':
            import pipeline
            self.send(pipeline.PAGE, 'text/html')
        elif path == '/api/run':
            import pipeline
            self.send(pipeline.state())
        elif path == '/api/options':
            import options
            self.send({'schema': options.schema(), 'values': options.load()})
        elif path == '/api/file':  # a built .glb of this folder for the 3D view
            f = os.path.realpath(os.path.join(HERE, urllib.parse.parse_qs(q).get('f', [''])[0]))
            if not f.startswith(HERE + os.sep) or not f.endswith('.glb') or not os.path.isfile(f):
                self.send_error(403)
            else:
                self.send(open(f, 'rb').read(), 'model/gltf-binary')
        elif path in ('/api/edit/state', '/api/edit/mesh', '/api/edit/before', '/api/edit/tex_info', '/api/edit/uv_layout', '/api/edit/mesh_uv'):
            import edit_api
            with edit_api.LOCK:
                try:
                    self.send({'state': edit_api.state, 'mesh': edit_api.mesh, 'before': edit_api.before, 'tex_info': edit_api.tex_info,
                               'uv_layout': edit_api.uv_layout, 'mesh_uv': edit_api.mesh_uv}[path.rsplit('/', 1)[1]]())
                except ValueError as e:
                    self.send({'error': str(e)})
                except FileNotFoundError as e:  # work/ is not in git: say what to copy, not a bare "Failed to fetch"
                    self.send({'error': 'нет файла ' + os.path.relpath(e.filename or '?', HERE) + ': положите в папку work/ файлы baked.png, hero1_eye.glb, eye_open.json (см. README)'})
        elif path == '/api/edit/parts':
            import edit_api
            try:
                with edit_api.LOCK:
                    edit_api._init()
                    self.send({'parts': edit_api.donor_parts(urllib.parse.parse_qs(q).get('src', [''])[0])})
            except Exception as e:
                self.send({'error': str(e)})
        elif path == '/api/edit/export':
            import edit_api
            qq = urllib.parse.parse_qs(q)
            try:
                with edit_api.LOCK:
                    b, ct, fn = edit_api.export_bytes(qq.get('fmt', ['glb'])[0], qq.get('body', ['0'])[0] == '1')
                self.send_response(200)
                self.send_header('Content-Type', ct)
                self.send_header('Content-Disposition', 'attachment; filename="%s"' % fn)
                self.send_header('Content-Length', str(len(b)))
                self.end_headers()
                self.wfile.write(b)
            except Exception as e:
                self.send({'error': str(e)})
        elif path == '/api/edit/texture.png':
            import edit_api
            import texture
            with edit_api.LOCK:
                b = texture.png(edit_api.A.parts['head'])
            self.send(b, 'image/png')
        elif path == '/api/critic':      # common critic format (C1): ?kind=eye|mesh
            import critics
            try:
                self.send(critics.load(urllib.parse.parse_qs(q).get('kind', [''])[0]))
            except (KeyError, OSError, ValueError) as e:
                self.send({'error': 'нет оценки: %s' % e})
        elif path == '/api/edit/job':
            import jobs
            try:
                self.send(jobs.get(urllib.parse.parse_qs(q).get('id', [''])[0]))
            except KeyError:
                self.send({'error': 'нет такой задачи'})
        elif path == '/ui.css':
            self.send(open(os.path.join(HERE, 'ui.css'), 'rb').read(), 'text/css')
        elif path == '/tour.js':
            self.send(open(os.path.join(HERE, 'tour.js'), 'rb').read(), 'application/javascript')
        elif path == '/edit':
            self.send(open(os.path.join(HERE, 'edit.html'), 'rb').read(), 'text/html')
        elif path == '/model':
            self.send(MODEL, 'text/html')
        elif path == '/api/model':
            import model
            jq = urllib.parse.parse_qs(q).get('job', [''])[0]
            if jq:
                j = JOBS.get(jq) or {'state': 'done', 'ok': False, 'error': 'unknown job'}
                self.send(dict(j, elapsed=round(time.time() - j.get('t0', time.time()), 1)))
                return
            f = urllib.parse.parse_qs(q).get('f', [''])[0]
            if f:
                f = os.path.realpath(f if os.path.isabs(f) else os.path.join(HERE, f))
                if not f.startswith(HERE + os.sep) or not f.endswith('.glb'):
                    self.send_error(403)
                    return
                self.send({'file': f, 'parts': model.parts(f)})
            else:
                files = sorted(glob.glob(os.path.join(HERE, 'work', '*.glb')) + glob.glob(os.path.join(HERE, 'models', '*.glb')))
                self.send({'files': [os.path.relpath(x, HERE) for x in files]})
        elif path == '/review':
            self.send(REVIEW, 'text/html')
        elif path == '/api/pairs':
            import review
            self.send({'pairs': review.load_pairs()[-40:], 'stats': review.stats(), 'focus': review.get_focus()})
        elif path == '/api/img':
            raw = urllib.parse.parse_qs(q)['p'][0]
            p = os.path.realpath(raw if os.path.isabs(raw) else os.path.join(HERE, raw))
            if not (p.startswith(HERE + os.sep) or p.startswith('/tmp/')) or not p.lower().endswith(('.png', '.jpg', '.jpeg')):
                self.send_error(403)
            else:
                import io
                from PIL import Image
                qs = urllib.parse.parse_qs(q)
                im = Image.open(p).convert('RGB')
                if 'box' in qs:
                    im = im.crop(tuple(int(v) for v in qs['box'][0].split(',')))
                    k = max(1, 560 // max(im.size))
                    im = im.resize((im.width * k, im.height * k), Image.LANCZOS)
                else:
                    im.thumbnail((900, 900))
                buf = io.BytesIO()
                im.save(buf, 'PNG')
                self.send(buf.getvalue(), 'image/png')
        elif path == '/api/check':
            c = load()
            p = c['profiles'][int(q.split('=')[1])]
            try:
                m = check(p)
                log(f"проверка {p['name']}: {len(m)} моделей" + ('' if is_local(p['url']) else ' (ВНЕШНИЙ адрес!)'))
                self.send({'ok': True, 'models': m})
            except Exception as e:
                log(f"проверка {p['name']}: {e}")
                self.send({'ok': False, 'error': str(e)})
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path == '/api/model':
            import model
            d = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            def t(k):
                r = os.path.realpath(os.path.join(HERE, d[k]))
                if not r.startswith(HERE + os.sep) or (k == 'out' and not r.endswith('.glb')):
                    raise ValueError('path outside the project / not .glb: ' + d[k])
                return r
            def work():
                try:
                    if d['op'] == 'replace':
                        out = model.replace(t('target'), d['node'], t('source'), d.get('snode') or None, d.get('out') and t('out'))
                    elif d['op'] == 'add':
                        out = model.add(t('target'), t('source'), d['snode'], d.get('name') or None, d.get('out') and t('out'))
                    elif d['op'] == 'remesh':
                        out = model.remesh(t('target'), d['node'], int(d['faces']) if d.get('faces') else None,
                                           float(d['edge']) if d.get('edge') else None, int(d.get('subdivide') or 0),
                                           out=d.get('out') and t('out'))
                    elif d['op'] == 'uv':
                        out = model.new_uv(t('target'), d['node'], out=d.get('out') and t('out'))
                    elif d['op'] == 'remove':
                        out = model.remove(t('target'), d['node'], d.get('out') and t('out'))
                    else:
                        raise ValueError('unknown op')
                    JOBS[jid].update(state='done', ok=True, out=os.path.relpath(out, HERE))
                except Exception as e:  # noqa: BLE001
                    JOBS[jid].update(state='done', ok=False, error=str(e))
            jid = '%d' % (time.time() * 1000)
            JOBS[jid] = {'state': 'run', 't0': time.time(), 'op': d['op']}
            threading.Thread(target=work, daemon=True).start()  # remesh with a texture takes minutes: poll /api/model?job=
            self.send({'job': jid})
            return
        if self.path.startswith('/api/edit/upload'):
            import edit_api
            try:
                with edit_api.LOCK:
                    self.send(edit_api.save_upload(urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).get('name', [''])[0],
                                                   self.rfile.read(int(self.headers.get('Content-Length') or 0))))
            except Exception as e:
                self.send({'error': str(e)})
            return
        if self.path.startswith('/api/edit/'):
            import edit_api
            d = json.loads(self.rfile.read(int(self.headers.get('Content-Length') or 0)) or b'{}')
            k = self.path[len('/api/edit/'):]
            try:
                with edit_api.LOCK:
                    r = {'select': edit_api.select, 'save': edit_api.save_selection, 'apply': edit_api.apply, 'replace': edit_api.replace_head,
                         'replace_job': edit_api.replace_job, 'suggest': edit_api.suggest_area, 'cancel': lambda x: __import__('jobs').cancel(x['id']),
                         'delete': lambda x: edit_api.delete_selection(x['id']) or {'ok': True},
                         'tex_paint': edit_api.tex_paint, 'uv_xform': edit_api.uv_xform, 'tex_history': edit_api.tex_history,
                         'tex_export': edit_api.tex_export, 'undo': lambda x: edit_api.history('undo'), 'redo': lambda x: edit_api.history('redo')}[k](d)
                self.send(r)
            except Exception as e:
                self.send({'error': str(e)})
            return
        if self.path == '/api/focus':
            import review
            d = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            review.set_focus(d.get('box'), d.get('name', 'drawn'))
            self.send({'ok': True})
            return
        if self.path == '/api/vote':
            import review
            d = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            acc = review.vote(int(d['id']), d['choice'], d.get('note', ''))
            log(f"выбор по паре {d['id']}: {d['choice']}; оценщик, точность на выборах: {acc}")
            self.send({'ok': True, 'acc': acc})
            return
        if self.path == '/api/options':
            import options
            j = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            if j.get('reset'):
                j = dict(options.DEFAULTS)
            log('настройки конвейера: %s' % j)
            self.send({'values': options.save(j)})
            return
        if self.path == '/api/variant':
            import pipeline
            j = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            name, err = pipeline.save_variant(j.get('name'))
            log('вариант головы: %s' % (name or err))
            self.send({'name': name, 'error': err})
            return
        if self.path == '/api/run':
            import pipeline
            j = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            log('шаг конвейера: %s' % j.get('step'))
            self.send({'error': pipeline.run(j.get('step'), j.get('model', 'hero1'))})
            return
        if self.path == '/api/config':
            save(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
            log('конфиг сохранён')
            self.send({'ok': True})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--port', type=int, default=8770)
    a = ap.parse_args()
    log(f'http://127.0.0.1:{a.port}')
    ThreadingHTTPServer(('127.0.0.1', a.port), H).serve_forever()


if __name__ == '__main__':
    main()
