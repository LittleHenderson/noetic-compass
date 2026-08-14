# -*- coding: utf-8 -*-
import pymupdf
import sys

sys.stdout.reconfigure(encoding='utf-8')
doc = pymupdf.open('manuscript.pdf')
flags = [(96, 'authority.'), (141, 'together.'), (288, 'operator'),
         (289, '÷)'), (310, 'principled'), (322, 'substrate)'),
         (381, 'second)'), (400, 'coverage'), (598, '→Knowi'),
         (626, ';'), (763, 'language_conformance'), (764, 'test_v78')]
for pno, word in flags:
    words = doc[pno - 1].get_text('words')
    cands = [w for w in words if word.rstrip('.') .rstrip(')') in w[4]]
    if not cands:
        cands = [max(words, key=lambda w: w[2])]
    w = max(cands, key=lambda w: w[2])
    line = ' '.join(x[4] for x in sorted(words, key=lambda t: t[0]) if abs(x[1] - w[1]) < 3)
    print(f'p{pno} [{w[0]:.0f},{w[2]:.0f}]: {line[:130]}')
