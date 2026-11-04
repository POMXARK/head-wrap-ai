#!/usr/bin/env python3
"""head-wrap-ai: local web UI (stdlib only) for fitting a clean head template onto a generated head.

python app.py [--port 8770]   ->  http://127.0.0.1:8770
Stage 0 of docs/plan.md: model profiles (Ollama / OpenAI-compatible) with a check button, a log panel, a cache of
AI answers. Only 127.0.0.1 is served. Pictures never leave the machines of the user (see README, privacy).
"""
import argparse
import hashlib
import json
import os
import threading
import time
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


PAGE = """<!doctype html><meta charset=utf-8><title>head-wrap-ai</title>
<style>body{font:14px sans-serif;margin:20px;max-width:900px}pre{background:#111;color:#ccc;padding:8px;height:220px;overflow:auto}
input,select{margin:2px}.ok{color:#080}.bad{color:#b00}</style>
<h2>head-wrap-ai</h2><p>Этап 0: профили моделей. Остальные этапы — <code>docs/plan.md</code>.</p>
<h3>Профили моделей</h3><div id=pr></div><button onclick=add()>+ профиль</button> <button onclick=sv()>Сохранить</button>
<h3>Журнал</h3><pre id=lg></pre>
<script>
let C={};const $=i=>document.getElementById(i);
async function init(){C=await (await fetch('/api/config')).json();draw()}
function draw(){$('pr').innerHTML=C.profiles.map((p,i)=>`<div><input type=radio name=a ${C.active==i?'checked':''} onclick="C.active=${i}">
<input value="${p.name}" onchange="C.profiles[${i}].name=this.value">
<select onchange="C.profiles[${i}].kind=this.value"><option ${p.kind=='ollama'?'selected':''}>ollama</option><option ${p.kind!='ollama'?'selected':''} value=openai>openai</option></select>
<input size=28 value="${p.url}" onchange="C.profiles[${i}].url=this.value">
<input size=18 value="${p.model}" onchange="C.profiles[${i}].model=this.value">
<button onclick="chk(${i})">Проверить</button> <span id=r${i}></span></div>`).join('')}
function add(){C.profiles.push({name:'новый',kind:'ollama',url:'http://127.0.0.1:11434',model:'',role:'judge'});draw()}
async function sv(){await fetch('/api/config',{method:'POST',body:JSON.stringify(C)})}
async function chk(i){await sv();const r=await (await fetch('/api/check?i='+i)).json();
$('r'+i).className=r.ok?'ok':'bad';$('r'+i).textContent=r.ok?('ок: '+r.models.join(', ')):r.error}
setInterval(async()=>{$('lg').textContent=(await (await fetch('/api/log')).json()).join('\\n')},2000);init()
</script>"""


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, body, ctype='application/json'):
        b = body if isinstance(body, bytes) else (body if isinstance(body, str) else json.dumps(body, ensure_ascii=False)).encode()
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
