# CAS Compass landing site

This directory is the version-controlled source for `https://cascompass.ai`.
The Netlify project is `famous-sunflower-86f91c` (site ID
`060816d5-7153-43e3-9d8a-9428c58a420c`). The pre-import production deploy was
a three-file CLI upload with no Git source bundle.

The public legal text is deliberately a draft. `legal.html`, `privacy.html`,
and `terms.html` must remain `OPEN` and `FLAG_FOR_HUMAN_REVIEW` until qualified
counsel and the owner approve publication. A source merge or deploy must not be
treated as customer-production `ACCEPT`.

Netlify internally rewrites `/legal`, `/privacy`, `/terms`, and `/contact` to
their static HTML files with status 200. This preserves the exact requested URL
for the fail-closed claim-honesty collector.

Verify the source from the repository root:

```powershell
python -m unittest scripts.tests.test_cascompass_landing
python scripts/collect_claim_honesty_evidence.py --output C:\tmp\claim-honesty-draft.json --pretty
```

Production deployment must use the exact protected commit being released, not
the unrelated dirty root working directory. The Netlify access token is an
account secret and must not be committed.
