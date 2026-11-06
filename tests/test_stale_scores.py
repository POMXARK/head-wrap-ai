"""stale scores: pipeline.stale_reason by file mtimes; edit_api marks scores of non-last ops as stale."""
import os, sys, tempfile, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import pipeline
import edit_api as E


def test_pipeline_stale():
    d = tempfile.mkdtemp()
    assert pipeline.stale_reason('eye_score.json', work=d) == 'нет оценки'
    t = time.time()
    for n, dt in (('hero1_eye.glb', -10), ('options.json', -10), ('eye_score.json', 0)):
        open(os.path.join(d, n), 'w').write('{}')
        os.utime(os.path.join(d, n), (t + dt, t + dt))
    assert pipeline.stale_reason('eye_score.json', work=d) is None
    os.utime(os.path.join(d, 'options.json'), (t + 5, t + 5))
    assert 'настройки' in pipeline.stale_reason('eye_score.json', work=d)
    os.utime(os.path.join(d, 'options.json'), (t - 10, t - 10))
    os.utime(os.path.join(d, 'hero1_eye.glb'), (t + 5, t + 5))
    assert 'модель' in pipeline.stale_reason('eye_score.json', work=d)


def test_edit_ops_stale():
    E._init()
    while E.A._undo:
        E.history('undo')
    E.replace_head({'donor': 'template'})
    assert [o['stale_scores'] for o in E.state()['ops']] == [False]
    E.select({'action': 'brush', 'point': list(E.A.parts['head'].V[0]), 'radius': 1.0})
    E.apply({'op': 'smooth', 'selection': 'draft', 'params': {'iterations': 2}})
    assert [o['stale_scores'] for o in E.state()['ops']] == [True, False]
    E.history('undo'); E.history('undo')


if __name__ == '__main__':
    for k, f in list(globals().items()):
        if k.startswith('test_'):
            f(); print('ok', k)
