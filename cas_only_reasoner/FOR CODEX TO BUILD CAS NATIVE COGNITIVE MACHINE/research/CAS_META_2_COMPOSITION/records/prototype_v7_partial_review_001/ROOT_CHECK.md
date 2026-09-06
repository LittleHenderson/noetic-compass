# Independent main-agent check

The main agent repeated the unchanged extractor's 23 standard-library tests
with Python 3.14.0; all passed in 0.052 seconds, exit 0:

```text
C:/Python314/python.exe -I -S -B records/prototype_v7_partial_review_001/test_extract.py
```

This was a synthetic helper check, not another extraction or semantic audit.
The actual extraction receipt's SHA256 was independently confirmed as
`9bf40771df6dd7f67189d402d6bcfd8e05bd8cd997b71a6825fff21da105ae98`.
The later main-agent training-record recount used the unchanged `Packet` helper
to recheck every extracted member against the externally pinned ZIP before and
after its training-record checks. That separate receipt is
`452705ca332f9cf8b42c8815c3c08f031ec73ba4fc443a51797679acddc62d76`.

The experiment remains failed/incomplete. Byte verification and training-record
verification do not turn missing native outcomes into completed results.
