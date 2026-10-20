# CTT-1 custodian procedure — the sealed human English exam (E-HUMAN-W)

The custodian is NOT the builder. The builder (any agent that wrote this package) never sees the writer sheets, the
writers' sentences, the drawn records, the sealed exam file or the sealed 98. Plain words throughout.

## 0. What the custodian needs

- The final sealed zip `HELM_CTT_20261019_SOURCE_CTT.zip` and its full sha256 (from `ZIP_SHA256.txt` and
  `PACKAGE_FREEZE_CTT.json`).
- `APPROVAL_RECORD_CTT.json` (it quotes the owner's verbatim pre-approval line and names that zip sha256).
- Three writers (owner pick Q4, "me plus two"): **W1 = the owner**, **W2 = person B**, **W3 = person C**. Agents may
  not write. The writers' names go into the seal record; this package holds only the empty format.

## 1. The seed (coordinator's custody addition, 2026-10-19)

`seed_source = sha256( UTF-8( OWNER_LINE + ":" + ZIP_SHA256 ) )`

- OWNER_LINE is, byte for byte (three spaces after "FOLLOWING:"):
  `I PRE-APPROVE BOTH OF THE FOLLOWING:   Two sign lines are coming: X-REAL at 1 USD, and the transformer training at 8 USD.`
  Its own sha256: `2a8a6f864a9e6d5349a048232813506c8efd51c50fdfde0f70af1e396fe56e00`.
- ZIP_SHA256 is the full lowercase hex sha256 of the final sealed zip. No seed can exist before the zip bytes are
  final.
- Bands: CW 1,920,000,001–1,921,000,000 (singles, k = seed_source characters 0–15 as hex); CD
  1,922,000,001–1,923,000,000 (dialogues, k = characters 16–31). First slot = k mod 1,000,000. A refused draw steps
  the slot by +1 inside its band; a full band = STOP (never another band). Every step goes to
  `SEED_DERIVATION_CTT.json`. These bands sit above every band used so far (X4 1,858–1,863 M; X5 1,878–1,881 M;
  X-REAL 1,898–1,905 M).

## 2. Draw the contents (laptop, custodian folder outside every repo)

```
cd <custody work dir>    (an extracted copy of the sealed zip; run from its HELM_CTT_20261019 folder)
python -X utf8 -B -m custody.draw_contents --approval <APPROVAL_RECORD_CTT.json> --out <custody work dir>/work
```
Output: `CONTENTS_CTT.json` (the gold records and the plain-words prompts), `WRITER_SHEET_W1.txt`,
`WRITER_SHEET_W2.txt`, `WRITER_SHEET_W3.txt`, `SEED_DERIVATION_CTT.json`.
128 single turns (W1: S001–S064; W2: S065–S096; W3: S097–S128) and 16 short dialogues (W2: D01–D08; W3: D09–D16),
3 to 5 turns each.

## 3. The writers write (the slot for the human sentences)

- Give each writer ONLY their own sheet and this one instruction (printed at the top of the sheet): read the
  situation, then type how YOU would say it to HELM, in your own everyday words.
- Show NO example sentences, no part of this package, no generator template, no earlier exam. (So the exam is not
  primed toward the reader's own sentence shapes.)
- Each writer returns a plain text file: one line per prompt, `id<TAB>sentence`. Any spelling, slang, typos and
  contractions are welcome; that is the point.
- Writers may be told the exam is about a kitchen assistant. They are not told what the model or the reader can read.

## 4. Seal (before the run)

```
python -X utf8 -B -m custody.seal_exam seal --contents work/CONTENTS_CTT.json --typed W1.tsv --typed W2.tsv
    --typed W3.tsv --writers "W1=<owner's name>" "W2=<name>" "W3=<name>" --approval <APPROVAL_RECORD_CTT.json>
    --out <exam dir>
```
Checks: every prompt answered once; no tab or line break inside a sentence; 1–400 characters; no CAS notation
(`⟦ ⟧ Ω Θ Φ ^digit`). Writes, create-only: `E_HUMAN_W_CTT.json` (LF, UTF-8), `E_HUMAN_W_SEAL_RECORD.json` (raw and
LF sha256, seed source, zip sha256, writers, counts, the typed files' sha256), `E_HUMAN_W_SEALED.flag`.

Hold-out rules: the custodian keeps the exam folder off every repo and every shared drive the builders use. The exam
reaches the GPU host as its own carrier (top folder `ehumanw`) holding exactly `E_HUMAN_W_CTT.json` and
`E_HUMAN_W_SEAL_RECORD.json`. The sealed 98 reaches the host as a carrier (top folder `sealed98`) holding exactly
`real_heldout_unparseables_98.jsonl` (sha256 `e269a448cf1d087aa6b98436dadfbfdefa60216346f0f886659f0f9d7dd61cfe`).

## 5. Leakage (automatic on the host)

The host's data build drops every TRAINING row that equals an exam sentence or shares an 8-word sequence with one
(E-HUMAN-W, the sealed 98, the six NO-HARM exams), never an exam row; it records counts and the sha256 of the dropped
list only (`LEAKAGE_CTT.json`), and re-checks that 0 exact and 0 eight-word overlaps remain.

## 6. After the run

```
python -X utf8 -B -m custody.seal_exam confirm --record <exam dir>/E_HUMAN_W_SEAL_RECORD.json
    --exam <exam dir>/E_HUMAN_W_CTT.json --out <exam dir>/E_HUMAN_W_SEAL_CONFIRM.json
```
The confirm file (raw and LF hashes unchanged) is the `exam_seal` input of the frozen reader. The exam is then spent.

## 7. Byte traps

Every file is hashed raw and LF-normalized; the receiver checks raw. Files are written `.partial` then renamed.
UTF-8 with `-X utf8`. Never open the exam in an editor that rewrites line ends (the lexicon-v2 split script's CRLF
hashes differed from LF hashes).
