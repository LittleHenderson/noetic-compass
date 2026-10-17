# PROVENANCE — `language_v3`

This folder is the LM-T1 package (`lm_t1`), copied whole into this repository so that it runs from inside the
repo, plus two additions: the `p/q` number form (the owner's Q13 ruling) and sentence forms for the REFUSE and
CLOSE turns. Nothing was redesigned.

Source root, every file below:

    C:\Users\wakil\Documents\Codex\2026-10-14\lm_t1

That folder is loose files and is not a git repository. It is the real translator. It passed 576 of 576 hard
marks, read 233 of 439 free English sentences, and its three suites passed 26, 11 and 5 on 2026-10-14. The
`docs/working/noetic_council/language_v2` folder in this repo is a weaker duplicate and is NOT the base; see its
own README, which now marks it superseded.

The sha256 of every copied file is in the first table below, and it is the hash of the file **as copied**, which
equalled the source: 101 of 101 files matched byte for byte at the moment of copying. The second table lists the
files this folder adds, and the three copied files it changed, with their sha256 now.

## The two dependencies that stay outside this repository

Both are imported read-only. Neither is copied here, and neither was modified.

    sdg_bridge_v2          C:\Users\wakil\Documents\Codex\CAS-Recipe-Network-Comparison-20261011
    lacunarity_machine     C:\Users\wakil\Documents\Codex\2026-10-14\lacunarity_machine_v1

The base cannot run without them on `PYTHONPATH`. This is the exact setting that was verified working:

    $env:PYTHONPATH = "C:\Users\wakil\Documents\Codex\CAS-Recipe-Network-Comparison-20261011;C:\Users\wakil\Documents\Codex\2026-10-14\lacunarity_machine_v1"

With that set, from this folder:

    C:\Python314\python.exe -X utf8 -B test_lm_t1.py     # Ran 26 tests ... OK
    C:\Python314\python.exe -X utf8 -B test_lm_t1b.py    # Ran 11 tests ... OK
    C:\Python314\python.exe -X utf8 -B test_lm_t1c.py    # Ran 5 tests ... OK

What needs what:

- `test_lm_t1c.py` is the lightest. It imports `cce_v01c` only and needs no external path.
- `test_lm_t1b.py` needs `sdg_bridge_v2` for its compiler cross-check (B4).
- `test_lm_t1.py` needs `lacunarity_machine` for the coverage-ledger test and `sdg_bridge_v2` for the
  ALIAS-WIDE tests. Without those two paths it fails at import: `ModuleNotFoundError` for `sdg_bridge_v2`.
  The ledger test and the ALIAS-WIDE tests cannot run without the dependency present. This is stated plainly
  rather than worked around, because the alternative would be to fake the ledger or to skip the test.

`measure_marks.py` also needs both paths, and it additionally reads the 5,268-row English file set under
`C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-synthetic\data\path_d` for M4. Those rows are inputs, not code; they
stay where they are.

## A run versus a re-measurement

`worker.py` runs the marks under a single-use owner permit, blocks sockets and writes receipts to `runs/`. It will
not start on another machine: it requires hostname `MSI`, a signed authorization for the exact run id, and it
consumes that authorization on first use.

`measure_marks.py` calls the same scoring functions in the same order and prints the same numbers without a
permit. It is a re-measurement tool for comparing a before and an after on one machine. It writes nothing to
`runs/`, and it is never a run record and never a claim.

## Files copied from the base, with sha256

The size is in bytes. Each sha256 is of the file as copied; the source file with the same name under the source
root above has the same bytes.

| file here | bytes | sha256 |
|---|---|---|
| `ALIAS_WIDE_LEXICON_v0_1.json` | 6133 | `d199611397d4d8ff5c215095d3424327917e4da9fcd5676e52cdd8c047a8b2e0` |
| `aliaswide.py` | 8421 | `e6afd206736ea9c70bd15a72281c503d15cf7f97da2735cacb476ede8c722211` |
| `cas_ast.py` | 13148 | `175fbadf23e9ae11ed94513e6ff382b07e6bb46f78bbc7e764200f3afb8f58ae` |
| `cce_v01b.py` | 16716 | `25047ba1c3cd3ecb9212aa0cb66f59fad9b8abdb62a9875f403ce59c201228bd` |
| `cce_v01c.py` | 5143 | `a043c988f7fda529adb2a3cdf8ad28405f7fe2b7e7c4f96e43bc42ef57a4302f` |
| `cce.py` | 41546 | `b494598e4b665514d7fd78b89a90186d7e7fc679ab7f407b4826459356289bd3` |
| `coverage.py` | 11804 | `36e520e5f47074a8815e4c38aa9d82d859877a19aafc225a40749207b9dc22b5` |
| `FROZEN_T1B.json` | 6161 | `6a9eae1aa7fdf6ff3ce8c874a291b2ef149b98084d34f57e8a079e8e678717b6` |
| `FROZEN_T1C.json` | 3230 | `f69a58e1a5addbb9a854e85d06c0c64ca599af861c714f412d6dfffaffb9f926` |
| `FROZEN.json` | 11016 | `ac41c92ea5dc4a44391f7e4366af4f03503b2ddff45a5ddbf66e06948429094f` |
| `GRAMMAR_CCE_v0_1.md` | 14707 | `36b9a6dbb52facdadf293476d5623fb80d122cf90412ba3d033d9de59b12ef70` |
| `GRAMMAR_CCE_v0_1b_ADDENDUM.md` | 7271 | `9191c7dbc4b3220fb2236c4bbb4493649d586ce05d113ddad2a9530fbb086241` |
| `GRAMMAR_CCE_v0_1c_ADDENDUM.md` | 2269 | `333ebde57b269d8f1494218cd1f8f6bfe950a7a2d53e0bb9f1d736e926c94d1a` |
| `GRAMMAR_CCE_v0_1c_R_ADDENDUM.md` | 1402 | `b76d2093fc5058822afc43170bf12133abfa64743f37e8a7de7fd98683bc5119` |
| `handset/HAND_SET_FREEZE.json` | 511 | `91b49bb98af31e5fb074442f1dc328c564ad846ed6f121f987ce579216962acf` |
| `handset/HAND_SET_v0_1.json` | 47070 | `653cdc708112410b18c59ce26daf65382eccd94a8f9e49705fcea32eeedab56b` |
| `handset/HAND_SET_v0_1b_ADD16_FREEZE.json` | 391 | `44e152b3e20aadb2dfec0d44514cc26e7bc745b147fc4c84f9849eb3b9544277` |
| `handset/HAND_SET_v0_1b_ADD16.json` | 12445 | `cf28d0a065190bbc283e6256de46503917b924e952a3682bfb22dd750fdc1ffc` |
| `handset/HAND_SET_v0_1c_DOTTED4_FREEZE.json` | 299 | `4fcb6ac202a311aa6880b10949a901cfde25e90553c1022a597900e3156e99f1` |
| `handset/HAND_SET_v0_1c_DOTTED4.json` | 3946 | `e34bf08cb38171299abe146316f3457e8f015c3c7075c29d2eac9cbe43ebc216` |
| `handset/HAND_SET_v0_1c_R_DOTTED4_FREEZE.json` | 333 | `d3b17da7097c6d5063c7478df4a8a39f5dfeb87f75f0a4c5697dc6870dc02ae0` |
| `handset/HAND_SET_v0_1c_R_DOTTED4.json` | 3778 | `73b71b44c524753185fcd87180860e5ac9322c2ce3ab29315be092dbd203c86f` |
| `OWNER_APPROVAL_EVIDENCE.template.md` | 1277 | `746e7b37dbeb2ce9dcadf7dd365123fc840a81f5702970246f5030b127df8d52` |
| `README.md` | 862 | `21d6ac0d82ea38d5532bd1d49e06583122581144b6ff15577a2e6007c78a26e0` |
| `RESULTS_T1B.md` | 3228 | `f6b46849023a0aa45c357e6f2805ada00a4ef956833a27e29cfee4cc6b7d379c` |
| `RESULTS_T1C.md` | 1464 | `3e3a53e67a7bba064ff85a3bd6f8a995ea68414afd742a9f994ddcff6b692a36` |
| `RESULTS.md` | 4432 | `1e96b4fc52804297a4a113e88071a6aac4e6e0cef0ddf167f4ad513bf6f2ef41` |
| `runs/LM_T1_MSI_ONCE/AUTHORIZATION.json` | 667 | `4ecd01d57254437d1fa8b320ca8080b4686ea69199b59b8170b5d6c42b54a811` |
| `runs/LM_T1_MSI_ONCE/CLAIM.json` | 89 | `39607175933fc87fbec058c03ecda9f632438160157184a3f88fc25d97c1e034` |
| `runs/LM_T1_MSI_ONCE/CONSUMED.json` | 74 | `71b9f20c9672620007ba872d939b13816726751d2ed0b24023084e0017a11b2e` |
| `runs/LM_T1_MSI_ONCE/END.json` | 531 | `b587aed2115c01fd8c885740669b56a2807da88c2f596e6a5bde426511dbcc07` |
| `runs/LM_T1_MSI_ONCE/M1_ROUND_TRIP_576.json` | 80146 | `5a922603b4a84e659aa70d7b60f10e1f2cce1d6a5e9fe8cda1b218aad15259d5` |
| `runs/LM_T1_MSI_ONCE/M2_WORDING_DRAWS.json` | 269 | `eddc94dc562051e4d23aa887e1f727643cfde6f06a59fb36d1f1c1ca65c2569d` |
| `runs/LM_T1_MSI_ONCE/M3_HAND_SET.json` | 24686 | `06bbce4b3c1174a0746f7e41ac4fdd2691885b2fdbb6b7c60fa3be0e71c5a30c` |
| `runs/LM_T1_MSI_ONCE/M4_SDG_ENGLISH.json` | 627 | `de14d56f74fdcca19078adf8fe35ab1c94802d5389300b844ff8f70c6f7fa893` |
| `runs/LM_T1_MSI_ONCE/M4_SDG_ROWS.jsonl` | 72175 | `4d43fe168aaae050708977c55e1525c294b6d0a48dbc4f816cba959620926a9e` |
| `runs/LM_T1_MSI_ONCE/M5_CONTROLS.json` | 5226 | `80c7ca16df3aa9c8af9d34a9ab61a2377a9a75ba2bcb19772960cfc596eff271` |
| `runs/LM_T1_MSI_ONCE/M6_COVERAGE_LEDGER.json` | 1098143 | `2515fd6320345266598608635b702a01baa92d8ba14c823b4873fc2b8956213e` |
| `runs/LM_T1_MSI_ONCE/M7_COMPILER_CROSSCHECK.json` | 218 | `507996257d2e5efc5680c4ffa6eab3918b29ff1b07d4a2dd8f3ef6fa3f651586` |
| `runs/LM_T1_MSI_ONCE/OWNER_APPROVAL_EVIDENCE.md` | 1424 | `7c9a2b7dd2917c3af05c21ec42dc0c6f7038c5fa382a16317dbf0501d8e9d946` |
| `runs/LM_T1_MSI_ONCE/READING.json` | 796 | `fa3ecdb50487422b7ef936583cfb7bfe55c706c87b39e99e0bb04409b1d4106e` |
| `runs/LM_T1_MSI_ONCE/stderr.log` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `runs/LM_T1_MSI_ONCE/stdout.log` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `runs/LM_T1_MSI_ONCE/SUMMARY.json` | 9926 | `50dcfa82145a3c58c625f804de1a1fb8160b089b443a4adbb28eea10d70aaf32` |
| `runs/LM_T1_MSI_ONCE/TEST_RESULTS.json` | 86 | `560792e7a52a4b1ed1830f45706854f0d3a9ae747130698aa170db1d9766bc27` |
| `runs/LM_T1B_MSI_ONCE/AUTHORIZATION.json` | 816 | `bd64aeb12a90e2b4952b399470bc9b4dc1822fedd0363c72fdfcd4de2916a9b0` |
| `runs/LM_T1B_MSI_ONCE/B1_NEST.json` | 269 | `626831d200fa7c083482e80669fd77dc3ac7fc4165898385cd992dc4ca0b3aca` |
| `runs/LM_T1B_MSI_ONCE/B2_META.json` | 290 | `a409baf8458ce92a9c30073c1a7adc8cf665158a64f0689c67c8f110e3dafa8a` |
| `runs/LM_T1B_MSI_ONCE/B3_HAND_ADD16.json` | 3643 | `50bea232de286e73689acefd582b1cddfb50e92c989ea71249f333bfe4f3b171` |
| `runs/LM_T1B_MSI_ONCE/B4_COMPILER.json` | 112 | `dc12e2c39c68b6ca0c3e999a255f01708ba9bd0442aa1c4052805bb139199e49` |
| `runs/LM_T1B_MSI_ONCE/B5_NO_DAMAGE.json` | 104 | `c2c513c71409eb515a0155863befa9c3d22c2dae4521755c1064af7ce152aa51` |
| `runs/LM_T1B_MSI_ONCE/B6_BOOK_EXAMPLES.json` | 22882 | `e1ca280f0fe5063d551dccee6b4aca7cbf15e6aaf90858b40b1aac50f74f9bc2` |
| `runs/LM_T1B_MSI_ONCE/B7_RECIPE_GRAMMAR.json` | 58 | `d5d915596d9d2b45d8dbf57e8c3765d8fc62eb0f59acf5382ba0386d65dee4d5` |
| `runs/LM_T1B_MSI_ONCE/CLAIM.json` | 90 | `fe366e5fc7df87058bfeab7fc29a1aa36c1a89f9c8fc44103be75be54c7c34aa` |
| `runs/LM_T1B_MSI_ONCE/CONSUMED.json` | 76 | `eef004359ef43286c4ff8526fdaf65b2c7e39323fe397cce898f4e77d30ed1bd` |
| `runs/LM_T1B_MSI_ONCE/END.json` | 529 | `5602af168cc52867ce4843557bbaa1ccea14231c2d04dce93502c71e92e1c675` |
| `runs/LM_T1B_MSI_ONCE/OWNER_APPROVAL_EVIDENCE.md` | 1426 | `1b27238571505b4505435bf812044d979c64fc34eff1b06214d137e6b877c8f9` |
| `runs/LM_T1B_MSI_ONCE/READING.json` | 594 | `89284aa353e7f635755a904bc61b696312bc34ffcdcdf5454579139b61035a52` |
| `runs/LM_T1B_MSI_ONCE/stderr.log` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `runs/LM_T1B_MSI_ONCE/stdout.log` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `runs/LM_T1B_MSI_ONCE/SUMMARY.json` | 2594 | `ab14c7403d65b706b6310c69d62f5dc98d256a5309919da30e794e5c989d19f7` |
| `runs/LM_T1B_MSI_ONCE/TEST_RESULTS.json` | 86 | `69145ea5ca37d39111261087c33f7cf16a5fde6a1670c17f34a965220f61fbe4` |
| `runs/LM_T1C_MSI_ONCE/AUTHORIZATION.json` | 869 | `2e6061a9279fad5f495bd1932cdf6e043402765c36cc612d39e26e153712dd46` |
| `runs/LM_T1C_MSI_ONCE/C1_DOTTED_LEDGER.json` | 308 | `ad616a11a7587262d05d5ec4f300d0573ea8adc94a92d062e75a28601c4af111` |
| `runs/LM_T1C_MSI_ONCE/C2_HAND_R4.json` | 617 | `f15c985a4e453402a046a0d53d4742c64105141371de20fc7cdcae06ce622849` |
| `runs/LM_T1C_MSI_ONCE/C3_SAME_NESTING.json` | 63 | `8fecbf119e4990543983d5c0149683fc36e6e2e05c529860a2dffec30aa693c1` |
| `runs/LM_T1C_MSI_ONCE/C4_REFUSALS.json` | 203 | `a75716fb2b3503beb35408428205ce0d720e013778536e5e0f505e5d3ac8d43d` |
| `runs/LM_T1C_MSI_ONCE/C5_NO_DAMAGE.json` | 95 | `25edf68c557b47717dda8acae026af9f1a96e766102ab17a7310c70424cf0103` |
| `runs/LM_T1C_MSI_ONCE/CLAIM.json` | 90 | `6ba23c68a2be8d5a2ce9bcaa8591de622e684645e45926c0a78f7ecbcec7a880` |
| `runs/LM_T1C_MSI_ONCE/CONSUMED.json` | 76 | `6cb4ee37378e138d5d87f2f8ce49e29e0e812752c00313abcd90533a59bec04c` |
| `runs/LM_T1C_MSI_ONCE/END.json` | 530 | `fc876f0f564f7b9d25954b62eb6a0bc159a1d593a0d3df344425b8c761805b7d` |
| `runs/LM_T1C_MSI_ONCE/OWNER_APPROVAL_EVIDENCE.md` | 1426 | `21f2d59c90035dd226739dab91d6e766f18ff09bd52cedd05b176071b5480815` |
| `runs/LM_T1C_MSI_ONCE/READING.json` | 340 | `83e0789f5918baee5c17e5b1d97bb76a8883cb8b6be7afe53a4d19f0822849b0` |
| `runs/LM_T1C_MSI_ONCE/stderr.log` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `runs/LM_T1C_MSI_ONCE/stdout.log` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `runs/LM_T1C_MSI_ONCE/SUMMARY.json` | 1464 | `0d6ef68133152d1e03dba83c963348c7212d9944c2d0c568b2dea5e38ebb02a4` |
| `runs/LM_T1C_MSI_ONCE/TEST_RESULTS.json` | 86 | `f96adcac9b54561a5444bd17a1d1cac585b9b9339a3654889a49466c6f15edf6` |
| `scoring.py` | 16677 | `1712681f0c088f552227f52730172701a6b9a36ad53b2a16f4f276197a24f1d8` |
| `SOURCE_MANIFEST_T1B.json` | 11277 | `db2d4f4076270c3bf4b0a82f1af74eddc2d99e2a92824bf7031a9f00ef27adf9` |
| `SOURCE_MANIFEST_T1C.json` | 13231 | `89c17fddc3063e3b425f5845cdeb5b9b979f65246cf2f53b4e99d2ab4df40012` |
| `SOURCE_MANIFEST.json` | 8243 | `0db2fcdb01965110ec15f2d032fc6014f7890bd043a15a46e60f9e588c4a580e` |
| `STATIC_CHECK_T1B.json` | 2069 | `70304deec5fa62c93c94ad9dd8f8e317b755afc7fb8d41681352b63178eb30e7` |
| `static_check_t1b.py` | 4887 | `0a6027a4251c7e8b254987da9f18419404947cd70e2a973764dc068269f314a1` |
| `STATIC_CHECK_T1C.json` | 2487 | `e0080774f5238bfef217f3d8e2d0f43d6b2ac0fd862f0e66afd575bae19927bb` |
| `static_check_t1c.py` | 5233 | `e3bc4102fc728caedeb3883984b1db8d789bf7f8dbfe95f1215498812485c49c` |
| `STATIC_CHECK.json` | 1437 | `f3f386f4a00311e4b5a99925c278272132b516cb85f1c04926b2a428991a16df` |
| `static_check.py` | 4315 | `53b60e221765557cbbc9994d9bb29b101f7b65bbf948e391e491203d85954821` |
| `STATUS_T1B.json` | 281 | `b93b5a384b1af709a9061ec4daa95ad637c814fc5ff47932230994dd305e821e` |
| `STATUS_T1C.json` | 281 | `506bf166157abce74d8415af9fb4441d5618717f0394ef07a4b9500427bad078` |
| `STATUS.json` | 279 | `d5de8eb760814d46808f6e5f0e731e2fb46bc6d9ccb32a3d243ea77f8d386173` |
| `supervisor_t1b.ps1` | 6458 | `d1c2e580b24396a20638305595b3c8834b19895ef51e39cfad8ac1fa7cdd282c` |
| `supervisor_t1c.ps1` | 6514 | `87b5de585ab59ca6602e9d692ef92689c89942516e25b78f6f8e95343d67d9fc` |
| `supervisor.ps1` | 6301 | `39654f795b07e6ef6db0b8fdea63cb9edb8f56f1304bcd5df35c966d41dda77a` |
| `t1b.py` | 13121 | `4a175cad7f95266cf3a86a1974ed2a0c6e30dceab73295037dab85b1c46b0b46` |
| `t1c.py` | 5260 | `5afecfb42c7f763487cea70ca565f10edb897ff4e74f1458761187ce42fd04f5` |
| `test_lm_t1.py` | 11799 | `2e6880a7c13a14022814f664e45cb5246bf024e61de754ab459a8e5942d60ce2` |
| `test_lm_t1b.py` | 4150 | `473fec265b39a685c012e45194ea51c77fe130e0088d025823ebdec8ce468ca6` |
| `test_lm_t1c.py` | 1595 | `27410bf408c430718eba060d484154efb1610c4a496516ec165657665326cdd2` |
| `worker_t1b.py` | 7389 | `ceeb309b8c468ee7897f6287afb265cfc5f82fe35e3a4ee48702f07bc84e8b0e` |
| `worker_t1c.py` | 6182 | `fa32d686933aef74afcc33e57a2ec8e74e50dadc772bf188d1e6068ac6f2ee84` |
| `worker.py` | 9615 | `bb54388f8246c706d9b93b543cd04007abba864aabfcb3593a6e8d014b456669` |

## Files added or changed in `language_v3`

Three copied files were changed. Everything else in the first table is byte-identical to the base, which is what
the first table's hashes prove.

| file | bytes | sha256 now | what changed |
|---|---|---|---|
| `cce.py` | 46446 | `7135d3958ad5890a148fcb65f307b89b9f9966a1b9e25cd7a9a5e1e62a5ee614` | added the `p/q` number form: `FRACTION_RX` inside `NUM_RX`, and `fraction_value`, `is_terminating`, `_place`, `fraction_text_of`, `_decimal_of`, `num` and `decimal_text` replacing the `Decimal`-based `num`; the `LOSSY_CONVERSION_REFUSED` refusal; the coefficient sign check moved from `Decimal` to an exact `Fraction`; and the REFUSE and CLOSE forms in `parse` and `render` with the `_bare_turn` guard. No frame, template, alias, tail word, relation, existing refusal code, nesting limit, fractal rule, recipe shape or normalization rule was touched. |
| `coverage.py` | 12561 | `2919d2d803eb184b812a0ba92f4594c3962b953a0b8536c848ac0b8e23e8eb5f` | the U-TURN side universe takes its charge from a new `TURN_CHARGES` table, in which REFUSE and CLOSE are charged because the grammar now has their forms. The universe, its six cells and their probe contents are unchanged. |
| `README.md` | 7168 | `30d46e6b1587e0acfb80f461a719a898dcdc360a52606236218813ed802a24b3` | the base's own README text is kept word for word; added around it are how to run from inside the repo, the `PYTHONPATH` the base needs, and what this folder adds. |

Files added here; none of them came from the base:

| file | bytes | sha256 |
|---|---|---|
| `PROVENANCE.md` | this file | not listed: a file cannot hold its own sha256 |
| `MEASUREMENTS.md` | 6230 | `173ca6eef56d04d9472dda5a14871ed39241f074cb1b63b1e5355fadf63096d2` |
| `GRAMMAR_CCE_v0_1_v3_ADDENDUM.md` | 6733 | `c6c93153cc937ddb6adf086ed9963f6dbc77df340278c0a6c817c079b7d27cbb` |
| `test_lm_t1v3.py` | 12738 | `f149b2f24444d2414530b17834cec96012e73981f8ecaf17a540d9dc8d89dc46` |
| `measure_marks.py` | 4589 | `e3fe0d6ae93a7968a0b6a31fea688c33441f22d188f46686ba66733e81328048` |
| `run_suites.py` | 1987 | `ebd3765b18322489c30215838f1626dc41f34f7d17aa084407f392a479d52058` |
| `MEASURE_BEFORE.json` | 9126 | `90d93ab61f280339927f58fb51f85171c6aa35c10a12dac9a3db04f76bbae3ea` |
| `MEASURE_AFTER.json` | 8958 | `438f8e4bbf6e5a1a2de05d3d618f0e16d96b022d59511be54e06618673377e9f` |

Every hash above is the hash of the file as committed. To check one, from this folder:

    Get-FileHash <file> -Algorithm SHA256

`SOURCE_MANIFEST.json`, `SOURCE_MANIFEST_T1B.json` and `SOURCE_MANIFEST_T1C.json` are the base build's own records
of the bytes it ran on, and they still list the base's `cce.py`. They were deliberately not rewritten, because
they are the record of the 2026-10-14 run, and because `worker.py` verifies them: a future run would need its own
manifest, not an edited one of these.
