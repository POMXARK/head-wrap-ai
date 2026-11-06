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


PAGE = """<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>Конвейер головы</title>
<style>body{font:14px sans-serif;margin:16px;max-width:1200px}button{font-size:14px;padding:6px 12px;margin:2px}
pre{background:#111;color:#ccc;padding:8px;height:260px;overflow:auto;font-size:12px}table{border-collapse:collapse;font-size:12px}
table.btns td{text-align:left;border:0;font-size:14px}td,th{border:1px solid #bbb;padding:2px 6px;text-align:right}.bad{background:#fcc}.ok{color:#080}.row{display:flex;gap:16px;flex-wrap:wrap}
.row>div{flex:1;min-width:340px}img{max-width:100%;border:1px solid #888}#opts label{display:block;margin:4px 0}#opts .d{color:#666;font-size:12px;margin-left:24px}.h{color:#555;font-size:12px}model-viewer{width:100%;height:380px;background:#ddd}</style>
<a href="/">&larr; head-wrap-ai</a><h2>Конвейер головы</h2>
<details id=help open><summary><b>Справка: что это и как пользоваться</b></summary>
<p><b>Зачем.</b> Панель собирает голову героя (hero / hero1) для игры и помогает подобрать настройки так, чтобы глаза были открыты, без ям и растянутой текстуры. Вы меняете настройки, собираете голову и смотрите оценки и 3D — без правки кода.</p>
<ol>
<li><b>Выберите настройки</b> в блоке «Настройки» и нажмите «Сохранить настройки». Они лежат в <code>work/options.json</code>; «По умолчанию» возвращает исходные значения.</li>
<li><b>Если меняли «Сгладить кожу под челюстью» или её силу</b> — сначала «Текстура» (долго, нейрозаливка LaMa на Windows-машине), остальные настройки действуют сразу.</li>
<li><b>«Собрать голову»</b> — главная кнопка: строит <code>hero1_eye.glb</code> и сам оценивает глаза и сетку (минуты).</li>
<li><b>Смотрите результат:</b> слева таблица «Оценка глаз» (видны ли глаза, раскрыты ли, нет ли ямы/складки) и картинка профиля «Оценка сетки» (синие и красные точки — дефекты); справа голова в 3D, её можно вращать мышью. Оценки — от 0 до 100, чем больше, тем лучше.</li>
<li><b>«Сохранить вариант»</b> — дайте имя; голова копируется вместе с настройками и обеими оценками. Меняйте настройки, собирайте и сохраняйте новые варианты.</li>
<li><b>Сравните:</b> в таблице вариантов видно оценки и чем каждый отличается от умолчаний; выберите вариант в списке «Слева» и другой в «Справа» — две головы будут рядом в 3D.</li>
<li><b>Когда устраивает</b> — выберите модель (hero / hero1) и «В игру»: голова записывается в файлы игры (перезаписывает их!). «Всё» делает сборку, перенос в игру и рендер за раз.</li>
</ol>
<p><b>Кнопки по назначению.</b> «Состояние» — какие файлы шагов есть и свежие ли (ничего не меняет); «Оценка глаз» и «Оценка сетки» — только оценить готовую модель, не пересобирая; «Журнал» внизу — вывод запущенных шагов.</p>
<p class=h>Подсказка: если сомневаетесь — оставьте умолчания, нажмите «Собрать голову» и сохраните вариант «умолчания» как точку отсчёта для сравнения.</p>
</details>
<p>Голова собирается из готовых промежуточных файлов (<code>work/</code>) шагами сверху вниз. Кнопки запускают ровно эти шаги; результат — файл <code>work/hero1_eye.glb</code>, он же показан справа в 3D.</p>
<table class=btns>
<tr><td><button title="Показать, какие файлы шагов есть и свежие ли они. Ничего не меняет." onclick="go('status')">Состояние</button></td><td>Показать, какие файлы шагов есть и свежие ли они. Ничего не меняет.</td></tr>
<tr><td><button title="Пересобрать цвет кожи головы (подгонка цвета, швы шеи, LaMa). Долго." onclick="go('texture')">Текстура</button></td><td>Пересобрать цвет кожи головы (подгонка цвета, швы шеи, нейрозаливка LaMa). Долго. Нужна, если меняли исходную картинку.</td></tr>
<tr><td><button title="Собрать hero1_eye.glb (голова, глаза, хвост) и сразу оценить глаза и сетку." onclick="go('build')"><b>Собрать голову</b></button></td><td>Главная кнопка: собрать модель головы с глазами и хвостом в <code>hero1_eye.glb</code> и сразу оценить глаза и всю сетку.</td></tr>
<tr><td><button title="Оценка только глаз готовой модели: таблица и картинка." onclick="go('eyes')">Оценка глаз</button></td><td>Только оценка глаз готовой модели (видны ли, раскрыты ли, нет ли складки): таблица и картинка слева.</td></tr>
<tr><td><button title="Оценка всей головы: осколки и растянутая текстура, картинка профиля." onclick="go('mesh')">Оценка сетки</button></td><td>Оценка всей головы: осколки, растянутая текстура (щека, ухо, шея, челюсть). Картинка профиля — ниже, синие и красные точки — дефекты.</td></tr>
<tr><td>Модель: <select id=mdl title='Для какой модели игры собрать голову: hero или hero1'><option>hero1</option><option>hero</option></select> <button title="Положить голову в игру для выбранной модели и снять рендеры. Перезаписывает файлы игры." onclick="go('game')">В игру</button></td><td>Положить собранную голову в игру для выбранной модели (hero или hero1) и снять рендеры. Перезаписывает файлы игры.</td></tr>
<tr><td><button title="Собрать, затем в игру, затем рендер — одним нажатием." onclick="go('all')">Всё</button></td><td>Собрать → в игру → рендер одним нажатием.</td></tr>
</table><div><span id=st></span></div>
<h3>Настройки (вы выбираете)</h3>
<p class=h>Настройки хранятся в <code>work/options.json</code>. Изменили «сглаживание шеи» — нажмите «Текстура», потом «Собрать голову»; остальные действуют после «Собрать голову». Затем «Сохранить вариант», чтобы сравнить результаты в 3D.</p>
<div id=opts></div><button onclick="saveOpts()" title="Записать настройки в work/options.json">Сохранить настройки</button><button onclick="resetOpts()" title="Вернуть все значения по умолчанию">По умолчанию</button><span id=os class=ok></span>
<h3>Варианты головы</h3>
<input id=vn placeholder="имя варианта" size=18> <button onclick="saveVar()" title="Скопировать собранную голову и текущие настройки под этим именем">Сохранить вариант</button>
<div id=vt class=h></div>
Слева: <select id=vs onchange="showVar()"><option value="">текущая сборка</option></select>
Справа (сравнить): <select id=vs2 onchange="showVar()"><option value="">— не сравнивать —</option></select>
<h3>Журнал</h3><pre id=lg></pre>
<div class=row><div><h3>Оценка глаз по мешам</h3><div id=sc>нет данных — нажмите «Оценка глаз»</div><br><img id=im hidden><h3>Оценка сетки (профиль)</h3><img id=mi hidden onerror="this.hidden=true"></div>
<div><h3>Голова (3D)</h3><div style="display:flex;gap:6px"><div style="flex:1"><model-viewer id=mv camera-controls auto-rotate shading-intensity=1 exposure=1.1></model-viewer><div id=mvn class=h></div></div>
<div style="flex:1" id=b2 hidden><model-viewer id=mv2 camera-controls auto-rotate shading-intensity=1 exposure=1.1></model-viewer><div id=mvn2 class=h></div></div></div></div></div>
<script type=module src="https://cdn.jsdelivr.net/npm/@google/model-viewer@3.5.0/dist/model-viewer.min.js"></script>
<script>
const $=i=>document.getElementById(i);let glbT=0;
async function go(s){const r=await (await fetch('/api/run',{method:'POST',body:JSON.stringify({step:s,model:$('mdl').value})})).json();if(r.error)alert(r.error)}
function table(e){const ks=['visible','through','aperture','picture','iris','back','step','shade','depth','gaps','blocky'];
const T={visible:[.9,1e9],through:[-1,.03],aperture:[.27,.45],picture:[.5,1e9],back:[-1,0],step:[-1,.006],shade:[-1,25],depth:[-1,.04],gaps:[-1,0],blocky:[-1,.6]};
const D={visible:'видимая доля заплатки глаза (меньше 0.9 — глаз закрыт кожей)',through:'доля пикселей глаза, где виден фон (дыра)',aperture:'высота/ширина раскрытого глаза (норма 0.27–0.45)',picture:'доля не-кожи в глазу (белок, радужка)',iris:'тёмные пиксели радужки и зрачка',back:'вывернутые грани под глазом',step:'ступенька глубины под глазом (складка)',shade:'скачок яркости под глазом (дуга, пятно)',depth:'глубина ямки щеки под глазом',gaps:'дыры в голове рядом с глазом',blocky:'доля одинаковых соседних пикселей щеки (увеличенная текстура)'};
let h='<b>score '+Math.round(e.score)+'/100</b><table><tr><th>вид</th>'+ks.map(k=>'<th title="'+D[k]+'">'+k+'</th>').join('')+'</tr>';
for(const v in e.views){h+='<tr><th>'+v+'</th>'+ks.map(k=>{const x=e.views[v][k],t=T[k];const bad=t&&(x<t[0]||x>t[1]);return '<td class="'+(bad?'bad':'')+'">'+(+x).toFixed(3)+'</td>'}).join('')+'</tr>'}
return h+'</table>'}
let OPT=null;
async function loadOpts(){OPT=await (await fetch('/api/options')).json();let h='';
for(const o of OPT.schema){const v=OPT.values[o.name];
h+='<label title="'+o.desc+'">'+(o.kind=='bool'?'<input type=checkbox id="o_'+o.name+'" '+(v?'checked':'')+'> ':'<input type=number id="o_'+o.name+'" value="'+v+'" min="'+o.min+'" max="'+o.max+'" step="'+o.step+'" style="width:70px"> ')+'<b>'+o.label+'</b><div class=d>'+o.desc+(o.default!==undefined?' (по умолчанию: '+(o.kind=='bool'?(o.default?'да':'нет'):o.default)+')':'')+'</div></label>'}
$('opts').innerHTML=h}
function collect(){const r={};for(const o of OPT.schema){const e=$('o_'+o.name);r[o.name]=o.kind=='bool'?e.checked:+e.value}return r}
async function saveOpts(){await fetch('/api/options',{method:'POST',body:JSON.stringify(collect())});$('os').textContent=' сохранено';setTimeout(()=>$('os').textContent='',2000)}
async function resetOpts(){await fetch('/api/options',{method:'POST',body:JSON.stringify({reset:1})});loadOpts()}
async function saveVar(){await saveOpts();const r=await (await fetch('/api/variant',{method:'POST',body:JSON.stringify({name:$('vn').value})})).json();if(r.error)alert(r.error);else{$('vn').value='';poll()}}
function showVar(){const v=$('vs').value,w=$('vs2').value;const u=x=>'/api/file?f='+(x?'work/variants/'+x+'.glb':'work/hero1_eye.glb')+'&t='+Date.now();
$('mv').src=u(v);$('mvn').textContent=v||'текущая сборка';$('b2').hidden=!w;if(w){$('mv2').src=u(w);$('mvn2').textContent=w}}
async function poll(){const s=await (await fetch('/api/run')).json();
$('st').textContent=s.running?('идёт: '+s.running+' …'):(s.rc==null?'':(s.rc==0?'готово':'код '+s.rc));$('st').className=s.rc==0?'ok':'';
$('lg').textContent=s.lines.join('\\n');$('lg').scrollTop=1e9;
if(s.eyes){$('sc').innerHTML=(s.eyes_stale?'<div class=bad id=stale style="padding:4px">⚠ Оценка устарела: '+s.eyes_stale+'. Нажмите «Оценка глаз».</div>':'')+table(s.eyes)}
if(s.has_png){$('im').hidden=false;$('im').src='/api/img?p=work/eye_score.png&t='+(s.eyes?Math.round(s.eyes.score*1000):0)}
if(!s.running&&s.rc===0&&window.mT!=s.lines.length){window.mT=s.lines.length;$('mi').hidden=false;$('mi').src='/api/img?p=work/mesh_score.png&t='+Date.now()}
if(s.variants)vars(s.variants);
if(s.glb&&!s.running&&!$('vs').value){const t=s.rc+'|'+s.lines.length;if(t!=glbT){glbT=t;$('mv').src='/api/file?f='+s.glb+'&t='+Date.now();$('mvn').textContent=s.glb}}}
function vars(l){const names=l.map(x=>x.name).join();if(window.vN===names)return;window.vN=names;
for(const [id,first] of [['vs','текущая сборка'],['vs2','— не сравнивать —']]){const s=$(id),cur=s.value;s.innerHTML='<option value="">'+first+'</option>'+l.map(x=>'<option value="'+x.name+'">'+x.name+' (глаза '+(x.eye==null?'?':Math.round(x.eye))+', сетка '+(x.mesh==null?'?':Math.round(x.mesh))+')</option>').join('');s.value=cur}
$('vt').innerHTML=l.length?'<table><tr><th>вариант</th><th>глаза</th><th>сетка</th><th>что отличалось от умолчаний</th></tr>'+l.map(x=>'<tr><th>'+x.name+'</th><td>'+(x.eye==null?'?':Math.round(x.eye))+'</td><td>'+(x.mesh==null?'?':Math.round(x.mesh))+'</td><td style="text-align:left">'+Object.keys(x.options||{}).filter(k=>OPT&&OPT.schema.some(o=>o.name==k&&o.default!==x.options[k])).map(k=>k+'='+x.options[k]).join(', ')+'</td></tr>').join('')+'</table>':''}
setInterval(poll,2000);loadOpts();poll()
</script>"""
