"""Agent 'suggest' for an area (ours, task C2). It only PROPOSES: tries smooth with several parameters on a copy of the mesh
inside the selection, scores each with a local critic and returns ranked proposals (common critic format, critics.py).
Local critic (no reference needed): roughness = mean |v - mean(neighbours)| of the area vertices (lower is better), and
shrink = mean displacement of the area vertices (a smoothing that eats the shape is bad). cost = roughness/roughness0 + SHRINK_W*shrink/edge.
Proposals never touch the asset; the user applies one (by='agent' in the journal)."""
import numpy as np
import ops

SHRINK_W = 2.0
CANDIDATES = [{'iterations': i, 'lam': l} for i in (1, 2, 4, 8, 16) for l in (0.3, 0.5)]


def area_metrics(V0, V, F, w):
    """roughness of V and shrink relative to V0 inside the area (w > 0)"""
    m = w > 0
    L = ops.laplacian_avg(F, len(V))
    rough = float(np.linalg.norm((L @ V - V)[m], axis=1).mean())
    e = np.linalg.norm(V[F[:, 0]] - V[F[:, 1]], axis=1).mean()
    shrink = float(np.linalg.norm((V - V0)[m], axis=1).mean() / e)
    return rough, shrink


def suggest(V, F, w, top=3):
    V = np.asarray(V, float)
    F = np.asarray(F, int)
    w = np.asarray(w, float)
    if not (w > 0).any():
        raise ValueError('область пуста: выделите место, для которого нужен совет')
    r0, _ = area_metrics(V, V, F, w)
    out = []
    for p in CANDIDATES:
        r, s = area_metrics(V, ops.apply('smooth', V, F, w, p), F, w)
        out.append({'op': 'smooth', 'params': p, 'cost': round(r / max(r0, 1e-12) + SHRINK_W * s, 4),
                    'before': {'roughness': round(r0, 5)}, 'after': {'roughness': round(r, 5), 'shrink': round(s, 4)}})
    out.sort(key=lambda x: x['cost'])
    best = out[:top]
    for i, b in enumerate(best):
        b['why'] = ('шероховатость %.0f%% от исходной, область сместилась на %.2f длины ребра' %
                    (100 * b['after']['roughness'] / max(r0, 1e-12), b['after']['shrink']))
    return {'agent': 'suggest', 'baseline_roughness': round(r0, 5), 'proposals': best,
            'note': 'советует, не применяет; если шероховатости нет (baseline≈0), лучший совет — ничего не менять'}
