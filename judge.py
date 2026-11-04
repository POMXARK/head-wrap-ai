#!/usr/bin/env python3
"""Stage 6: the VLM judge compares two renders (A/B), it never lists defects of a category: judge.py a.png b.png
The prompt names no categories (a list makes the model report a defect in each of them, see docs/plan.md). The pair is
asked twice with A and B swapped; a verdict counts only when both orders agree (the model likes the first picture)."""
import base64
import json
import re
import sys
import app

PROMPT = ("Two renders of a 3D head model: picture 1 and picture 2. Which model looks more like a clean, correct human head "
          "(natural eyes, ears, neck, lips)? Answer only JSON: {\"better\": 1 or 2, \"reason\": \"one sentence\"}")


def pick(p, x, y):
    ans = app.ask(p, PROMPT, [x, y])
    m = re.search(r'"better"\s*:\s*"?([12])', ans)
    return int(m.group(1)) if m else None, ans


def compare(a_path, b_path):
    c = app.load()
    p = c['profiles'][c.get('active', 0)]
    a, b = [base64.b64encode(open(x, 'rb').read()).decode() for x in (a_path, b_path)]
    r1, t1 = pick(p, a, b)
    r2, t2 = pick(p, b, a)
    winner = 'A' if (r1, r2) == (1, 2) else 'B' if (r1, r2) == (2, 1) else 'unsure (order bias)'
    return winner, [t1, t2]


if __name__ == '__main__':
    w, t = compare(sys.argv[1], sys.argv[2])
    print(w)
    print(json.dumps(t, ensure_ascii=False, indent=1))
