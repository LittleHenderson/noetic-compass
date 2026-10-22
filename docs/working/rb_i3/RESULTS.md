# RB-I3 results — the Unity Eye pairs and rotates the 7 desires with the 7 faculties

Claim ceiling: `SYNTHETIC_ONLY`. No creativity claim. Status word computed by `reader.py` from the raw part results, the frozen thresholds (FROZEN.json), the controls and the hard gates.

- Sign line: `APPROVE rb_i3, source 9ecfb7e7, LOCAL_CPU_ONCE on MSI, 300 s cap, no spend.`
- Source manifest sha256: `9ecfb7e7e486b148d82ca2d4f5d4fe263b1d6c27578ce0248c8eff3e1d198ff1`

## 🟩 Status word: `EYE_PAIRING_EARNED_KEEP` (test verdict `HARD_GATES_PASS`)

## Hard gates

| Gate | Result |
|---|---|
| H1_receipts_recheck | ✅ PASS |
| H2_no_invention | ✅ PASS |
| H3_replay | ✅ PASS |
| H4_equal_budgets | ✅ PASS |
| H5a_cut_holds_in_every_non_violator | ✅ PASS |
| H5b_cut_check_can_fail | ✅ PASS |
| H6_whisper_never_writes | ✅ PASS |
| H7_no_key_leak | ✅ PASS |
| H8_no_key_at_start | ✅ PASS |
| H9_learning_audit | ✅ PASS |
| H10_open_simplex | ✅ PASS |
| I1_null_control | ✅ PASS |
| H11_completeness | ✅ PASS |

I1 gap on C_NULL (|EYE_PAIRING − ATTENTION_ONLY|, pooled): 43/1528 = 2.81%.

## Marks (family A_STATIONARY, pooled over seeds 11 / 29 / 47)

| Mark | Result | Numbers |
|---|---|---|
| M1 pairing beats chance | ✅ PASS | EYE − RANDOM = 610/1527 (39.95%); EYE − ROUND_ROBIN = 217/509 (42.63%); per seed must be ahead |
| M2 near the key | ✅ PASS | EYE resolved / FIXED resolved = 295/309 (95.47%); bar 4/5 |
| M3 learning earns keep | ✅ PASS | M3a EYE − NO_LEARN = 620/1527 (40.60%) ✅ PASS; M3b EYE − SHUFFLED = 181/509 (35.56%) ✅ PASS |
| M4 the table finds the truth | ✅ PASS | best cell = true best faculty on 7 / 7 / 7 of 7 (seeds 11 / 29 / 47); bar 5 each |
| M5 cut in conversation | ✅ PASS | = H5a and H5b |
| M6 whisper never writes | ✅ PASS | = H6 |
| key room (exam sensitivity) | ✅ PASS | FIXED − RANDOM = 222/509 (43.61%); FIXED − ROUND_ROBIN = 707/1527 (46.30%) |

## Arm × family, 2-valued (resolved with a passing receipt / all items), pooled over 3 seeds

Cell marker = this arm against the better of the two mechanism-free baselines (RANDOM_PAIRING, ROUND_ROBIN_PAIRING) in the same family, pooled: 🟩 at least 5 points ahead; 🟨 ahead by less than 5; 🟧 0 to 5 points behind; 🟥 more than 5 points behind; ⬜ a baseline itself, or CUT_VIOLATOR (instrument, never scored).

