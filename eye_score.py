#!/usr/bin/env python3
"""Score of the eyes of a head glb without running the game (ours): an offline z-buffer render of the model with the
patch of the eyes, and measures read off the buffers. It is the quality gate of the head-wrap pipeline.

eye_score.py [glb] [eye_open.json] [--png out.png] [--json out.json]   exit code 1 if a check fails

Views: front and 25 degrees to both sides (the way the player sees the head). Per eye and view:
  visible   share of the projected patch not hidden by the faces of the head (z-buffer); < 0.9 = the eye is buried
  through   share of the patch pixels where nothing is drawn (the background shows through the hole)
  aperture  height / width of the visible eye (the open eye is 0.28-0.40; < 0.25 = sleepy, the lids cover it)
  picture   share of the visible eye pixels that are not skin (sclera, iris): the eye is seen, not a skin patch
  iris      dark pixels in the eye (the iris and the pupil are in the picture)
Under the eye (the fold and the circles):
  back      visible faces turned away from the camera (a flipped wall of the pit)
  step      largest depth jump between neighbouring pixels (a wall); > 0.006 = a fold
  shade     largest jump of the lit brightness on the skin under the eye outside the patch (an arc, a round spot)
  depth     depth range of the cheek under the eye (a pit); > 0.04 = a dish
  gaps      pixels beside the eye where nothing is drawn (a hole in the head)
  blocky    share of the cheek pixels equal to their neighbour: the texture is magnified (cramped UV of the old socket)
Score 0-100: the weighted share of passed checks; the thresholds are THRESH."""
import sys
import json
import numpy as np
import trimesh

THRESH = {'visible': 0.9, 'through': 0.03, 'aperture': (0.27, 0.45), 'picture': 0.5, 'back': 0, 'step': 0.006,
          'shade': 25.0, 'depth': 0.04, 'gaps': 0, 'blocky': 0.6}
RES = 0.0005  # head units per pixel
LIGHT = np.array([-0.35, 0.55, 0.75])
LIGHT = LIGHT / np.linalg.norm(LIGHT)


def sample(tex, uv):
    h, w = tex.shape[:2]
    x = np.clip((uv[:, 0] % 1.0) * w, 0, w - 1).astype(int)
    y = np.clip((1 - uv[:, 1]) * h, 0, h - 1).astype(int)
    return tex[y, x]


def mesh_arrays(geom):
    tex = np.array(geom.visual.material.baseColorTexture.convert('RGB'), float)
    return geom.vertices.copy(), geom.faces, geom.vertex_normals.copy(), geom.visual.uv, tex


def render(parts, box, yaw):
    """z-buffer of the parts (list of (V, F, N, UV, tex, id)) seen along -z after turning the head by yaw degrees."""
    x0, x1, y0, y1 = box
    W, H = int((x1 - x0) / RES), int((y1 - y0) / RES)
    zb = np.full((H, W), -9.0)
    idb = np.full((H, W), -1, int)
    nb = np.zeros((H, W, 3))
    col = np.zeros((H, W, 3))
    a = np.radians(yaw)
    R = np.array([[np.cos(a), 0, np.sin(a)], [0, 1, 0], [-np.sin(a), 0, np.cos(a)]])
    for V, F, N, UV, tex, pid in parts:
        Vr, Nr = V @ R.T, N @ R.T
        for f in F:
            p = Vr[f]
            if p[:, 0].max() < x0 or p[:, 0].min() > x1 or p[:, 1].max() < y0 or p[:, 1].min() > y1:
                continue
            px = (p[:, 0] - x0) / RES
            py = (y1 - p[:, 1]) / RES
            bx0, bx1 = max(int(px.min()), 0), min(int(px.max()) + 1, W - 1)
            by0, by1 = max(int(py.min()), 0), min(int(py.max()) + 1, H - 1)
            if bx1 < bx0 or by1 < by0:
                continue
            gx, gy = np.meshgrid(np.arange(bx0, bx1 + 1) + 0.5, np.arange(by0, by1 + 1) + 0.5)
            d = (py[1] - py[2]) * (px[0] - px[2]) + (px[2] - px[1]) * (py[0] - py[2])
            if abs(d) < 1e-9:
                continue
            l0 = ((py[1] - py[2]) * (gx - px[2]) + (px[2] - px[1]) * (gy - py[2])) / d
            l1 = ((py[2] - py[0]) * (gx - px[2]) + (px[0] - px[2]) * (gy - py[2])) / d
            l2 = 1 - l0 - l1
            m = (l0 >= -1e-6) & (l1 >= -1e-6) & (l2 >= -1e-6)
            if not m.any():
                continue
            z = l0 * p[0, 2] + l1 * p[1, 2] + l2 * p[2, 2]
            sub = zb[by0:by1 + 1, bx0:bx1 + 1]
            win = m & (z > sub)
            if not win.any():
                continue
            L = np.stack([l0[win], l1[win], l2[win]], 1)
            n = L @ Nr[f]
            n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-9)
            c = sample(tex, L @ UV[f])
            ys, xs = np.where(win)
            sub[ys, xs] = z[win]
            idb[by0:by1 + 1, bx0:bx1 + 1][ys, xs] = pid
            nb[by0:by1 + 1, bx0:bx1 + 1][ys, xs] = n
            col[by0:by1 + 1, bx0:bx1 + 1][ys, xs] = c
    return zb, idb, nb, col


