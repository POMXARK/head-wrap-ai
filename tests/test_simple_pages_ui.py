"""UX rules (docs/ux-rules.md) for the plain windows /, /model, /review: shared ui.css, header, toasts, no alert/confirm, labels, one main action."""
import os, re, sys
H = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, H)
css = open(os.path.join(H, 'ui.css'), encoding='utf-8').read()
for need in ('prefers-color-scheme:dark', ':focus-visible', '[hidden]{display:none!important}', 'prefers-reduced-motion', '--acc', 'min-height:36px'):
    assert need in css, need
for f, ids in (('index.html', ('pr', 'lg', 'bsave', 'h-go')), ('model.html', ('f', 't', 'n', 'fc', 'res', 'pv', 'sv')), ('review.html', ('st', 'foc', 'cur', 'hist'))):
    h = open(os.path.join(H, f), encoding='utf-8').read()
    assert 'href="/ui.css"' in h and '<header class="top">' in h and 'lang="ru"' in h and 'viewport' in h, f
    assert 'alert(' not in h and 'confirm(' not in h and 'prompt(' not in h, f
    assert 'id="toasts"' in h and 'class="status"' in h, f
    for i in ids:
        assert 'id="%s"' % i in h, (f, i)
    # every text field has a label
    for m in re.finditer(r'<(?:input|select)[^>]*\bid="(\w+)"[^>]*>', h):
        if 'type="radio"' in m.group(0):
            continue
        assert 'for="%s"' % m.group(1) in h, (f, m.group(1))
    assert h.count('btn primary"') <= 4
import app
assert app.PAGE.count('id="bsave"') == 1 and 'id="h-go"' in app.PAGE
print('PASS test_simple_pages_ui')