| Arm | A_STATIONARY (scored) | B_DRIFT (reported) | C_NULL (control) | per seed A (11 / 29 / 47) |
|---|---|---|---|---|
| NO_DRIVE | 🟥 264/1527 = 17.29% | 🟥 276/1592 = 17.34% | 🟥 408/1528 = 26.70% | 81/523 / 98/511 / 85/493 |
| EYE_PAIRING | 🟩 1180/1527 = 77.28% | 🟩 1122/1592 = 70.48% | 🟨 887/1528 = 58.05% | 401/523 / 409/511 / 370/493 |
| FIXED_TABLE | 🟩 1236/1527 = 80.94% | 🟩 1271/1592 = 79.84% | 🟩 917/1528 = 60.01% | 411/523 / 436/511 / 389/493 |
| RANDOM_PAIRING | ⬜ 570/1527 = 37.33% | ⬜ 558/1592 = 35.05% | ⬜ 819/1528 = 53.60% | 187/523 / 184/511 / 199/493 |
| ROUND_ROBIN_PAIRING | ⬜ 529/1527 = 34.64% | ⬜ 502/1592 = 31.53% | ⬜ 814/1528 = 53.27% | 176/523 / 180/511 / 173/493 |
| EYE_PAIRING_NO_LEARN | 🟧 560/1527 = 36.67% | 🟧 522/1592 = 32.79% | 🟥 692/1528 = 45.29% | 237/523 / 167/511 / 156/493 |
| ATTENTION_ONLY | 🟨 609/1527 = 39.88% | 🟩 686/1592 = 43.09% | 🟨 844/1528 = 55.24% | 267/523 / 185/511 / 157/493 |
| PAIRING_ONLY | 🟩 1004/1527 = 65.75% | 🟩 890/1592 = 55.90% | 🟥 702/1528 = 45.94% | 347/523 / 355/511 / 302/493 |
| EYE_RATIO | 🟩 1169/1527 = 76.56% | 🟩 1126/1592 = 70.73% | 🟨 882/1528 = 57.72% | 383/523 / 419/511 / 367/493 |
| EYE_SHUFFLED_FEEDBACK | 🟨 637/1527 = 41.72% | 🟩 660/1592 = 41.46% | 🟨 867/1528 = 56.74% | 228/523 / 194/511 / 215/493 |
| CUT_VIOLATOR | ⬜ 1249/1527 = 81.79% | ⬜ 1218/1592 = 76.51% | ⬜ 1016/1528 = 66.49% | 432/523 / 428/511 / 389/493 |

## Arm × family, 3-valued (RESOLVED / WRONG / UNDETERMINED)

UNDETERMINED = still open, or closed after 7 different faculties failed (CLOSED_NO_FIX). It is never counted as wrong.

| Arm | A_STATIONARY | B_DRIFT | C_NULL |
|---|---|---|---|
| NO_DRIVE | 264 / 0 / 1263 | 276 / 0 / 1316 | 408 / 0 / 1120 |
| EYE_PAIRING | 1180 / 0 / 347 | 1122 / 0 / 470 | 887 / 0 / 641 |
| FIXED_TABLE | 1236 / 0 / 291 | 1271 / 0 / 321 | 917 / 0 / 611 |
| RANDOM_PAIRING | 570 / 0 / 957 | 558 / 0 / 1034 | 819 / 0 / 709 |
| ROUND_ROBIN_PAIRING | 529 / 0 / 998 | 502 / 0 / 1090 | 814 / 0 / 714 |
| EYE_PAIRING_NO_LEARN | 560 / 0 / 967 | 522 / 0 / 1070 | 692 / 0 / 836 |
| ATTENTION_ONLY | 609 / 0 / 918 | 686 / 0 / 906 | 844 / 0 / 684 |
| PAIRING_ONLY | 1004 / 0 / 523 | 890 / 0 / 702 | 702 / 0 / 826 |
| EYE_RATIO | 1169 / 0 / 358 | 1126 / 0 / 466 | 882 / 0 / 646 |
| EYE_SHUFFLED_FEEDBACK | 637 / 0 / 890 | 660 / 0 / 932 | 867 / 0 / 661 |
| CUT_VIOLATOR | 1249 / 0 / 278 | 1218 / 0 / 374 | 1016 / 0 / 512 |

## The learned 7 × 7 table vs the true table (EYE_PAIRING, family A, end of life) — M4