def score(glb, polys, png=None):
    sc = trimesh.load(glb)
    head = mesh_arrays(sc.geometry['geometry_0'])
    patch = mesh_arrays(sc.geometry['geometry_1'])
    skin = np.median(patch[4][:6, :6].reshape(-1, 3), 0)
    res, shots = {}, []
    for k, p in polys.items():
        p = np.array(p)
        c = p.mean(0)
        w, h = np.ptp(p[:, 0]), np.ptp(p[:, 1])
        box = (c[0] - 1.3 * w, c[0] + 1.3 * w, c[1] - 3.5 * h, c[1] + 2.0 * h)
        sel = (np.abs(patch[0][:, 0] - c[0]) < w) & (np.abs(patch[0][:, 1] - c[1]) < h)
        cz = float(patch[0][sel][:, 2].mean()) if sel.any() else 0.0
        for yaw in (0, -25, 25):
            # the box follows the eye when the head turns (x' = x cos + z sin)
            a = np.radians(yaw)
            dx = (c[0] * np.cos(a) + cz * np.sin(a)) - c[0]
            box = (c[0] - 1.3 * w + dx, c[0] + 1.3 * w + dx, c[1] - 3.5 * h, c[1] + 2.0 * h)
            parts = [(*head, 0), (*patch, 1)]
            zb, idb, nb, col = render(parts, box, yaw)
            pz, pid, _, _ = render([(*patch, 1)], box, yaw)[0:2] + (None, None)
            eye_all = pid == 1
            eye_vis = idb == 1
            m = {}
            m['visible'] = float(eye_vis.sum() / max(eye_all.sum(), 1))
            hole = eye_all & (idb == -1)
            m['through'] = float(hole.sum() / max(eye_all.sum(), 1))
            ys, xs = np.where(eye_vis)
            # the box holds both eyes at an angle: only the eye of this box (the largest blob) is measured; an eye
            # mostly hidden by the nose (< 50 % of its blob visible) is not measured (nan = not applicable)
            from scipy import ndimage as ndi
            lab, n = ndi.label(ndi.binary_dilation(eye_vis, iterations=3))
            if n:
                big = lab == (1 + int(np.argmax(ndi.sum(eye_vis, lab, range(1, n + 1)))))
                vis_b = eye_vis & big
                lab2, n2 = ndi.label(ndi.binary_dilation(eye_all, iterations=3))
                full_b = eye_all & (lab2 == lab2[vis_b][0])
                ys, xs = np.where(vis_b)
                m['aperture'] = float((np.ptp(ys) + 1) / (np.ptp(xs) + 1)) if len(ys) > 10 else 0.0
                if vis_b.sum() < 0.5 * full_b.sum():
                    m['aperture'] = float('nan')
            else:
                m['aperture'] = 0.0
            cc = col[eye_vis]
            m['picture'] = float((np.linalg.norm(cc - skin, axis=1) > 40).mean()) if len(cc) else 0.0
            m['iris'] = float((cc.mean(1) < 70).mean()) if len(cc) else 0.0
            # the cheek under the eye: the zone below the patch, as wide as the eye
            xs_, ys_ = np.where(eye_all)[1], np.where(eye_all)[0]
            ybot = ys_.max() if len(ys_) else int((box[3] - c[1]) / RES)
            zone = np.zeros_like(eye_all)
            zone[ybot + int(0.2 * h / RES):int((box[3] - c[1] + 2.8 * h) / RES),
                 int((0.75 * w) / RES):int((1.85 * w) / RES)] = True
            zone &= (idb == 0)
            if eye_all.any():  # the nose or the silhouette beside the cheek is not the cheek: depth near the eye only
                zone &= np.abs(zb - np.median(pz[eye_all])) < 0.07
            m['back'] = int((nb[zone][:, 2] < 0.05).sum())
            dzy = np.abs(np.diff(zb, axis=0))[:, :-1]
            dzx = np.abs(np.diff(zb, axis=1))[:-1, :]
            dz = np.maximum(dzy, dzx)
            from scipy import ndimage as ndi
            zin = ndi.binary_erosion(zone, iterations=8)  # the edge of the zone is the nose or the silhouette: an occlusion, not a fold
            ok = zin[:-1, :-1] & zin[1:, 1:] & (zb[:-1, :-1] > -8)
            m['step'] = float(dz[ok].max()) if ok.any() else 0.0
            lit = col * (0.35 + 0.65 * np.clip(nb @ LIGHT, 0, 1))[..., None]
            L = lit.mean(2)
            gl = np.maximum(np.abs(np.diff(L, axis=0))[:, :-1], np.abs(np.diff(L, axis=1))[:-1, :])
            m['shade'] = float(np.percentile(gl[ok], 99.5)) if ok.any() else 0.0
            zz = zb[zone]
            if len(zz) > 20:  # a dish, not a tilted cheek: the plane of the zone is taken out before the range
                yy, xx = np.nonzero(zone)
                A = np.stack([np.ones(len(xx)), xx * RES, yy * RES], 1)
                resid = zz - A @ np.linalg.lstsq(A, zz, rcond=None)[0]
                m['depth'] = float(np.percentile(resid, 98) - np.percentile(resid, 2))
            else:
                m['depth'] = 0.0
            # pixels of the face with nothing drawn (a hole in the head) beside the eye
            from scipy import ndimage as ndi
            gap = (idb == -1) & ~ndi.binary_dilation(eye_all, iterations=6)
            # only holes inside the head: skin on both sides in the row (the silhouette of a turned head is not a hole)
            sk = idb == 0
            gap &= np.maximum.accumulate(sk, axis=1) & np.maximum.accumulate(sk[:, ::-1], axis=1)[:, ::-1]
            gap[:, :4] = gap[:, -4:] = gap[:4] = gap[-4:] = False
            m['gaps'] = int(gap.sum())
            # blocky texture: the texels of the skin under the eye must not be magnified (texels per pixel of the render)
            tx = col[zone]
            m['blocky'] = float(np.mean(np.abs(np.diff(col[:, :, 0], axis=1))[zone[:, :-1]] < 0.5)) if zone.any() else 0.0
            res[f'{k}@{yaw}'] = m
            if yaw == 0:
                shots.append(np.clip(lit, 0, 255).astype(np.uint8))
    if png:
        from PIL import Image
        Image.fromarray(np.hstack(shots)).save(png)
    return res


