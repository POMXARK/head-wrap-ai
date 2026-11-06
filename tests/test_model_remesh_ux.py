"""/model section 3 explains itself (own test): purpose text, live estimate, before/after counts, way back to the source file."""
import os
H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
s = open(os.path.join(H, 'model.html'), encoding='utf-8').read()
for k in ('Зачем:', 'id="est"', 'function est()', 'Что получится', 'было', 'Вернуться к исходному', 'function back(', 'не изменён', 'Ничего не изменено'):
    assert k in s, k
print('OK test_model_remesh_ux')