Each cell: the Eye's successes/tries. `*` = the Eye's best cell for that Foundation; `T` = the true best faculty (the home kind's primary). In brackets: items filed at that Foundation the faculty truly solves, out of all items filed there.

Seed 11 — match on 7 of 7; noisy (half-dead) wells: F1, F5

| | CURIOSITY | PONDERING | IMAGINATION | VERIFY | ASKING | INTEGRATION | CONSOLIDATE |
|---|---|---|---|---|---|---|---|
| F1 Unity | 1/23 [6/82] | 0/15 [3/82] | 1/18 [2/82] | 21/53 *T [33/82] | 0/16 [2/82] | 0/16 [12/82] | 1/20 [1/82] |
| F2 Wisdom | 3/14 [4/67] | 2/10 [4/67] | 5/14 [5/67] | 3/16 [4/67] | 4/17 [20/67] | 41/60 *T [46/67] | 3/10 [5/67] |
| F3 Vitality | 3/7 [5/64] | 1/6 [2/64] | 45/59 *T [50/64] | 4/14 [15/64] | 3/6 [3/64] | 1/5 [1/64] | 5/14 [5/64] |
| F4 Connection | 0/3 [1/81] | 2/9 [27/81] | 4/11 [4/81] | 5/10 [5/81] | 2/6 [3/81] | 3/8 [4/81] | 64/81 *T [64/81] |
| F5 Agency | 1/24 [1/74] | 31/65 *T [34/74] | 0/21 [0/74] | 3/29 [3/74] | 0/23 [1/74] | 0/23 [1/74] | 0/22 [9/74] |
| F6 Structure | 5/16 [30/86] | 1/7 [5/86] | 3/13 [5/86] | 6/16 [7/86] | 59/80 *T [62/86] | 3/16 [7/86] | 6/13 [7/86] |
| F7 Purpose | 41/58 *T [50/69] | 4/12 [6/69] | 2/8 [21/69] | 1/8 [6/69] | 2/11 [2/69] | 4/12 [5/69] | 2/12 [4/69] |

Seed 29 — match on 7 of 7; noisy (half-dead) wells: F1, F2

| | CURIOSITY | PONDERING | IMAGINATION | VERIFY | ASKING | INTEGRATION | CONSOLIDATE |
|---|---|---|---|---|---|---|---|
| F1 Unity | 21/52 *T [25/64] | 1/17 [4/64] | 0/13 [2/64] | 3/19 [4/64] | 1/20 [8/64] | 0/14 [2/64] | 2/17 [3/64] |
| F2 Wisdom | 1/24 [2/71] | 1/19 [1/71] | 3/22 [4/71] | 2/21 [2/71] | 27/59 *T [30/71] | 1/25 [9/71] | 0/18 [2/71] |
| F3 Vitality | 1/10 [3/87] | 4/13 [23/87] | 62/82 *T [67/87] | 1/8 [5/87] | 1/9 [3/87] | 5/14 [6/87] | 5/10 [8/87] |
| F4 Connection | 3/10 [3/76] | 0/7 [2/76] | 1/8 [1/76] | 59/72 *T [62/76] | 5/10 [7/76] | 1/7 [2/76] | 2/10 [24/76] |
| F5 Agency | 0/7 [5/67] | 2/8 [3/67] | 3/11 [4/67] | 2/8 [19/67] | 4/13 [7/67] | 47/63 *T [50/67] | 2/10 [3/67] |
| F6 Structure | 3/11 [22/82] | 59/79 *T [60/82] | 5/11 [6/82] | 2/12 [4/82] | 4/12 [6/82] | 2/11 [3/82] | 4/15 [4/82] |
| F7 Purpose | 1/7 [4/64] | 4/12 [5/64] | 0/8 [17/64] | 1/7 [3/64] | 4/10 [4/64] | 2/8 [2/64] | 45/59 *T [49/64] |

Seed 47 — match on 7 of 7; noisy (half-dead) wells: F4, F5

| | CURIOSITY | PONDERING | IMAGINATION | VERIFY | ASKING | INTEGRATION | CONSOLIDATE |
|---|---|---|---|---|---|---|---|
| F1 Unity | 6/17 [8/73] | 41/64 *T [47/73] | 1/9 [5/73] | 2/11 [6/73] | 2/11 [21/73] | 3/9 [7/73] | 2/13 [5/73] |
| F2 Wisdom | 2/10 [3/66] | 1/8 [3/66] | 4/11 [4/66] | 37/53 *T [46/66] | 2/10 [5/66] | 1/10 [1/66] | 13/25 [24/66] |
| F3 Vitality | 0/4 [2/65] | 2/5 [4/65] | 2/5 [19/65] | 3/5 [5/65] | 1/4 [1/65] | 46/58 *T [50/65] | 3/6 [4/65] |
| F4 Connection | 3/28 [5/80] | 2/28 [3/80] | 29/72 *T [31/80] | 0/20 [0/80] | 2/25 [5/80] | 2/27 [12/80] | 2/25 [4/80] |
| F5 Agency | 2/23 [8/63] | 1/15 [3/63] | 1/14 [3/63] | 0/13 [3/63] | 2/17 [3/63] | 0/17 [1/63] | 12/39 *T [21/63] |
| F6 Structure | 3/9 [3/79] | 3/9 [20/79] | 2/10 [3/79] | 3/9 [6/79] | 58/76 *T [61/79] | 3/9 [5/79] | 2/5 [3/79] |
| F7 Purpose | 48/64 *T [51/67] | 2/10 [5/67] | 3/9 [3/67] | 2/8 [18/67] | 5/11 [6/67] | 3/7 [5/67] | 1/8 [1/67] |

## The conversation cut (M5) and the whisper (M6), summed over 3 seeds

| Arm | family | faculty calls in conversation | attention steps in conversation | whispers issued | whispers admitted | whisper writes to the brain |
|---|---|---|---|---|---|---|
| NO_DRIVE | A_STATIONARY | 0 | 0 | 0 | 0 | 0 |
| NO_DRIVE | B_DRIFT | 0 | 0 | 0 | 0 | 0 |
| NO_DRIVE | C_NULL | 0 | 0 | 0 | 0 | 0 |
| EYE_PAIRING | A_STATIONARY | 0 | 0 | 2977 | 2977 | 0 |
| EYE_PAIRING | B_DRIFT | 0 | 0 | 3097 | 3097 | 0 |
| EYE_PAIRING | C_NULL | 0 | 0 | 3050 | 3050 | 0 |
| FIXED_TABLE | A_STATIONARY | 0 | 0 | 2959 | 2959 | 0 |
| FIXED_TABLE | B_DRIFT | 0 | 0 | 3079 | 3079 | 0 |
| FIXED_TABLE | C_NULL | 0 | 0 | 3056 | 3056 | 0 |
| RANDOM_PAIRING | A_STATIONARY | 0 | 0 | 0 | 0 | 0 |
| RANDOM_PAIRING | B_DRIFT | 0 | 0 | 0 | 0 | 0 |
| RANDOM_PAIRING | C_NULL | 0 | 0 | 0 | 0 | 0 |
| ROUND_ROBIN_PAIRING | A_STATIONARY | 0 | 0 | 0 | 0 | 0 |
| ROUND_ROBIN_PAIRING | B_DRIFT | 0 | 0 | 0 | 0 | 0 |
| ROUND_ROBIN_PAIRING | C_NULL | 0 | 0 | 0 | 0 | 0 |
| EYE_PAIRING_NO_LEARN | A_STATIONARY | 0 | 0 | 3054 | 3054 | 0 |
| EYE_PAIRING_NO_LEARN | B_DRIFT | 0 | 0 | 3184 | 3184 | 0 |
| EYE_PAIRING_NO_LEARN | C_NULL | 0 | 0 | 3056 | 3056 | 0 |
| ATTENTION_ONLY | A_STATIONARY | 0 | 0 | 3054 | 3054 | 0 |
| ATTENTION_ONLY | B_DRIFT | 0 | 0 | 3184 | 3184 | 0 |
| ATTENTION_ONLY | C_NULL | 0 | 0 | 3056 | 3056 | 0 |
| PAIRING_ONLY | A_STATIONARY | 0 | 0 | 2971 | 2971 | 0 |
| PAIRING_ONLY | B_DRIFT | 0 | 0 | 3117 | 3117 | 0 |
| PAIRING_ONLY | C_NULL | 0 | 0 | 3056 | 3056 | 0 |
| EYE_RATIO | A_STATIONARY | 0 | 0 | 2987 | 2987 | 0 |
| EYE_RATIO | B_DRIFT | 0 | 0 | 3088 | 3088 | 0 |
| EYE_RATIO | C_NULL | 0 | 0 | 3052 | 3052 | 0 |
| EYE_SHUFFLED_FEEDBACK | A_STATIONARY | 0 | 0 | 3054 | 3054 | 0 |
| EYE_SHUFFLED_FEEDBACK | B_DRIFT | 0 | 0 | 3184 | 3184 | 0 |
| EYE_SHUFFLED_FEEDBACK | C_NULL | 0 | 0 | 3056 | 3056 | 0 |
| CUT_VIOLATOR | A_STATIONARY | 765 | 765 | 3476 | 3476 | 0 |
| CUT_VIOLATOR | B_DRIFT | 749 | 749 | 3711 | 3711 | 0 |
| CUT_VIOLATOR | C_NULL | 708 | 708 | 3751 | 3751 | 0 |

CUT_VIOLATOR is EYE_PAIRING with the cut line removed. Its counts above 0 show the counters can fire.

## Reported rows (no word)

- R1 geometry: EYE_PAIRING − EYE_RATIO = 11/1527 (0.72%), pooled family A.
- R2: EYE − ATTENTION_ONLY = 571/1527 (37.39%); EYE − PAIRING_ONLY = 176/1527 (11.53%).
- R3 drift (family B; resolved sessions 1-16 | 17-32, per seed):
  - NO_DRIVE: 48/258 / 35/285 / 47/261 | 46/280 / 47/262 / 53/246
  - EYE_PAIRING: 185/258 / 222/285 / 189/261 | 186/280 / 159/262 / 181/246
  - FIXED_TABLE: 209/258 / 233/285 / 194/261 | 221/280 / 202/262 / 212/246
  - RANDOM_PAIRING: 115/258 / 85/285 / 89/261 | 88/280 / 90/262 / 91/246
  - ROUND_ROBIN_PAIRING: 83/258 / 89/285 / 83/261 | 83/280 / 83/262 / 81/246
  - EYE_PAIRING_NO_LEARN: 91/258 / 85/285 / 94/261 | 86/280 / 74/262 / 92/246
  - ATTENTION_ONLY: 108/258 / 102/285 / 149/261 | 128/280 / 94/262 / 105/246
  - PAIRING_ONLY: 170/258 / 181/285 / 134/261 | 138/280 / 103/262 / 164/246
  - EYE_RATIO: 180/258 / 212/285 / 185/261 | 184/280 / 170/262 / 195/246
  - EYE_SHUFFLED_FEEDBACK: 110/258 / 128/285 / 121/261 | 81/280 / 119/262 / 101/246
  - CUT_VIOLATOR: 210/258 / 226/285 / 202/261 | 205/280 / 176/262 / 199/246
  - first session (0-based) after the drift where the Eye's best cells match the new key on >= 5 of 7: [22, 28, 21] (None = not by session 32)
- R4 learning curve (family A, per session, pooled over seeds):
  - EYE_PAIRING: 46 42 62 59 77 83 82 88 90 82 93 71 87 75 76 73 87 85 80 81 72 83 79 91 88 78 90 64 78 78 91 72
  - FIXED_TABLE: 76 77 75 72 88 79 77 92 90 90 93 71 80 78 78 77 82 92 88 81 70 83 71 84 86 78 90 70 73 76 91 85
  - RANDOM_PAIRING: 44 43 38 20 26 40 36 56 28 35 28 53 33 28 31 32 51 25 48 43 43 34 40 32 38 43 49 20 25 46 45 39
- R5 blocking (family A): NO_DRIVE zero-resolved sessions 7, most tries on one item 1; EYE_PAIRING zero-resolved sessions 0, most tries on one item 7; FIXED_TABLE zero-resolved sessions 0, most tries on one item 7; RANDOM_PAIRING zero-resolved sessions 0, most tries on one item 7; ROUND_ROBIN_PAIRING zero-resolved sessions 1, most tries on one item 7; EYE_PAIRING_NO_LEARN zero-resolved sessions 1, most tries on one item 7; ATTENTION_ONLY zero-resolved sessions 0, most tries on one item 7; PAIRING_ONLY zero-resolved sessions 0, most tries on one item 7; EYE_RATIO zero-resolved sessions 0, most tries on one item 7; EYE_SHUFFLED_FEEDBACK zero-resolved sessions 0, most tries on one item 7; CUT_VIOLATOR zero-resolved sessions 0, most tries on one item 7
- R6/R7 (EYE_PAIRING, A, seed 11): pull gap mean {'F1-F7': '0.14006250982644985', 'F2-F6': '0.1104617096474289', 'F3-F5': '0.1722022409455432'}, max {'F1-F7': '0.747809152872444', 'F2-F6': '0.5985744343730789', 'F3-F5': '0.6902221049059165'}; Fisher-Rao step mean 0.12570194940613283, max 0.4780622384599204; min coordinate 0.0039176785057316735
- R6/R7 (EYE_PAIRING, A, seed 29): pull gap mean {'F1-F7': '0.17518292428250193', 'F2-F6': '0.18006185245057205', 'F3-F5': '0.10134170230980236'}, max {'F1-F7': '0.7928423950447351', 'F2-F6': '0.7785888077858881', 'F3-F5': '0.5029864822382899'}; Fisher-Rao step mean 0.1256504467372163, max 0.4698213180639808; min coordinate 0.003435082522552787
- R6/R7 (EYE_PAIRING, A, seed 47): pull gap mean {'F1-F7': '0.1481098268410496', 'F2-F6': '0.1129924070997542', 'F3-F5': '0.17065284352922228'}, max {'F1-F7': '0.7277079593058049', 'F2-F6': '0.5523889148449603', 'F3-F5': '0.7664670658682635'}; Fisher-Rao step mean 0.12450558196446336, max 0.5356116010151019; min coordinate 0.0032951211773063326
- R9 NO_DRIVE (RB today's one routine, PONDERING): 264/1527 = 17.29% on family A.

## Replay (H3)

- R01 vs A02: equal (33d52ef05f56039f)
- R02 vs A13: equal (f8db399d2f3e0ff3)
- R03 vs A24: equal (aaa64d8da52068df)

## What this does and does not show

It licenses only this sentence: On synthetic idle worlds where the fit between item kinds and faculties is hidden and filing is noisy, an Eye that counts verified tries per (desire, faculty) pair, starting with no key, resolves at least 5 points more items than random or round-robin pairing, reaches at least 80% of the answer-key arm, recovers the hidden best pairing on at least 5 of 7 desires, and never acts or writes during conversation.

It does NOT license: anything outside synthetic worlds; that HELM's faculties are creative, curious or imaginative in any human sense; meaning for the Foundations beyond category labels; that the Fisher-Rao geometry helps (R1 is a row, not a word); that the Eye should act outside tests; anything about U2; any change to wave 3's DRIVE_LOOP = NEUTRAL.

## Plain reading (operator's prose; the word above comes from the program, not from this paragraph)

What it does show. In a made-up idle world built so that pairing matters, the Eye starts with a blank 7 × 7 table
(every cell 0/0). It only counts verified tries. By the end of each life its best cell matched the hidden best
faculty for all 7 desires, on all 3 seeds (7 / 7 / 7). It resolved 1180 of 1527 items (77.28%). The answer-key arm
resolved 1236 (80.94%), so the Eye reached 95.47% of the key without ever seeing it. Random pairing got 37.33% and
round-robin 34.64%. The gain comes from learning from the right evidence: the same Eye with learning frozen got
36.67%, and fed shuffled verdicts it got 41.72%. The conversation cut now can fail: the cut-breaking arm made
765 / 749 / 708 faculty calls in conversation (families A / B / C); every other arm made 0. The Eye issued 2977
whispers on family A and wrote 0 times to the brain; the planted Eye write was refused and counted in every part.

What it does not show. Nothing about HELM's real idle life: the world was built so pairing has room. The learning
rule is plain counting; any count-based chooser would do the same. The Fisher-Rao step is a tie with the plain
count ratio (+0.72 points, row R1): the geometry has not earned a word. Nothing here is a claim that any faculty is
creative, curious or imaginative. On the null family (no pairing structure) the Eye was 2.81 points from
attention-only, inside the 5-point band, but it was 4.45 points above random pairing there; part of the Eye's
lead anywhere is the attention learning, not the table.

Predictions vs result. Designer: EYE_PAIRING_EARNED_KEEP about 70% — it came. Misses: FIXED_TABLE 80.94% (designer
82-86); ATTENTION_ONLY 39.88% (designer 27-38); NO_DRIVE 17.29% (designer 15-17); drift: the designer expected the
best cells NOT to recover by session 32 (about 70%), but they recovered at sessions 22 / 28 / 21 (0-based).
Builder: 60% for this word.

Deviations, recorded. The brief fixed the scored seeds at 11 / 29 / 47 instead of a custodian deriving them from the
sign-line hash, so custody is weaker than wave 3's X2 (the builder ran fixture seeds 101 / 202 / 303 only before the
sign line). The brief listed 8 arms; all 11 design arms ran (the 103-part count needs them). The reader ran as an
extra part M00 under the same supervisor. The sign line is operator-composed from the owner's word, not a separate
owner signature. One run, synthetic only, no statistical superiority claim.
