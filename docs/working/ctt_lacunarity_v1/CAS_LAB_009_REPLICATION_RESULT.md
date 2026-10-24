# CAS-LAB-009 — Dose-0.20 replication: safe on all three seeds, efficacy bar met on two (2026-10-24)

Status: **preregistered replication, AWS-evaluated, mixed result.** The frozen rule required the dose-0.20 setting to
hold **both** conditions on the replication seeds: composite within 0.02 of that seed's baseline **and** notation gain
≥ 0.051125. It does not: safety holds everywhere, the gain falls short on A4-s3.

## 1. The three seeds at dose 0.20

| Seed | Baseline composite | Dose-0.20 composite | Δ composite | Internal gain | Gain bar | Result |
|---|---:|---:|---:|---:|---|---|
| A4-s1 | 0.231817 | 0.225594 | −0.006223 | 0.054952 | pass | **PASS** |
| A4-s2 | 0.235008 | 0.239805 | **+0.004797** | 0.081052 | pass | **PASS** |
| A4-s3 | 0.245909 | 0.249941 | **+0.004032** | **0.038718** | **fail** | **FAIL** |

Full dose curves per seed (gain, fraction of full):

| Seed | 0.05 | 0.10 | 0.20 | 0.40 | 1.00 |
|---|---|---|---|---|---|
| A4-s1 | 0.009708 (5.4%) | 0.024033 (13.4%) | 0.054952 (30.6%) | 0.102854 (57.3%) | 0.179647 (100%) |
| A4-s2 | 0.012518 (3.5%) | 0.030305 (8.5%) | 0.081052 (22.7%) | 0.210795 (58.9%) | 0.357754 (100%) |
| A4-s3 | 0.012436 (5.6%) | 0.021050 (9.5%) | 0.038718 (17.5%) | 0.080188 (36.2%) | 0.221681 (100%) |

## 2. The verdict, stated plainly

- **Safety replicates: 3 of 3.** No seed breaches the 0.02 allowance at dose 0.20. Two seeds actually improve slightly
  (+0.004797, +0.004032) and one loses 0.006223.
- **The efficacy bar does not replicate.** A4-s3 delivers 0.038718 against the required 0.051125 — 76% of the bar,
  17.5% of its own full gain versus 30.6% on A4-s1.
- Under the frozen rule, the dose-0.20 setting **fails its replication** and cannot be declared a working control
  setting.

## 3. What the honest conclusion is

The dose-response result survives in a weaker form: **damage is dose-dependent and 0.20 is safe everywhere**. What
does not survive is the specific claim that 0.20 reliably keeps a quarter of the gain — on one seed it keeps about a
sixth. The safe band and the useful band overlap, but the useful band's width varies by seed.

This is exactly why the replication was preregistered. The seed-1 result alone would have been reported as a pass.

## 4. Selector test: still not run

`rpm_select.py` failed a **third** time: after fixing the discovery-tensor indexing, the oracle gain line indexed a
discovery-only tensor with a confirmation row's global id (`KeyError: 6`). The fix is to compute the oracle direction
for **all** rows and keep the discovery subset for selection. No selector numbers exist; the second approved option is
not yet evaluated.

## 5. Cost and host

- Replication run: instance `i-09958d92b2ae27011`, us-west-2, g5.xlarge, 706.7 s, **0.2159 USD**.
- Gain run: instance `i-0ef3db5110a4f3195`, us-west-2, g5.xlarge, 277.2 s, **0.0847 USD**.
- Goal total so far: about **0.98 USD** of the 15.00 USD cap.

## 6. Claim status

| Statement | Status |
|---|---|
| Dose 0.20 is safe (no seed loses more than 0.02 of composite) | `REAL`, 3 of 3 seeds |
| Dose 0.20 keeps ≥ 25% of the internal gain on every seed | `FAILED` (A4-s3: 17.5%) |
| Steering has a safe operating range | `REAL` |
| Steering is a reliable repair at a fixed safe dose | `NOT ESTABLISHED` |
| RPM-guided selection beats distance | `NOT TESTED` (script failures) |
