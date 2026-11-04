#!/usr/bin/env python3
"""Stage 3: landmarks of the face on the generated head and on the template (MediaPipe Face Mesh, Apache 2.0, local).
landmarks.py find-template wrapped.obj template/head_sub.obj atlas.png template/landmarks.json   (once per template)
landmarks.py targets target.glb front.png template/landmarks.json out.json                       (per generated head)
Template: front render of a textured template -> MediaPipe -> the front-most vertex under each point. Target: MediaPipe on
the Qwen front view (orthographic, the figure box = the bbox of the mesh, as pdm_project_views.project) -> x, y, and z from a
ray into the mesh. The pairs (template vertex, target point) go to wrap_fit as landmarks of the non-rigid ICP."""
import json
import os
import sys
import numpy as np
import trimesh
from PIL import Image, ImageDraw
from bake import read_uv_faces, read_v

# MediaPipe Face Mesh indices: eye corners, lids, brows, nose, mouth corners/lips, chin, cheeks
LM = {'eye_r_out': 33, 'eye_r_in': 133, 'eye_l_in': 362, 'eye_l_out': 263, 'lid_r_up': 159, 'lid_r_low': 145,
      'lid_l_up': 386, 'lid_l_low': 374, 'brow_r': 105, 'brow_l': 334, 'nose_tip': 1, 'nose_r': 98, 'nose_l': 327,
      'mouth_r': 61, 'mouth_l': 291, 'lip_up': 0, 'lip_low': 17, 'lip_in_up': 13, 'lip_in_low': 14, 'chin': 152}


def mesh_points(rgb):
    import mediapipe as mp
    with mp.solutions.face_mesh.FaceMesh(static_image_mode=True, max_num_faces=1, refine_landmarks=False) as fm:
        r = fm.process(rgb.astype(np.uint8))
    if not r.multi_face_landmarks:
        return None
    h, w = rgb.shape[:2]
    return np.array([[p.x * w, p.y * h] for p in r.multi_face_landmarks[0].landmark])


def render_front(W, F, col, size=1024):
    """orthographic front render; returns image, face-id buffer, (x0, x1, y0, y1) box mapping x,y -> pixels"""
    lo, hi = W.min(0), W.max(0)
    s = (size * 0.9) / max(hi[0] - lo[0], hi[1] - lo[1])
    ox, oy = size / 2 - (lo[0] + hi[0]) / 2 * s, size / 2 + (lo[1] + hi[1]) / 2 * s
    px = np.stack([W[:, 0] * s + ox, oy - W[:, 1] * s], 1)
    img, ids = Image.new('RGB', (size, size), (255, 255, 255)), Image.new('I', (size, size), -1)
    di, dd = ImageDraw.Draw(img), ImageDraw.Draw(ids)
    z = W[F].mean(1)[:, 2]
    for k in np.argsort(z):
        a, b, c = F[k]
        n = np.cross(W[b] - W[a], W[c] - W[a])
        if n[2] <= 0:
            continue
        poly = [tuple(px[i]) for i in (a, b, c)]
        di.polygon(poly, fill=tuple(int(x) for x in col[k] * 255))
        dd.polygon(poly, fill=int(k))
    return np.asarray(img), np.asarray(ids), (s, ox, oy)


def find_template(wrapped, template, atlas, out):
    W = read_v(wrapped)
    vt, FF = read_uv_faces(template)
    F = np.array([[p[0] for p in f] for f in FF])
    tex = np.asarray(Image.open(atlas).convert('RGB'))
    S = tex.shape[0]
    uv = np.array([vt[[p[1] for p in f]].mean(0) for f in FF])
    col = tex[np.clip(((1 - uv[:, 1]) * S).astype(int), 0, S - 1), np.clip((uv[:, 0] * S).astype(int), 0, S - 1)] / 255.
    img, ids, (s, ox, oy) = render_front(W, F, col)
    Image.fromarray(img).save(out.replace('.json', '.png'))
    P = mesh_points(img)
    if P is None:
        sys.exit('no face found in the template render')
    res = {}
    for name, i in LM.items():
        x, y = P[i]
        k = ids[int(round(y)), int(round(x))]
        if k < 0:
            continue
        # the vertex of the face under the pixel nearest to the point
        pts = W[F[k]]
        d = np.linalg.norm(np.stack([pts[:, 0] * s + ox, oy - pts[:, 1] * s], 1) - [x, y], axis=1)
        res[name] = int(F[k][d.argmin()])
    json.dump(res, open(out, 'w'))
    print('template landmarks', len(res), '->', out)


def targets(target, front, lm, out):
    """x, y of the Qwen front landmarks in mesh units (orthographic, figure box = mesh bbox), z from a ray into the mesh"""
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'corsairs-remake', 'tools'))
    import pdm_project_views as pv
    m = trimesh.load(target, force='mesh')
    lo, hi = m.vertices.min(0), m.vertices.max(0)
    f, (x0, x1, y0, y1), _ = pv.load_view(front)
    scale = 1024 / f.shape[0]
    small = np.asarray(Image.fromarray(f.clip(0, 255).astype(np.uint8)).resize((1024, 1024), Image.LANCZOS))
    P = mesh_points(small) / scale  # back to full-size pixels
    ids = json.load(open(lm))
    res = {}
    for name, v in ids.items():
        px, py = P[LM[name]]
        x = lo[0] + (px - x0) / (x1 - x0) * (hi[0] - lo[0])
        y = lo[1] + (y1 - py) / (y1 - y0) * (hi[1] - lo[1])
        hit, _, _ = m.ray.intersects_location([[x, y, hi[2] + 1]], [[0, 0, -1]], multiple_hits=False)
        if len(hit):
            res[name] = {'vertex': v, 'target': hit[0].tolist()}
    json.dump(res, open(out, 'w'), indent=1)
    print('target landmarks', len(res), '->', out)


if __name__ == '__main__':
    if sys.argv[1] == 'find-template':
        find_template(*sys.argv[2:6])
    else:
        targets(*sys.argv[2:6])