def check(m):
    t = THRESH
    return {'visible': m['visible'] >= t['visible'], 'through': m['through'] <= t['through'],
            'aperture': bool(np.isnan(m['aperture'])) or t['aperture'][0] <= m['aperture'] <= t['aperture'][1], 'picture': m['picture'] >= t['picture'],
            'back': m['back'] <= t['back'], 'step': m['step'] <= t['step'], 'shade': m['shade'] <= t['shade'],
            'depth': m['depth'] <= t['depth'], 'gaps': m['gaps'] <= t['gaps'], 'blocky': m['blocky'] <= t['blocky']}


def main():
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    png = sys.argv[sys.argv.index('--png') + 1] if '--png' in sys.argv else None
    glb = a[0] if a else 'work/hero1_eye.glb'
    polys = json.load(open(a[1] if len(a) > 1 else 'work/eye_open.json'))
    res = score(glb, polys, png)
    keys = ['visible', 'through', 'aperture', 'picture', 'iris', 'back', 'step', 'shade', 'depth', 'gaps', 'blocky']
    print('%-8s' % 'view' + ''.join('%10s' % k for k in keys))
    passed = total = 0
    for v, m in res.items():
        ok = check(m)
        passed += sum(ok.values())
        total += len(ok)
        print('%-8s' % v + ''.join(('%10.3f' % m[k]) + ('' if ok.get(k, True) else '!') if False else
                                   ('%9.3f%s' % (m[k], '' if ok.get(k, True) else '!')) for k in keys))
    s = 100.0 * passed / total
    print(f'score {s:.0f}/100 ({passed}/{total} checks)')
    if '--json' in sys.argv:
        json.dump({'score': s, 'views': res}, open(sys.argv[sys.argv.index('--json') + 1], 'w'), indent=1)
    sys.exit(0 if passed == total else 1)


if __name__ == '__main__':
    main()
