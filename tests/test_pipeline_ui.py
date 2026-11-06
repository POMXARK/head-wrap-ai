"""pipeline.html: UX rules of the redesign (static checks) + page is served through pipeline.PAGE."""
import os, sys, re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import pipeline

if __name__ == '__main__':
    h = pipeline.PAGE
    assert 'alert(' not in h, 'toasts instead of alert()'
    assert '[hidden]{display:none!important}' in h and 'prefers-color-scheme:dark' in h and ':focus-visible' in h
    assert len(re.findall(r'class="btn primary', h)) >= 2 and h.count('btn primary" id="b-build"') == 1, 'one main action: build'
    assert 'confirmGo' in h and 'id="ask"' in h, 'overwriting game files asks for confirmation'
    assert "disabled=!!s.running" in h, 'buttons are disabled while a step runs'
    for i in ('st', 'sc', 'im', 'mi', 'mv', 'mv2', 'b2', 'vs', 'vs2', 'vt', 'vn', 'opts', 'lg', 'mdl', 'pill'):
        assert 'id="%s"' % i in h, i
    assert 'id="stale"' in h, 'stale-scores banner is kept (B3.3)'
    print('test_pipeline_ui OK')
