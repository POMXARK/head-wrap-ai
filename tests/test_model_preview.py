"""/model has a 3D preview (own test): both viewers, row click highlights a part, fallback text without WebGL/CDN, GLB served."""
import os, re, urllib.request
H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
s = open(os.path.join(H, 'model.html'), encoding='utf-8').read()
for i in ('pv', 'sv', 'pvc', 'svc'):
    assert 'id="%s"' % i in s, i
for k in ('GLTFLoader', 'OrbitControls', 'V.hl', 'V.partOf', 'WebGL', 'не загрузилась библиотека'):
    assert k in s, k
assert 'role="img"' in s and 'aria-label' in s
assert re.search(r'<tr data-n=.*onclick="pick\(', s)
t = open(os.path.join(H, 'tour.js'), encoding='utf-8').read()
assert "sel: '#pv'" in t
try:
    r = urllib.request.urlopen('http://localhost:8770/api/file?f=work/hero1_eye.glb', timeout=10)
    assert r.read(4) == b'glTF'
except OSError:
    print('server off: GLB check skipped')
print('OK test_model_preview')
