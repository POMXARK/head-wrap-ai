"""model operations run as background jobs (own test): POST returns a job, GET ?job= reports state; auto texture size; one closest_point call."""
import json, os, sys, time, urllib.request
H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
m = open(os.path.join(H, 'model.py'), encoding='utf-8').read()
assert m.count('closest_point(old, pts)') == 1 and 'def auto_size' in m
u = 'http://localhost:8770/api/model'
def post(d): return json.load(urllib.request.urlopen(urllib.request.Request(u, json.dumps(d).encode()), timeout=10))
j = post({'op': 'nope', 'target': 'work/hero1_eye.glb', 'node': 'x'})['job']
for _ in range(20):
    q = json.load(urllib.request.urlopen(u + '?job=' + j, timeout=10))
    if q['state'] == 'done': break
    time.sleep(.3)
assert q['state'] == 'done' and q['ok'] is False and 'unknown op' in q['error'], q
out = os.path.join(H, 'work', '_job_test.glb')
j = post({'op': 'remesh', 'target': 'work/hero1_eye.glb', 'node': 'ponytail', 'faces': '800', 'out': 'work/_job_test.glb'})['job']
t = time.time()
while time.time() - t < 120:
    q = json.load(urllib.request.urlopen(u + '?job=' + j, timeout=10))
    if q['state'] == 'done': break
    time.sleep(.5)
assert q['state'] == 'done' and q['ok'] and os.path.exists(out), q
os.remove(out)
print('OK test_model_job %.1fs' % q['elapsed'])
