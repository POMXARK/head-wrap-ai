"""jobs + replace_job: progress grows, cancel leaves the asset untouched, finished job commits."""
import os, sys, time
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import jobs
import edit_api as E


def wait(j, st=('done', 'cancelled', 'error'), t=60):
    t0 = time.time()
    while jobs.get(j)['status'] not in st and time.time() - t0 < t:
        time.sleep(0.02)
    return jobs.get(j)


def test_progress_and_cancel():
    seen = []

    def fn(step):
        for i in range(50):
            step('шаг %d' % i, i / 50)
            seen.append(i)
            time.sleep(0.02)
    j = jobs.start(fn)
    time.sleep(0.3)
    mid = jobs.get(j.id)
    assert mid['status'] == 'running' and 0 < mid['progress'] < 1 and mid['eta_s'] is not None
    jobs.cancel(j.id)
    r = wait(j.id)
    assert r['status'] == 'cancelled' and len(seen) < 50


def test_replace_job_cancel_keeps_model():
    E._init()
    v0, f0 = E.A.parts['head'].V.copy(), E.A.parts['head'].F.copy()
    n_log = len(E.A.log)
    real = E._donor

    def slow(name):          # a slow donor so that the cancel arrives before the commit
        time.sleep(0.5)
        return real(name)
    E._donor = slow
    try:
        jid = E.replace_job({'donor': 'template'})['job']
        time.sleep(0.1)
        jobs.cancel(jid)
        r = wait(jid)
    finally:
        E._donor = real
    assert r['status'] == 'cancelled', r
    assert np.array_equal(E.A.parts['head'].V, v0) and np.array_equal(E.A.parts['head'].F, f0) and len(E.A.log) == n_log


def test_replace_job_done():
    E._init()
    n_log = len(E.A.log)
    jid = E.replace_job({'donor': 'template'})['job']
    r = wait(jid)
    assert r['status'] == 'done' and r['progress'] == 1.0, r
    assert len(E.A.log) == n_log + 1 and E.A.log[-1]['op'] == 'replace_part'
    E.history('undo')


if __name__ == '__main__':
    for k, f in list(globals().items()):
        if k.startswith('test_'):
            f(); print('ok', k)
