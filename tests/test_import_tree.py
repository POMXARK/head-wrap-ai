"""import dialog is an outliner tree (group > file > part), a picked part drives the hidden dn/dpart, the guide explains each field"""
import os
D = os.path.join(os.path.dirname(__file__), '..')
e = open(os.path.join(D, 'edit.html'), encoding='utf-8').read()
t = open(os.path.join(D, 'tour.js'), encoding='utf-8').read()
for k in ('id="tree"', 'id="picked"', 'function pickPart', 'function buildTree', 'id="sch"', 'id="dn"', 'id="dpart"'):
    assert k in e, k
for k in ("sel: '.prevbox'", "sel: '#tree'", "sel: '#picked'", "sel: '#sc'", "sel: '#brp'"):
    assert k in t, k
print('PASS test_import_tree')
