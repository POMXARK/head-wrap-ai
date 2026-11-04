#!/usr/bin/env python3
"""The settings of the pipeline the user chooses in the panel (ours).

Every option has a default, a label and a description (the panel draws the form from OPTIONS). The values live in
work/options.json; HW_<NAME> in the environment wins (for a one-off run). Scripts read them with options.get('NAME')."""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
FILE = os.path.join(HERE, 'work', 'options.json')

# (name, default, kind, label, description, min, max, step) ; kind: bool | num
OPTIONS = [
    ('NECKBLUR', True, 'bool', 'Сгладить кожу под челюстью',
     'Размывает блочную кожу под челюстью, убирает контур заплатки на шее. Борода не трогается.'),
    ('NECKBLUR_SIGMA', 2.2, 'num', 'Сила сглаживания шеи',
     'Радиус размытия в текселах: больше — глаже, но пластиковее.', 0.5, 6, 0.1),
    ('FOLD', True, 'bool', 'Заполнять яму вокруг глаза',
     'Сглаживает яму (глазницу) обёртки под глазом. Выключите, чтобы увидеть исходную складку.'),
    ('PIT_RINGS', 6, 'num', 'Колец вокруг ямы',
     'На сколько рядов вершин заполнение выходит за яму: больше — мягче край, но больше меняется лицо.', 2, 12, 1),
    ('FIT_MAX', 0.15, 'num', 'Предел сдвига UV у ямы',
     'Вершины, чью UV пришлось бы сдвинуть дальше, остаются как были (иначе грани растягиваются через атлас).', 0.03, 0.5, 0.01),
    ('PLATE', True, 'bool', 'Перекрасить плиты под глазами',
     'Плоские «плиты» под глазами закрашиваются кожей лица и размываются.'),
    ('PLATE_BLUR', 3.0, 'num', 'Размытие плит',
     'Радиус размытия перекрашенных плит в текселах.', 0, 8, 0.5),
    ('UNDER', True, 'bool', 'Закрасить розовые круги под глазами (LaMa)',
     'Нейрозаливка кожи на месте розовых кругов. Долго; без неё круги остаются.'),
    ('UNDER_SCALE', 2.2, 'num', 'Размер закраски под глазом',
     'Во сколько раз зона закраски шире раскрытия глаза.', 1, 4, 0.1),
]
DEFAULTS = {o[0]: o[1] for o in OPTIONS}


def load():
    try:
        saved = json.load(open(FILE))
    except (OSError, ValueError):
        saved = {}
    return {k: saved.get(k, d) for k, d in DEFAULTS.items()}


def get(name):
    d = DEFAULTS[name]
    v = os.environ.get('HW_' + name)
    if v is None:
        v = load()[name]
    if isinstance(d, bool):
        return v if isinstance(v, bool) else str(v).lower() in ('1', 'true', 'yes', 'on')
    return type(d)(v) if not isinstance(v, str) or v else d


def save(values):
    cur = load()
    for k, v in values.items():
        if k in DEFAULTS:
            cur[k] = bool(v) if isinstance(DEFAULTS[k], bool) else type(DEFAULTS[k])(v)
    os.makedirs(os.path.dirname(FILE), exist_ok=True)
    json.dump(cur, open(FILE, 'w'), indent=1)
    return cur


def schema():
    out = []
    for o in OPTIONS:
        out.append({'name': o[0], 'default': o[1], 'kind': o[2], 'label': o[3], 'desc': o[4]} |
                   ({'min': o[5], 'max': o[6], 'step': o[7]} if o[2] == 'num' else {}))
    return out
