"""Background jobs with progress, ETA and cooperative cancel (ours, task B3).
j = jobs.start(lambda step: ...)  # step(msg, frac) reports progress and raises Cancelled after j.cancel()
jobs.get(id) -> dict(status running|done|cancelled|error, progress 0..1, msg, eta_s, result, error)"""
import threading
import time
import uuid


class Cancelled(Exception):
    pass


class Job:
    def __init__(self):
        self.id = uuid.uuid4().hex[:8]
        self.status, self.progress, self.msg = 'running', 0.0, 'старт'
        self.result = self.error = None
        self.t0 = time.time()
        self._stop = threading.Event()

    def step(self, msg, frac):
        if self._stop.is_set():
            raise Cancelled()
        self.msg, self.progress = msg, float(frac)

    def cancel(self):
        self._stop.set()

    def info(self):
        el = time.time() - self.t0
        eta = round(el * (1 - self.progress) / self.progress, 1) if 0.05 < self.progress < 1 and self.status == 'running' else None
        return {'id': self.id, 'status': self.status, 'progress': round(self.progress, 3), 'msg': self.msg, 'eta_s': eta,
                'elapsed_s': round(el, 1), 'result': self.result, 'error': self.error}


JOBS = {}


def start(fn):
    j = Job()
    JOBS[j.id] = j

    def run():
        try:
            j.result = fn(j.step)
            j.status, j.progress, j.msg = 'done', 1.0, 'готово'
        except Cancelled:
            j.status, j.msg = 'cancelled', 'отменено, модель не изменена'
        except Exception as e:
            import traceback
            traceback.print_exc()      # the cause stays in the server window / log for a bug report
            j.status, j.error, j.msg = 'error', '%s: %s' % (type(e).__name__, e) if not isinstance(e, ValueError) else str(e), 'ошибка'
    threading.Thread(target=run, daemon=True).start()
    return j


def get(jid):
    return JOBS[jid].info()


def cancel(jid):
    JOBS[jid].cancel()
    return {'ok': True}
