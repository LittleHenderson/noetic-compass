# HELM_CUBE_TRAIN_20261022 — the sealed package for retraining the CTT on cube readings

What it does, in plain words: fine-tunes HELM's CTT translator (three copies A4-s1..s3 and the small twin A5-s1, each
starting from its c45 weights) to read a teaching line into a fact — thing, slot words, value, replaced value — as
POINTERS to the line's own words, never writing a word itself. Then it reads the held-back DEV lines and prints one
status word: `TRAIN_READY`, `TRAIN_NOT_READY` or `INCONCLUSIVE`.

Run on the GPU host (one AWS g5.xlarge, us-west-2; cap 3 USD):

    python3 -X utf8 -B run_cube.py --zip <this zip> --zip-sha256 <its sealed sha256> --out <dir>

Rules: `PREREGISTRATION_CUBE_TRAIN.precode.md` (sha256 `6e1afceb…`) and amendments A-CUBE-TRAIN-1..5 in the tksCAS
repository (`docs/working/helm_cube_oscillation_v1/`); frozen numbers in `FROZEN_CUBE_TRAIN.json`; data in `data/`
(manifest `DATA_MANIFEST_CUBE.json`); start weights in `weights/` (sha256 pinned). Laptop tests:
`python -B -m unittest discover -s tests_cube -t .` (standard library only). The owner wrote nothing; the approval is
the owner's choice "train the CTT first", recorded by the operator as `CUBE TRAIN at 3 USD` (A-TEACH2-17).
Claim status of everything here: `ENGINEERED-NOT-VALIDATED`.
