# -*- coding: utf-8 -*-
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
src = Path('body.tex').read_text(encoding='utf-8')
lines = src.split('\n')
probes = ['not authority', 'wall of resentment', 'her parents', 'to be impreg',
          'The prescrip', '340M settlement', 'Unaware', 'language_conformance.rs::set_theory',
          'cardinality_assertion']
for pr in probes:
    idxs = [i for i, l in enumerate(lines) if pr in l][:2]
    for i in idxs:
        lo = max(0, i - 4)
        print(f'=== {pr!r} at line {i+1}:')
        for j in range(lo, min(len(lines), i + 2)):
            print(f'  {j+1}: {lines[j][:105]}')
