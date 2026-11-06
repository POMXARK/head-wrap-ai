"""Common format of critic results (ours, task C1): every critic (eye_score, mesh_score, replace_part report) is converted
to {critic, version, score, summary, source, metrics:[{name,label,value,unit,better,zone,ok}]} — spec/critic.schema.json.
Agents and the UI read only this format. from_eye(d) / from_mesh(d) / from_replace(scores) -> dict; validate(c); worst(c)."""
import json
import os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
EYE = {'visible': ('доля видимой радужки/глаза', 'higher'), 'aperture': ('раскрытие глаза', 'higher'),
       'through': ('просвет сквозь глаз', 'lower'), 'step': ('ступенька у края', 'lower'), 'depth': ('глубина ямы', 'lower'),
       'shade': ('затемнение', 'lower'), 'iris': ('доля радужки', 'higher'), 'blocky': ('блочность текстуры', 'lower')}
MESH = {'shard': ('осколки', 'lower'), 'stretch': ('растяжение текстуры', 'lower'), 'seam': ('шов', 'lower')}
REPLACE = {'ring_gap': ('несовпадение кольца', 'lower', 'доля радиуса'), 'scale': ('масштаб донора', 'higher', '×'),
           'seam_stretch': ('растяжение шва', 'lower', '× радиуса')}


def _m(name, label, value, better, zone=None, unit='', ok=None):
    m = {'name': name, 'label': label, 'value': round(float(value), 5), 'unit': unit, 'better': better, 'ok': ok}
    if zone:
        m['zone'] = zone
    return m


def from_eye(d, source='work/eye_score.json'):
    """eye_score.json: {score, views:{view:{metric:value}}} -> one metric per (metric, view)"""
    ms = []
    for view, vals in d['views'].items():
        for k, v in vals.items():
            if k in EYE and isinstance(v, (int, float)):
                ms.append(_m(k, EYE[k][0], v, EYE[k][1], zone=view))
    return {'critic': 'eye', 'version': 1, 'score': float(d['score']), 'source': source, 'metrics': ms,
            'summary': 'Глаза: %.0f из 100' % d['score']}


def from_mesh(d, source='work/mesh_score.json'):
    ms = []
    for zone, vals in d['zones'].items():
        for k, v in vals.items():
            if k in MESH:
                ms.append(_m(k, MESH[k][0], v, MESH[k][1], zone=zone))
    return {'critic': 'mesh', 'version': 1, 'score': float(d['score']), 'source': source, 'metrics': ms,
            'summary': 'Сетка: %.0f из 100' % d['score']}


def from_replace(scores, source='op replace_part'):
    """the 'after' dict recorded by replace_part; score is not defined for it (None) — only metrics"""
    a = scores.get('after', scores)
    ms = [_m(k, REPLACE[k][0], v, REPLACE[k][1], unit=REPLACE[k][2]) for k, v in a.items() if k in REPLACE]
    return {'critic': 'replace', 'version': 1, 'score': None, 'source': source, 'metrics': ms,
            'summary': 'Замена части: ' + ', '.join('%s %.3g' % (m['label'], m['value']) for m in ms)}


def validate(c):
    import jsonschema
    jsonschema.Draft202012Validator(json.load(open(os.path.join(HERE, 'spec', 'critic.schema.json')))).validate(c)
    return c


def worst(c, n=3):
    """the n metrics furthest from good within the critic: 'lower' ones by value, 'higher' by 1-value — explanation for the user"""
    return sorted(c['metrics'], key=lambda m: -(m['value'] if m['better'] == 'lower' else 1 - m['value']))[:n]


def load(kind, work=os.path.join(HERE, 'work')):
    f = {'eye': 'eye_score.json', 'mesh': 'mesh_score.json'}[kind]
    d = json.load(open(os.path.join(work, f)))
    return validate((from_eye if kind == 'eye' else from_mesh)(d, 'work/' + f))
