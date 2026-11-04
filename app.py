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


PAGE = """<!doctype html><meta charset=utf-8><title>head-wrap-ai</title>
<style>body{font:14px sans-serif;margin:20px;max-width:900px}pre{background:#111;color:#ccc;padding:8px;height:220px;overflow:auto}
input,select{margin:2px}.ok{color:#080}.bad{color:#b00}</style>
<h2>head-wrap-ai</h2><p>Этап 0: профили моделей. Остальные этапы — <code>docs/plan.md</code>.</p>
<p><a href="/pipeline"><b>Конвейер головы: собрать, оценить, в игру</b></a> &nbsp; <a href="/model"><b>Модель: части, импорт, замена</b></a> &nbsp; <a href="/review"><b>Сравнение вариантов (лучше/хуже)</b></a></p><h3>Профили моделей</h3><div id=pr></div><button onclick=add()>+ профиль</button> <button onclick=sv()>Сохранить</button>
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


REVIEW = """<!doctype html><meta charset=utf-8><title>review</title>
<style>body{font:14px sans-serif;margin:16px;max-width:1300px}img{max-width:100%;border:2px solid #888}.row{display:flex;gap:12px}
.row>div{flex:1;text-align:center}button{font-size:15px;padding:8px 14px;margin:4px}.h{color:#666;font-size:12px}
.done{opacity:.55}</style><a href="/">&larr; head-wrap-ai</a>
<h2>Сравнение вариантов</h2><div id=st class=h></div><div id=foc class=h></div><div id=cur></div><h3>История</h3><div id=hist></div>
<script>
const $=i=>document.getElementById(i);const img=(p,b)=>'/api/img?p='+encodeURIComponent(p)+(b?'&box='+b:'');
async function sf(box,name){await fetch('/api/focus',{method:'POST',body:JSON.stringify({box,name})});load()}
async function load(){const r=await (await fetch('/api/pairs')).json(),P=r.pairs,s=r.stats;
$('st').textContent=`пар: ${s.pairs}, ждут: ${s.pending}, ваших выборов: ${s.voted}, решил оценщик: ${s.auto}; оценщик учится на ${s.evaluator_votes} выборах, точность на них ${s.evaluator_acc==null?'—':Math.round(s.evaluator_acc*100)+'%'}`;
const f=r.focus;$('foc').innerHTML='Область работы: '+(f?`<b>${f.name||''}</b> [${f.box}] <button onclick="sf(null)">снять</button>`:'вся картинка')+' — выделите мышью на картинке A/B/до, чтобы сузить';
const q=P.filter(p=>p.status=='pending')[0];
$('cur').innerHTML=q?`<h3>#${q.id} ${q.problem}: ${q.question}</h3>${q.pred_a!=null?`<div class=h>оценщик думает: A лучше с вероятностью ${Math.round(q.pred_a*100)}%</div>`:''}${q.vlm?`<div class=h>VLM-судья: лучше ${q.vlm.toUpperCase()}</div>`:''}
<div class=row>${q.base?`<div>до<br><img class=sel src="${img(q.base)}"></div>`:''}<div><b>A</b> ${q.a.label}<br><img class=sel src="${img(q.a.img,q.box)}" data-full="${img(q.a.img)}"></div><div><b>B</b> ${q.b.label}<br><img class=sel src="${img(q.b.img,q.box)}"></div></div>
<p><button onclick="v(${q.id},'a')">A лучше</button><button onclick="v(${q.id},'b')">B лучше</button><button onclick="v(${q.id},'same')">одинаково</button><button onclick="v(${q.id},'both_worse')">оба хуже</button><button onclick="v(${q.id},'skip')">пропустить</button>
<input id=nt placeholder="заметка (что не так)" size=40></p>`:'<p>Ждущих пар нет.</p>';
$('hist').innerHTML=P.filter(p=>p.status!='pending').reverse().map(p=>`<div class=done>#${p.id} ${p.problem}: ${p.a.label} vs ${p.b.label} → <b>${p.choice}</b> (${p.status}) ${p.note||''}</div>`).join('')}
async function v(id,c){await fetch('/api/vote',{method:'POST',body:JSON.stringify({id,choice:c,note:$('nt').value})});load()}
setInterval(load,4000);load();
let d0=null;document.addEventListener('mousedown',e=>{if(e.target.className=='sel'&&!e.target.src.includes('box='))d0={x:e.offsetX,y:e.offsetY,im:e.target};e.preventDefault()});
document.addEventListener('mouseup',async e=>{if(!d0)return;const im=d0.im,k=im.naturalWidth/im.width,x0=Math.min(d0.x,e.offsetX)*k,x1=Math.max(d0.x,e.offsetX)*k,y0=Math.min(d0.y,e.offsetY)*k,y1=Math.max(d0.y,e.offsetY)*k;d0=null;
if(x1-x0>8&&y1-y0>8){const S=2048/Math.max(im.naturalWidth,im.naturalHeight);sf([x0,y0,x1,y1].map(v=>Math.round(v*S)),'drawn')}})
</script>"""


MODEL = """<!doctype html><meta charset=utf-8><title>model</title>
<style>body{font:14px sans-serif;margin:16px;max-width:1100px}table{border-collapse:collapse}td,th{border:1px solid #bbb;padding:4px 8px;text-align:left}
select,input,button{font-size:14px;padding:4px;margin:2px}.h{color:#666}</style>
<a href="/">&larr; head-wrap-ai</a> | <a href="/review">Голова: сравнение вариантов</a>
<h2>Модель: из чего состоит, замена частей</h2>
<p class=h>Отдельный режим: любая GLB-модель (не только голова). Исходный файл не меняется, результат пишется в новый файл.</p>
<p>Файл: <select id=f onchange=show()></select></p><div id=t></div>
<h3>Заменить / добавить / убрать часть</h3>
<p>В файле <b id=tg></b> часть <select id=n></select>
<br>на часть <select id=sf onchange=sparts()></select> <select id=sn></select>
<br>новое имя файла (необязательно): <input id=o size=30 placeholder="work/new.glb">
<br><button onclick="go('replace')">заменить</button><button onclick="go('add')">добавить из другого файла</button><button onclick="go('remove')">убрать</button></p>
<h3>Ремеш, UV-развёртка</h3>
<p>Часть выбранная выше. Ремеш: целевое число треугольников <input id=fc size=6> или длина ребра <input id=ed size=6> или подразбиений <input id=sd size=3>
<button onclick="go('remesh')">ремеш + новая UV + перенос текстуры</button> <button onclick="go('uv')">только новая UV-развёртка</button></p>
<div id=res class=h></div>
<script>
const $=i=>document.getElementById(i);let FILES=[];
async function init(){FILES=(await (await fetch('/api/model')).json()).files;$('f').innerHTML=$('sf').innerHTML=FILES.map(x=>`<option>${x}</option>`).join('');show();sparts()}
async function show(){const r=await (await fetch('/api/model?f='+encodeURIComponent($('f').value))).json();$('tg').textContent=$('f').value;
$('t').innerHTML='<table><tr><th>часть (node)<th>вершин<th>треугольников<th>UV<th>текстура<th>габариты (min .. max)</tr>'+r.parts.map(p=>`<tr><td><b>${p.node}</b><td>${p.vertices}<td>${p.triangles}<td>${p.uv?'да':'нет'}<td>${p.texture?p.texture.join('×'):'—'}<td>${p.bbox_min} .. ${p.bbox_max}</tr>`).join('')+'</table>';
$('n').innerHTML=r.parts.map(p=>`<option>${p.node}</option>`).join('')}
async function sparts(){const r=await (await fetch('/api/model?f='+encodeURIComponent($('sf').value))).json();$('sn').innerHTML=r.parts.map(p=>`<option>${p.node}</option>`).join('')}
async function go(op){const o=$('o').value;const r=await fetch('/api/model',{method:'POST',body:JSON.stringify({op,target:$('f').value,node:$('n').value,source:$('sf').value,snode:$('sn').value,out:o,faces:$('fc').value,edge:$('ed').value,subdivide:$('sd').value})});
const j=await r.json().catch(()=>({}));$('res').textContent=j.out?'готово → '+j.out:'ошибка';await init()}
init()
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
        elif path == '/model':
            self.send(MODEL, 'text/html')
        elif path == '/api/model':
            import model
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
                self.send_error(400)
                return
            self.send({'ok': True, 'out': os.path.relpath(out, HERE)})
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
