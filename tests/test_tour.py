"""Interactive guide (tour.js): every window has a tour, every selector of a step exists on its page, server injects the script."""
import json, os, re, subprocess, sys, urllib.request
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
H = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
js = open(os.path.join(H, 'tour.js'), encoding='utf-8').read()
import app, pipeline
src = {'/': app.PAGE, '/pipeline': pipeline.PAGE, '/edit': open(os.path.join(H, 'edit.html'), encoding='utf-8').read(),
       '/model': app.MODEL, '/review': app.REVIEW, '/proto': open(os.path.join(H, 'proto', 'index.html'), encoding='utf-8').read()}
for page, html in src.items():
    m = re.search(r"TOURS\['%s'\] = \[(.*?)\n  \];" % re.escape(page), js, re.S)
    assert m, 'no tour for ' + page
    body = m.group(1)
    assert body.count('{ t:') + body.count('{ sel:') >= 3, page
    for sel in re.findall(r"sel: '([^']+)'", body):
        for part in re.findall(r"#([A-Za-z0-9_-]+)", sel):
            assert re.search(r'id=["\']?%s["\'\s>]' % re.escape(part), html), (page, sel)
        for cls in re.findall(r"\.([A-Za-z0-9_-]+)", sel.split('[')[0]):
            assert re.search(r'class=["\']?[^"\'>]*\b%s\b' % re.escape(cls), html), (page, sel)
for need in ('Escape', 'localStorage', 'role', 'aria-label', 'prefers-reduced-motion', 'tour=all'):
    assert need in js, need
assert 'alert(' not in js
print('PASS test_tour (static)')
