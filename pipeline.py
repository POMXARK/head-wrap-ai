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


def state():
    out = {'running': STATE['running'], 'rc': STATE['rc'], 'lines': STATE['lines'][-200:]}
    try:
        out['eyes'] = json.load(open(os.path.join(WORK, 'eye_score.json')))
    except (OSError, ValueError):
        out['eyes'] = None
    out['glb'] = 'work/hero1_eye.glb' if os.path.exists(os.path.join(WORK, 'hero1_eye.glb')) else None
    out['has_png'] = os.path.exists(os.path.join(WORK, 'eye_score.png'))
    return out


PAGE = """<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>Конвейер головы</title>
<style>body{font:14px sans-serif;margin:16px;max-width:1200px}button{font-size:14px;padding:6px 12px;margin:2px}
pre{background:#111;color:#ccc;padding:8px;height:260px;overflow:auto;font-size:12px}table{border-collapse:collapse;font-size:12px}
table.btns td{text-align:left;border:0;font-size:14px}td,th{border:1px solid #bbb;padding:2px 6px;text-align:right}.bad{background:#fcc}.ok{color:#080}.row{display:flex;gap:16px;flex-wrap:wrap}
.row>div{flex:1;min-width:340px}img{max-width:100%;border:1px solid #888}model-viewer{width:100%;height:380px;background:#ddd}</style>
<a href="/">&larr; head-wrap-ai</a><h2>Конвейер головы</h2>
<p>Голова собирается из готовых промежуточных файлов (<code>work/</code>) шагами сверху вниз. Кнопки запускают ровно эти шаги; результат — файл <code>work/hero1_eye.glb</code>, он же показан справа в 3D.</p>
<table class=btns>
<tr><td><button onclick="go('status')">Состояние</button></td><td>Показать, какие файлы шагов есть и свежие ли они. Ничего не меняет.</td></tr>
<tr><td><button onclick="go('texture')">Текстура</button></td><td>Пересобрать цвет кожи головы (подгонка цвета, швы шеи, нейрозаливка LaMa). Долго. Нужна, если меняли исходную картинку.</td></tr>
<tr><td><button onclick="go('build')"><b>Собрать голову</b></button></td><td>Главная кнопка: собрать модель головы с глазами и хвостом в <code>hero1_eye.glb</code> и сразу оценить глаза и всю сетку.</td></tr>
<tr><td><button onclick="go('eyes')">Оценка глаз</button></td><td>Только оценка глаз готовой модели (видны ли, раскрыты ли, нет ли складки): таблица и картинка слева.</td></tr>
<tr><td><button onclick="go('mesh')">Оценка сетки</button></td><td>Оценка всей головы: осколки, растянутая текстура (щека, ухо, шея, челюсть). Картинка профиля — ниже, синие и красные точки — дефекты.</td></tr>
<tr><td>Модель: <select id=mdl><option>hero1</option><option>hero</option></select> <button onclick="go('game')">В игру</button></td><td>Положить собранную голову в игру для выбранной модели (hero или hero1) и снять рендеры. Перезаписывает файлы игры.</td></tr>
<tr><td><button onclick="go('all')">Всё</button></td><td>Собрать → в игру → рендер одним нажатием.</td></tr>
</table><div><span id=st></span></div>
<h3>Журнал</h3><pre id=lg></pre>
<div class=row><div><h3>Оценка глаз по мешам</h3><div id=sc>нет данных — нажмите «Оценка глаз»</div><br><img id=im hidden><h3>Оценка сетки (профиль)</h3><img id=mi hidden onerror="this.hidden=true"></div>
<div><h3>Голова (3D)</h3><model-viewer id=mv camera-controls auto-rotate shading-intensity=1 exposure=1.1></model-viewer>
<div id=mvn class=h></div></div></div>
<script type=module src="https://cdn.jsdelivr.net/npm/@google/model-viewer@3.5.0/dist/model-viewer.min.js"></script>
<script>
const $=i=>document.getElementById(i);let glbT=0;
async function go(s){const r=await (await fetch('/api/run',{method:'POST',body:JSON.stringify({step:s,model:$('mdl').value})})).json();if(r.error)alert(r.error)}
function table(e){const ks=['visible','through','aperture','picture','iris','back','step','shade','depth','gaps','blocky'];
const T={visible:[.9,1e9],through:[-1,.03],aperture:[.27,.45],picture:[.5,1e9],back:[-1,0],step:[-1,.006],shade:[-1,25],depth:[-1,.04],gaps:[-1,0],blocky:[-1,.6]};
let h='<b>score '+Math.round(e.score)+'/100</b><table><tr><th>вид</th>'+ks.map(k=>'<th>'+k+'</th>').join('')+'</tr>';
for(const v in e.views){h+='<tr><th>'+v+'</th>'+ks.map(k=>{const x=e.views[v][k],t=T[k];const bad=t&&(x<t[0]||x>t[1]);return '<td class="'+(bad?'bad':'')+'">'+(+x).toFixed(3)+'</td>'}).join('')+'</tr>'}
return h+'</table>'}
async function poll(){const s=await (await fetch('/api/run')).json();
$('st').textContent=s.running?('идёт: '+s.running+' …'):(s.rc==null?'':(s.rc==0?'готово':'код '+s.rc));$('st').className=s.rc==0?'ok':'';
$('lg').textContent=s.lines.join('\\n');$('lg').scrollTop=1e9;
if(s.eyes){$('sc').innerHTML=table(s.eyes)}
if(s.has_png){$('im').hidden=false;$('im').src='/api/img?p=work/eye_score.png&t='+(s.eyes?Math.round(s.eyes.score*1000):0)}
if(!s.running&&s.rc===0&&window.mT!=s.lines.length){window.mT=s.lines.length;$('mi').hidden=false;$('mi').src='/api/img?p=work/mesh_score.png&t='+Date.now()}
if(s.glb&&!s.running){const t=s.rc+'|'+s.lines.length;if(t!=glbT){glbT=t;$('mv').src='/api/file?f='+s.glb+'&t='+Date.now();$('mvn').textContent=s.glb}}}
setInterval(poll,2000);poll()
</script>"""
