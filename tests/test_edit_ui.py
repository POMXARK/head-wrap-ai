"""edit.html: UX rules of the redesign (static checks; the behaviour is checked by a headless smoke run, see docs/ux-review.md)."""
import os, re

HERE = os.path.join(os.path.dirname(__file__), '..')

if __name__ == '__main__':
    h = open(os.path.join(HERE, 'edit.html'), encoding='utf-8').read()
    assert 'alert(' not in h, 'errors go to toasts, not alert()'
    assert '[hidden]{display:none!important}' in h, 'hidden must win over display:flex'
    assert 'prefers-color-scheme:dark' in h and 'prefers-reduced-motion' in h
    assert 'min-height:36px' in h, 'touch/click targets >= 36px'
    assert ':focus-visible' in h, 'visible keyboard focus'
    for k in ('Esc', 'aria-pressed', 'aria-live'):
        assert k in h, k
    assert 'NOGL' in h, 'graceful fallback when WebGL is unavailable'
    assert len(re.findall(r'class="btn primary', h)) == 2, 'one primary action per section (edit, replace)'
    assert 'disabled' in h and '$(\'ba\').disabled=!nsel' in h, 'Apply is disabled without a selection'
    print('test_edit_ui OK')
