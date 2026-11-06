#!/usr/bin/env python3
"""Check the example assets against the schemas: python3 spec/check.py [asset.json ...] (default: spec/*.asset.json)."""
import glob, json, os, sys
import jsonschema
from referencing import Registry, Resource

HERE = os.path.dirname(os.path.abspath(__file__))
load = lambda n: json.load(open(os.path.join(HERE, n)))
reg = Registry().with_resources([(n, Resource.from_contents(load(n))) for n in ('asset.schema.json', 'op.schema.json')])
v = jsonschema.Draft202012Validator(load('asset.schema.json'), registry=reg)
bad = 0
for f in sys.argv[1:] or sorted(glob.glob(os.path.join(HERE, '*.asset.json'))):
    errs = sorted(v.iter_errors(json.load(open(f))), key=lambda e: list(e.path))
    print(('FAIL ' if errs else 'ok   ') + os.path.basename(f))
    for e in errs:
        print('   ', '/'.join(map(str, e.path)), e.message[:120]); bad += 1
sys.exit(1 if bad else 0)
