"""edit.html: the tools of the sculpt/texture/UV extension are present and follow the UX rules (static checks)"""
import os
import re
HERE = os.path.join(os.path.dirname(__file__), '..')
h = open(os.path.join(HERE, 'edit.html'), encoding='utf-8').read()
for k in ('inflate', 'flatten', 'pinch', 'scale', 'displace', 'smooth'):
    assert re.search(r'\b%s:\[' % k, h), 'op button ' + k
for i in ('t-grab', 't-paint', 'v-mesh', 'v-tex', 'v-uv', 'uvc', 'sym', 'tmg', 'bte', 'btu', 'btr', 'bum', 'bus2', 'bur'):
    assert 'id="%s"' % i in h, i
for c in ("e.code", "KeyG", "KeyP"):
    assert c in h, c
assert 'alert(' not in h
assert len(re.findall(r'class="btn primary', h)) == 2
assert "$('bum').disabled" in h or "$(b).disabled=!nsel" in h, 'UV buttons are disabled without a selection, with the reason in the text'
assert 'У этой головы нет' in h
print('PASS test_edit_tools_ui')
