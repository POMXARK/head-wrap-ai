"""workspace tabs in /edit (Blender-style): model panel is embedded, no separate nav links to /model"""
import os
D = os.path.join(os.path.dirname(__file__), '..')
rd = lambda n: open(os.path.join(D, n), encoding='utf-8').read()
e = rd('edit.html')
for k in ('id="ws-edit"', 'id="ws-model"', 'function setWs', "'/model?embed=1'", 'body.wsm'):
    assert k in e, k
for n in ('index.html', 'review.html', 'edit.html'):
    assert 'href="/model"' not in rd(n), n
assert "'/model'," not in rd('tour.js').split('TOURS = {}')[0]
assert 'embed=1' in rd('model.html')
print('PASS test_workspaces')
