#!/usr/bin/env python3
"""Stage 6 (first version): the VLM judge of a render: judge.py render.png [--profile N]
Asks the active profile of app.py (Ollama) for defects as JSON; the answer is cached in work/cache."""
import base64
import sys
import app

PROMPT = ("This is a 3D render of a human head (front, three-quarter, side). List visible defects of the model: "
          "eyes (concave, missing), ears (broken, flat), neck/skin texture (wrong colour, stripes), hair (skin patches), "
          "lips/mouth (misplaced), nose. Answer only JSON: {\"defects\":[{\"part\":str,\"problem\":str,\"severity\":1-5}],"
          "\"overall\":1-10}")


def main():
    c = app.load()
    p = c['profiles'][c.get('active', 0)]
    img = base64.b64encode(open(sys.argv[1], 'rb').read()).decode()
    print(app.ask(p, PROMPT, img))


if __name__ == '__main__':
    main()
