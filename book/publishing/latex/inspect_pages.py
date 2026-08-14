# -*- coding: utf-8 -*-
import pymupdf
import sys

sys.stdout.reconfigure(encoding='utf-8')
doc = pymupdf.open('manuscript.pdf')
for pno in [8, 96, 141, 207, 208, 288, 289, 290, 310, 322, 381, 400, 598,
            623, 626, 627, 631, 763, 764]:
    p = doc[pno - 1]
    words = p.get_text('words')
    odd = pno % 2 == 1
    off = []
    for w in words:
        if odd and (w[2] > 396.5 or w[0] < 67):
            off.append(w)
        if not odd and (w[2] > 365 or w[0] < 35.5):
            off.append(w)
    for w in off[:2]:
        line = ' '.join(x[4] for x in words if abs(x[1] - w[1]) < 3)
        print(f'p{pno}: {w[4][:22]!r} x=[{w[0]:.0f},{w[2]:.0f}] | {line[:90]}')
