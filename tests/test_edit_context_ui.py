"""Static check of the context-panel rules (docs/ux-rules.md §10): panels by view, [ ] brush size, dblclick slider reset, one undo."""
import os
h = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'edit.html'), encoding='utf-8').read()
for need in ('function ctxPanels', "BracketLeft", "BracketRight", "dblclick", "defaultValue", 'id="s-edit"', 'MIDDLE=THREE.MOUSE.PAN',
             'onclick="undoAny(false)"', 'onclick="undoAny(true)"', "ctxPanels();\n</script>"):
    assert need in h, need
assert "hist('undo')\">" not in h.split('<aside')[0], 'header undo must be context-aware'
print('PASS test_edit_context_ui')
