# CAS Harness v2 preregistration and Evidence Packet v2 control kernel

Document status: `DRAFT / OPEN / NOT FROZEN`

Decision status: `OPEN / KEEP_OPEN`

Engineering status: `RING 4 / BOUNDED SOFTWARE CANDIDATE TESTED`

Experimental execution status: `NOT_STARTED`

License / disclosure / canon status: `NOT LICENSED / HELD / NOT FROZEN`

Live / product route status: `unavailable / not authorized`

This document specifies the isolated control kernel in
`src/cas_harness_v2`. It does not close Gate 5, execute an experiment, add a
live-worker route, authenticate a worker, change a product verdict, license a
claim, authorize disclosure, or establish production readiness.
It creates no live-execution, scientific, canon, product, license, or disclosure
authority.

The packaged private adapter now includes tested controller-only outcome-seal,
Packet-v2 attachment, explicit-nonreporting, and reconciliation paths as
bounded software around this isolated kernel. Exact transport envelopes remain
separate from the normative kernel carriers. The application reconstructs each
request-local chain from retained server facts, reserves one declared untrusted
outcome time, and uses a create-only Packet-versus-nonreporting intent bound to
the planned final artifact. Reconciliation binds strict per-run replay to a
separately limited configured-scope report. These controls do not change this
kernel's trust ceiling, prove provider-backed startup, create trusted time or
WORM authority, establish absence of off-registry execution, or authorize a
live route or experiment.

## Current RunPod readiness checkpoint (2026-08-12)

Build-only run `31566811228` at exact commit
`b163fee30634a21d2e717eda8a33de287426ee41` registry-verified the private image
`ghcr.io/littlehenderson/noetic-compass-stagec-qwen-batch@sha256:69f7e43a79501a075c50adff4c4f2fd7ec2932c62213e76144ea16a1b86b6df2`
and config digest
`sha256:e56c9971a93ce3ae5cf51c49440093620006e2fcad8ee890fd1b1732ede481b1`.
This evidence does not create an activated preregistration or worker.

Read-only UI inspection found pod `zp2s9pscgncn0b` stopped and unlocked, with
one A40 offered at `$0.44/hour` and stopped storage displayed at about
`$0.014/hour`. It still named the incompatible
`runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04` image, inherited
`8888/HTTP` and `22/TCP`, had an empty container start-command override, and
showed no selected registry credential. UI balance surfaces disagreed at
`$86.97` and `$105.54`; usable balance is unresolved. No change was saved.

The exact no-spend preflight itself made two authenticated GET observations and
passed its narrow observation schema: 71 billing rows and
`$0.982638896210119131` over the exact observed 72-hour window. Observation:
`9447` bytes / SHA-256
`081BE716EE26E5FA572F69614CEA21EF59E183295D30F8994D49246527F0EA82`.
Blocked plan: `7848` bytes / SHA-256
`705DF68AA8CFB7673C2313E0F2FA420739DB204BD6413ABCB48430351972603E`.
The plan records `application_capability: ABSENT`; no mutation or start follows
from the observation PASS.

The additive offline package candidate is 41 byte-mirrored Python files, 1,242
exports, and 2,551,834 bytes; its focused additive contract slice passed 383
tests. Three expanded same-process suite receipts now hold current authoritative
software-test status within `STRUCTURE_ONLY / NON_AUTHORITY` scope; the current
integrated 12-suite same-run PASS is recorded below within that same limited
scope. The published-baseline
receipts below are historical. The corpus scaffold
is `DRAFT / SYNTHETIC / NON_AUTHORITY`; real admissible corpus is `0 / 960`.

Provider mutations, pod starts, model invocations, and paid GPU compute by this
work remain `0 / 0 / 0 / $0.00`. Full stopped-pod update/readback and rollback,
private-registry credential validity, trusted time/nonce/ledger and WORM
readback, kernel/provider-backed no-egress, corpus authoring/double
adjudication, and post-start A40/BF16 evidence remain open. Gate 5 remains
`OPEN / KEEP_OPEN`; Stage C remains
`DESIGN_ONLY / UNAUTHORIZED / NOT_STARTED`; execution/disclosure remains
`NOT LICENSED / HELD / NOT FROZEN`.

### Current expanded same-process suite receipts

The current aggregate comprises three authoritative same-process suite
receipts. Their shared exact status is:

`AUTHORITATIVE SAME-PROCESS PASS / STRUCTURE_ONLY / NON_AUTHORITY`

The three strict-JSON receipt bundles bind verifier SHA-256
`87AA366193EBC0DDBFF6CF8ABC3C21C89ADA4B2322D543DD6058BAFB32C28B42`,
the pre-promotion 708-artifact manifest SHA-256
`507629AE1D90FB40F8AE197B75A9BB17FDBD2DE876C4A59AC6DDC96E24DA6620`,
and runner-lock SHA-256
`EB7D2D661BFE262C1E3BB4657E418EADE8339F35D1089C7AE6A87EFC6A360B13`.

- Harness bundle
  `gate5-expanded-harness-3eb295c211974984add34d4dbba9aad0.json`
  (`277731` bytes; SHA-256
  `526F02B798757CD58B70002F6507639BC3879750F5CD484A726AEAEA250007F0`)
  collected, started, and finished `1452` nodes. Exactly `1446` had all-phase
  PASS; the six exact setup skips remain mismatch evidence rather than PASS.
  It emitted `4350` ordinary reports and `163` passing subtests, recorded zero
  warnings, errors, collection errors, internal errors, or deselections, left
  the isolated pycache empty, and exited process/pytest `0 / 0`. Observational
  elapsed time was `2747.329161` seconds. Node-ID, ordinary-outcome,
  subtest-outcome, locked-import-origin, pre-test-loaded-code, and loaded-code
  SHA-256 values are, respectively,
  `4419F4BE8F2CCEE417763854814DA0FA5B7D4D6173BDAD18DF12F5AA06AFFC96`,
  `E600DEDCA64A9EBBA3584C6F44E4D69174817B13FD4E4B84F1B197BC935B8628`,
  `6C2AFB12D8F1DBC529C9493967B1CBB06AE98228B318DA724D093D3C84721109`,
  `3E1424E6BDBA7B6AE417189EF951E7502D108626EB5482277A627C9D6A29887A`,
  `0CBCB82DCF24426A868CFCA8DBC334661D1504A23C882DD342D5EC6767B30D98`,
  and `848B8099C06A7E3DBE5E970EAAE23ED228843934BA062D85CC3D307444DD6784`.
  Its exact status is `AUTHORITATIVE SAME-PROCESS PASS WITH SIX EXACT SETUP SKIPS / SKIPS ARE MISMATCH EVIDENCE, NOT PASS / STRUCTURE_ONLY / NON_AUTHORITY`.
- Worker bundle
  `gate5-expanded-worker-111768e866d8449cb4573292b1e4746a.json`
  (`98819` bytes; SHA-256
  `D7F939E268E26D2532E281EBBD16AF47D3B29392C9D87E211A15B8988A64F10F`)
  collected, started, finished, and passed all `732` nodes, emitted `2196`
  ordinary reports, and recorded zero skips, subtests, warnings, errors,
  collection errors, internal errors, or deselections. It left the isolated
  pycache empty, exited process/pytest `0 / 0`, and had observational elapsed
  time `162.481646` seconds. Node-ID, ordinary-outcome, subtest-outcome,
  locked-import-origin, pre-test-loaded-code, and loaded-code SHA-256 values
  are, respectively,
  `F53562BAECCC4982C402A9A747F8CADC29468B5F14D8B4A8C17CFC2A8E89B568`,
  `889E455626A3DC5F7EC26CFC253CABED4572F0F9E95E68CCF56142380404664E`,
  `4F53CDA18C2BAA0C0354BB5F9A3ECBE5ED12AB4D8E11BA873C2F11161202B945`,
  `035EFFD9DC44C1FD2D9F07A3BE62EA1BF07E3FD17D5807323F8D1B58AE6B0FD6`,
  `3696A5457FDF85823DAC360679C750DEC5B8A691207958EE0A1854A790A21A5E`,
  and `58A306279E05EBDF7F4C18A8B153170AB058C7DACF906D5E00AB92372F018681`.
  Its exact status is
  `AUTHORITATIVE SAME-PROCESS PASS / STRUCTURE_ONLY / NON_AUTHORITY`.
- Adapter/reconciliation bundle
  `gate5-expanded-adapter-ac618af4947f40d9a0175d9fc721acfe.json`
  (`16513` bytes; SHA-256
  `44455E29889D9B1C5E958763368E50716A195BDDF9DC0778FA1A469C0318F6B4`)
  collected, started, finished, and passed all `99` nodes, emitted `297`
  ordinary reports, and recorded zero skips, subtests, errors, collection
  errors, internal errors, or deselections and exactly one warning. It left the
  isolated pycache empty, exited process/pytest `0 / 0`, and had observational
  elapsed time `55.537553` seconds. Node-ID, ordinary-outcome, subtest-outcome,
  locked-import-origin, pre-test-loaded-code, and loaded-code SHA-256 values
  are, respectively,
  `B84EB29C59563DD0270C3BD8B230D604D59A2E45D38B9E375C7FA697468D656B`,
  `548361800978AF55EE04B8E45B71AE70A09BBBE015025C5D6BF428F8E2FD9C9F`,
  `4F53CDA18C2BAA0C0354BB5F9A3ECBE5ED12AB4D8E11BA873C2F11161202B945`,
  `3E1424E6BDBA7B6AE417189EF951E7502D108626EB5482277A627C9D6A29887A`,
  `0CBCB82DCF24426A868CFCA8DBC334661D1504A23C882DD342D5EC6767B30D98`,
  and `EFA05FB2B5AEA5000FFB8B77F910A06C14F1BA433A4DC1CCE71474807F708F53`.
  Its exact status is
  `AUTHORITATIVE SAME-PROCESS PASS / STRUCTURE_ONLY / NON_AUTHORITY`.

The pre-RunPod `1082`-node Harness and `719`-node worker receipts remain
`HISTORICAL / SUPERSEDED NODE SET / NON_AUTHORITY`. The pre-RunPod `99`-node
adapter receipt and every older receipt remain
`HISTORICAL EVIDENCE ONLY / NOT CURRENT-TREE SUBSTITUTE / NON_AUTHORITY`.
No historical receipt is rewritten or promoted.

Current integrated 12-suite replay status is `AUTHORITATIVE CURRENT-TRANCHE INTEGRATED 12-SUITE PASS / LOCAL ENGINEERING / STRUCTURE_ONLY / NON_AUTHORITY`. Run `retry-20260812T203610Z-c2861637` executed exact command `C:\Python314\python.exe -I -B scripts\verify_project_coherence_gate5.py`, exited `0`, and observed the exact PASS line across `12 / 12` suites and `2672` configured nodes. It revalidated `708` bound artifacts, `475` syntax-checked Python artifacts, `2317` executable-shadow paths before and after tests, `52` review criteria with `22` required `OPEN` boundaries, and `1280` postflight file identities. Loaded-code SHA-256 values for Harness `1452`, worker `732`, and adapter/reconciliation `99` were `848B8099C06A7E3DBE5E970EAAE23ED228843934BA062D85CC3D307444DD6784`, `58A306279E05EBDF7F4C18A8B153170AB058C7DACF906D5E00AB92372F018681`, and `EFA05FB2B5AEA5000FFB8B77F910A06C14F1BA433A4DC1CCE71474807F708F53`. Before/after input identities were identical: verifier `931351` bytes / SHA-256 `E687BD3BD01926763E737EE82C17AADB2222CBCC78172C500A7E5715C1C51D38`; manifest `204635` bytes / SHA-256 `74A42ED7CFB252A8F14B0E72735DBB9C0DD711CC7536063BBD84A7345BECDB62`; runner lock `121525` bytes / SHA-256 `EB7D2D661BFE262C1E3BB4657E418EADE8339F35D1089C7AE6A87EFC6A360B13`. The result `retry-20260812T203610Z-c2861637.result.json` is `3189` bytes / SHA-256 `9186AC199ADB038E4C462A5B420C1B777D95EDE694EB4DF3D803C8EFE3BA9FFB`; stdout is `11116` bytes / SHA-256 `AA4C46BA71EA2467C6963C21A8C54C70906943BB14644607AC98A7FF2950751C`; stderr is `0` bytes / SHA-256 `E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855`. Supervisor wall time `2813.248` seconds is observational only and carries no performance authority. No run ordinal, whole-run aggregate digest, trusted-time receipt, or WORM receipt is claimed. The replay used no RunPod, made no model invocation, and spent `$0.00`. It does not close Gate 5, authorize Stage C, admit any corpus row, license or disclose a claim, or establish scientific, provider, WORM, trusted-time, or product authority. Gate 5 remains `OPEN / KEEP_OPEN`; Stage C remains `DESIGN_ONLY / UNAUTHORIZED / NOT_STARTED`; real admissible corpus remains `0 / 960`; license/disclosure/canon remains `NOT LICENSED / HELD / NOT FROZEN`.

### Prompt-context provenance input obligation

The audit-only prompt-context family adds three schemas:
`cas_harness_v2.stagec_prompt_context_node.v1`,
`cas_harness_v2.stagec_prompt_context_provenance.v1`, and
`cas_harness_v2.stagec_prompt_context_inventory.v1`. Its four exact media
values are the node, provenance, and inventory JSON media types plus
`text/plain;charset=utf-8` for external source bytes. The only allowed graph
operations are `SOURCE` and ordered `UTF8_CONCAT`; normalization and declared
origin-to-chat-role coercion are forbidden.

These are companion artifacts, not a preregistration amendment or execution
authority. The additive Stage C prerequisite helper requires the exact aggregate
inventory ref in any future immutable diagnostic base `design.input_artifacts`,
and the structural activation candidate now calls it under controlled fixtures.
No actual real base or authenticated bundle has reached that path and no
deterministic real DRC has executed. Corpus freeze remains
`NOT_ESTABLISHED`. Focused structural receipts are 30/30, 22/22, 52/52, and
98/98 with the diagnostic Study. They create no detector, Packet v2, claim,
license, product route, trusted time, WORM proof, or scientific conclusion.

### Stage C prerequisite-admission companion

`diagnostic_stagec_prerequisite_admission.py` adds a separate exact-key
structural intake before diagnostic preregistration. It does not modify
`cas_harness_v2.preregistration.v1` or
`cas_harness_v2.diagnostic_preregistration.v1`. Six primary schema/media pairs
cover the detector DRC receipt, frozen-corpus bundle, trusted-storage receipt,
execution-authorization candidate, owner-intake assertion, and prerequisite
admission. Twelve additional schema/media pairs cover the exact role-specific
dependency bodies, for 18 pairs total and 62 public exports.

The factory first full-replays the one exact 160-group/480-row C-Cal split and
prompt-context inventory. Its target includes their raw identities and ordered
digests, the full prompt dependency count/digest, model and capture-profile
digests, and capture-request closure. Candidate loaders then require:

- a Stage C detector DRC profile, frozen closed ruleset, and known-fault fixture
  with every fixture rejected and zero false accepts;
- an exact 320-group/960-row three-variant corpus with disjoint 160/80/80 group
  assignment, adjudication, and surface bundle;
- corpus-bound Object Lock, readback, trusted-time, and verifier-identity
  candidate bodies; and
- a C-Cal-only authorization instrument, one prospective window, exact
  480-attempt/zero-generation/zero-intervention scope, and an unconsumed
  canonical 32-byte nonce.

The prospective subject is derived from the target plus DRC, corpus, and
storage refs before authorization, avoiding a cyclic self-binding. The owner
intake records `OWNER_ASSERTS_PRESENT` and binds all four exact candidates. The
only admission decision is
`ADMITTED_FOR_PROSPECTIVE_PREREGISTRATION_ONLY`.

`require_stagec_prerequisite_admission_in_preregistration` requires 19 exact
prerequisite refs in the immutable diagnostic base `design.input_artifacts`:
the prompt inventory; four primary candidates; their 12 dependencies; owner
intake; and admission. The exact C-Cal split remains the base split source.
These refs cannot be supplied only by amendment. Prompt/candidate/intake/
admission creation, base creation, ordered amendments, verifier observation,
authorization window, and storage retention must remain in strict prospective
order.

The focused receipt is 19/19 PASS with source SHA-256
`AD46AA964240C98D5C12070872C60B26E2310B35A88DD6FA50F68C10C62F09B3`,
test SHA-256
`56A9BCE442405EE57BFF95A735F5D80724A0F72B06136A8B4AEEC36A41F336A3`,
and node-ID SHA-256
`3785ADB97900ABAB40242DFD6DF1D0665B9996BAE94EC2697672A8506DCBE863`.
The last completed pre-runtime locked same-process Harness receipt, now
preserved historically, collected, started, and finished 537 nodes in 1,680.3
seconds. Exactly 531 had exact
all-phase PASS; the same six exact nodes setup-skipped as runtime-lock mismatch
evidence, not PASS. It emitted 1,605 ordinary reports/outcomes and 163 passing
subtests, recorded zero warnings, errors, collection or internal errors, or
deselections, left the isolated pycache empty; pytest and the verifier process
each exited 0. Node-ID, ordinary-outcome, subtest-outcome, locked-import,
pre-test-loaded-code, and loaded-code SHA-256 values are, respectively,
`3AA22AE520FD2604AB8E8B1EAA6ED4A955DDDEB4BEBEF95F8B750A163AA5FB19`,
`423154C5C83DF299F844E87D289CBB98E331B302CE1ABA8AEA7075A12B1C0EFF`,
`6C2AFB12D8F1DBC529C9493967B1CBB06AE98228B318DA724D093D3C84721109`,
`3E1424E6BDBA7B6AE417189EF951E7502D108626EB5482277A627C9D6A29887A`,
`0CBCB82DCF24426A868CFCA8DBC334661D1504A23C882DD342D5EC6767B30D98`,
and `C186ACEBF8165A195A4D66AF968A58E323B4C5943E84191DAA2CEF72FBD2B473`.
That historical integrated verifier PASS covered 637 artifacts, 409 syntax-checked Python
files, and 2,255 executable-shadow paths. The preceding 508-node receipt is
preserved as a historical checkpoint: 502 all-phase passes plus the same six
exact setup skips, 1,518 ordinary reports, 163 passing subtests, and node-ID
SHA-256 `8CDBA8F539912573D04723F39AD819C413F8AE5B69006BDC43E653F6AF6CCAE2`.

The receipt uses structural fixtures. Candidate JSON is not a provider trust
root and does not establish an actual DRC run, actual 960-row corpus freeze,
Object Lock/readback/trusted-time authenticity, authoritative runtime
authorization or nonce consumption, out-of-band prevention, or execution.
Gate 5 remains `OPEN / KEEP_OPEN`; Stage C remains
`DESIGN_ONLY / UNAUTHORIZED / NOT_STARTED`; `NOT LICENSED / HELD / NOT FROZEN`
is unchanged.

### Stage C read-only external-intake companion

The external-intake companion supplies a deterministic local-filesystem route
into the prerequisite-admission loaders without changing either
preregistration schema. The library contributes 20 public exports and three
wire pairs:

- `cas_harness_v2.stagec_prerequisite_external_locator_manifest.v1` /
  `application/vnd.cas-harness.stagec-prerequisite-external-locator-manifest+json`;
- `cas_harness_v2.stagec_prerequisite_external_intake_report.v1` /
  `application/vnd.cas-harness.stagec-prerequisite-external-intake-report+json`;
- `cas_harness_v2.stagec_prerequisite_external_binding_report.v1` /
  `application/vnd.cas-harness.stagec-prerequisite-external-binding-report+json`.

The isolated CLI contributes the context-locator and CLI-report pairs:
`cas_harness_v2.stagec_prerequisite_context_locator.v1` /
`application/vnd.cas-harness.stagec-prerequisite-context-locator+json` and
`cas_harness_v2.stagec_prerequisite_external_cli_report.v1` /
`application/vnd.cas-harness.stagec-prerequisite-external-cli-report+json`.

The fixed external manifest contains exactly 16 explicit roles (the four
candidate carriers and 12 dependencies), each with a canonical relative path
and exact artifact reference. Filenames never imply roles. Sources must be
stable absolute local files; ambient-CWD, UNC/device, and mapped-network input
are rejected. Reports retain hashes, lengths, media types, counts, and closure
digests but no source paths. The importer performs no writes, network/provider
actions, nonce issuance/consumption, corpus freeze, trust authentication, or
model execution.

Frozen SHA-256/byte identities are library
`865707DBBE5BE1560FFD1F065378C505BE89E48156F853166BC0E6CDA5896BB4` /
38,821; library test
`8E82DA357BE1DB0649BE069AC307C2AD1C1F380E9730B43240A4E26ABDBD7B5D` /
18,129; CLI
`24DDDB2D357DE5D9737DE325BF405C28F05467DBF5182BAA410BE08E25A9F1B5` /
31,668; CLI test
`E3014790E97872F825AA30865C0E3C4912B747C0DE7BC5F8B030C9C45508AA0B` /
14,844; and evidence helper
`969586F5FE5ED93C86F12F455D961E5EDFED62E023910F590772A9DD479BBC29` /
24,247.

The current focused receipt is 19 library plus 10 CLI nodes, 29/29 PASS in
47.72 seconds, zero subtests, pytest exit 0, and node-ID SHA-256
`A2D250135113EDD038C37040C94E11EE6E8B6208E14D53270F318FF48F06AD80`.
An independent pre-final audit passed 28/28 in 47.93 seconds and found no P0/P1
issue. The 537-node full-Harness receipt is the integrated pre-runtime replay
recorded above. The 508-node replay remains earlier historical evidence;
neither is a current-tree replay.

The companion is `NON_AUTHORITY`. The next protocol step is a real exact 4+12
intake and immutable base binding, followed by a separate post-plan runtime
activation that authenticates and atomically consumes its authorization.

### Stage C structural runtime-activation companion

`diagnostic_stagec_runtime_activation.py` now defines the post-plan structural
control seam. It does not modify preregistration or Evidence Packet schemas and
cannot create authority. Canonical source and test identities are
`E4B9C390117A474B32DB790B5B7CB8DC2E3022823FF6F2F718725B1B3826E52E` /
133,262 bytes and
`5CCF0EEC47D1814A9CA46FC047DD089F415D113D990F234659460261971E1ACF` /
52,693 bytes; the packaged source mirror is byte-identical. The unchanged-byte
focused receipt is 28/28 PASS in 922.45 seconds at node-ID SHA-256
`5D501F3505A98E23BDD2AB8B191BC6EEE90260F1F169940B6A6F70A61525A632`.

The companion binds sealed prerequisite, diagnostic-base, phase, attempt,
request, capture-profile, model, authorization, storage, issuer, ledger, and
worker-lease identities. Only disposable deep-copied expectations cross a
backend boundary; all observations are detached and rechecked. Phase and claim
state advance by compare-and-swap. A control-owned operation ID permits an
ambiguous backend-crossed claim to be durably terminalized by immutable logical
row as `INDETERMINATE` without trusting a malformed returned claim ID. Permit
invalidation and redemption are single-use monotone transitions.

The worker gate and capture pair enforce the same exact row and model-call
boundary. Gate source/test hashes are
`FC918942B2D324BCE1882577166A1F3FCFE8A98AAE2D5A39F90E0DCCD9B970B4` /
61,983 and
`0A3A177079AD28542C89F1EA9D745E448B6F6F3A7276DE26AD3EB62C72205489` /
49,357 bytes; 95/95 pass at node digest
`0554F3710F9A35667A462CAF53584C9517CF945BFC64811765ACFB4E7CC7BCD3`.
Capture source/test hashes are
`0ECD006E3799A70FFED72688015C03BC2A1D8107BC25632FD93D87435D06519C` /
124,345 and
`E21ED834800845E51223203DF018DCDEFAE43FB60E2FC7D0D43017EE99676A7E` /
84,540 bytes; 139/139 pass at node digest
`C306D70A052CDA8C0CFB12394B640A2ED2DDE9FEE58F16E92FF23771CAABFED1`.
The gate-plus-capture union is 234/234 at digest
`08CAA558DEE27A5876DA29A15E9D0E3875994C630E2826BC52154DC215776E76`.

Capture marks its redemption attempt before the control call and requires the
matching durable `CALL_STARTED` receipt before exactly one direct Qwen forward.
Duplicate, stale, drifted, mutated, or ambiguous inputs terminate without
retry. The Qwen generic-route exclusion surface has test SHA-256
`08A6D58EA0E9D083D13CCC57A62956A23EEEC85D79C8F4C2F62F7DDE60320A3B`
/ 27,690 bytes and 27 configured nodes at digest
`D80B52FFC48D0677F773269F640481A4C1CA0C434C707041FF391EA75BE90ECA`;
all 27 nodes passed as an exact executed subset of the preserved historical
719-node worker same-process receipt. Generic stream, cache,
Pythia, canary, and real ablation paths reject Qwen/cross-family/aliased carriers
before tokenizer, hook, or model-forward use.

The packaged kernel is now 22 byte-mirrored files, 469 unique exports, and
1,420,002 bytes under provenance SHA-256
`1561D0707AEB12ED720A1F70670494006B186628434CB6390A4DEEFBA5040D07`;
13/13 package tests pass, and the runtime module contributes 44 exports. Four
new unique worker schemas and zero new media types yield 49 schemas and 44 media
types total.

The preserved runtime-activation Harness checkpoint collected, started, and
finished 565 nodes in 2,477.3 seconds at node-ID SHA-256
`4CCAD2A4EF4868EBAD7EBDC9E219371A57CBE69C974E5D986A8714A0A0DDE601`:
559 nodes had exact all-phase PASS, the six exact setup skips remain mismatch
evidence rather than PASS, 1,689 ordinary reports and 163 passing subtests were
emitted, and warnings, collection or internal errors, and deselections were
zero. The isolated pycache remained empty and process and pytest exits were 0.
Its exact receipt digests are ordinary outcomes
`7FCD1D82405624E07792CD92DC5F9E40904F2B43FB723CC2DEFF5A7E2C4DDB6E`,
subtest outcomes
`6C2AFB12D8F1DBC529C9493967B1CBB06AE98228B318DA724D093D3C84721109`,
locked import origins
`3E1424E6BDBA7B6AE417189EF951E7502D108626EB5482277A627C9D6A29887A`,
pre-test loaded code
`0CBCB82DCF24426A868CFCA8DBC334661D1504A23C882DD342D5EC6767B30D98`,
and loaded code
`24F868086F5B21A263D06229B5FBEC36FC572878F0C2AA710001BCAF9C0CAE07`.

The preserved runtime-activation worker checkpoint passed 719/719 in 42.035
seconds at node-ID SHA-256
`98F7152B532C713DD22DF910FB762CE92E281A350ACA4E1A3CF2113C84D3DBB5`,
with 2,157 ordinary reports, zero subtests, skips, warnings, errors, or
deselections, an empty isolated pycache, and process and pytest exits 0. Its
exact receipt digests are ordinary outcomes
`CF7F1676BAAA3E83999E758A35F311743B7B227DBD0A160EF79F85AA72477468`,
subtest outcomes
`4F53CDA18C2BAA0C0354BB5F9A3ECBE5ED12AB4D8E11BA873C2F11161202B945`,
locked import origins
`035EFFD9DC44C1FD2D9F07A3BE62EA1BF07E3FD17D5807323F8D1B58AE6B0FD6`,
pre-test loaded code
`3696A5457FDF85823DAC360679C750DEC5B8A691207958EE0A1854A790A21A5E`,
and loaded code
`4B37B98E99C132E65C7095EBD0FC42A44E9C701923FD451DACC25EEC45636FBB`.
For the preserved 565-node Harness receipt only, `loaded_code_sha256` uses `CANONICAL
VALIDATED LOADED-MODULE RECORDS / NORMALIZED-PROJECTION V1 / EXACT VERIFIER
SELF-RECORD BYTE COUNT AND SHA-256 NORMALIZED TO ZERO ONLY IN THE AGGREGATE
DIGEST / ACTUAL VERIFIER BYTES REMAIN MANIFEST-BOUND AND REVALIDATED`. The
preserved 719-node worker and the preserved 537- and 508-node historical Harness
loaded-code digests use `CANONICAL VALIDATED LOADED-MODULE RECORDS / RAW
RECORDS / NO PROJECTION`; their recorded values remain unchanged.
At that checkpoint the complete verifier suite-map count was 1,772, not merely
the sum of these suites. The 565-node Harness, 719/719 worker, 537-node Harness,
594/594 worker, and 99/99 adapter/reconciliation receipts are preserved
historical checkpoints, not promoted; all remain
`STRUCTURE_ONLY / NON_AUTHORITY`. No real
authenticated exact 4+12 bundle, positive storage/issuer/ledger backend,
actual nonce consumption, model/provider execution call, result, or Packet
exists. Gate
5 remains
`OPEN / KEEP_OPEN`; Stage C remains
`DESIGN_ONLY / UNAUTHORIZED / NOT_STARTED`; claims remain
`NOT LICENSED / HELD / NOT FROZEN`.

### Provider-neutral comparison and recovery companion

Fourteen additive modules define a separate `STRUCTURE_ONLY / NON_AUTHORITY`
comparison and recovery companion. They do not modify the preregistration-v1,
diagnostic-preregistration, Study, worker-authorization, terminal, or Evidence
Packet-v2 schemas. They add no conversion from replay evidence into execution
or claim authority.

The model protocol binds exact open-weight, closed-weight, and replay identities
and their capability evidence. Replay and unavailable adapters are the only
installed backends. A frozen shared roster requires one exact open role, one
exact closed role, and three ordered rows per matched group:
`ADVERSARIAL_PRESENT`, `CLEAN_ABSENT`, `CLEAN_NULL_ABSENT`. The paired runner
consumes both one-use replay streams and returns only their complete canonical
association.

Prompt-injection evidence remains layered: text/context, open hidden state, and
runtime policy are independent carriers. A combined binding preserves
disagreement but has no aggregate verdict. Hidden-state evidence for a model
without that capability remains `unavailable`. Surface Gate and Meaning
Preservation receipts remain per-cell/per-axis records and create no overall
PASS.

The departure report derives deterministic signed `closed - open` component
metrics from frozen rows and caller-supplied scores, with matched-group
uncertainty and no composite index. Steering plans and steering-effect
associations remain separately authorized, unavailable-only, and
non-executing; `ACTIVATION_STEERING` and `BLACK_BOX_POLICY_CONTROL` cannot be
relabelled as the same mechanism. The blocked-execution carrier is the only
buildable execution state and fixes calls and spend at zero.

Universal and distributed probe artifacts bind config-only discovery, semantic
probe definitions, topology, rank ownership, fragments, checkpointing, and
reconstruction without model, GPU, filesystem, network, or distributed-runtime
execution. The disabled J-Space `SHADOW` contract binds source verification and
vector JVP/VJP protocol structure without import, autograd, verdict, or license.
The historical importer is read-only and emits only
`HISTORICAL_EVIDENCE_ONLY`; it cannot supply current Packet outcomes.

The expanded package candidate contains 41 byte-mirrored files, 1,242 unique
exports, and 2,551,834 bytes; its focused additive RunPod/corpus contract slice
passed 383 tests. The three current expanded same-process suite receipts and the
current integrated 12-suite same-run PASS are recorded above within
`LOCAL ENGINEERING / STRUCTURE_ONLY / NON_AUTHORITY` scope.

At published baseline commit
`b163fee30634a21d2e717eda8a33de287426ee41`, the package candidate contained 36
byte-mirrored files, 1,097 unique exports, and 2,332,110 bytes. The configured
Harness inventory was 1,082 nodes at node-ID SHA-256
`E791E0A7960201323A94F8B0BC88F53AF611771118A369D332B36100D80B7928`;
the configured worker inventory was 719 at node-ID SHA-256
`98F7152B532C713DD22DF910FB762CE92E281A350ACA4E1A3CF2113C84D3DBB5`.
The detailed receipts below are exact historical receipts for that baseline,
not an expanded-current-tree PASS. At that baseline, same-process suite
receipts were authoritative software-test PASS within
`STRUCTURE_ONLY / NON_AUTHORITY` only. Harness collected, started, and finished
1,082 nodes: 1,076
all-phase PASS, six exact setup skips retained as mismatch evidence, 3,240
ordinary reports, 163 passing subtests, and zero warnings, errors, collection
errors, internal errors, or deselections. Process/pytest was 0/0, pycache was
empty, and elapsed time was `3059.695080` seconds. The elapsed value is
observational only and carries no performance authority. Its exact
node/ordinary/subtest/origin/pre-test/loaded digests are
`E791E0A7960201323A94F8B0BC88F53AF611771118A369D332B36100D80B7928`,
`60F1AB42E3BA883AA3C093F506C4B0896E498C1FC3258A887895C596AAA38F29`,
`6C2AFB12D8F1DBC529C9493967B1CBB06AE98228B318DA724D093D3C84721109`,
`3E1424E6BDBA7B6AE417189EF951E7502D108626EB5482277A627C9D6A29887A`,
`0CBCB82DCF24426A868CFCA8DBC334661D1504A23C882DD342D5EC6767B30D98`,
and `DC4F9C8664415C211D257DFFBFD8D0DBC942F830C138C60D6AC3A0E8D4EAC768`
under `CANONICAL VALIDATED LOADED-MODULE RECORDS / NORMALIZED-PROJECTION V1 / EXACT VERIFIER SELF-RECORD BYTE COUNT AND SHA-256 NORMALIZED TO ZERO ONLY IN THE AGGREGATE DIGEST / ACTUAL VERIFIER BYTES REMAIN MANIFEST-BOUND AND REVALIDATED`.

Attempt 3's earlier same-process PASS is preserved as historical evidence with
the same counts and node, ordinary, subtest, origin, and pre-test-code digests,
elapsed `3350.340165` seconds, and loaded-code SHA-256
`B95348D54FD003715848CBD27B79D3D486DE182E3CF9717E176E5883C7675826`
under the same digest rule. Its elapsed value is also observational only.

Worker passed 719/719 with 2,157 ordinary reports, no subtests, warnings, or
errors, process/pytest 0/0, empty pycache, and `106.254353` seconds. Its exact
digests are
`98F7152B532C713DD22DF910FB762CE92E281A350ACA4E1A3CF2113C84D3DBB5`,
`CF7F1676BAAA3E83999E758A35F311743B7B227DBD0A160EF79F85AA72477468`,
`4F53CDA18C2BAA0C0354BB5F9A3ECBE5ED12AB4D8E11BA873C2F11161202B945`,
`035EFFD9DC44C1FD2D9F07A3BE62EA1BF07E3FD17D5807323F8D1B58AE6B0FD6`,
`3696A5457FDF85823DAC360679C750DEC5B8A691207958EE0A1854A790A21A5E`,
and `44A6B0A13CAA30860D3802C042455F72C90FFC6D15FA7503F3B159384EFF4C34`.
At that published baseline, adapter/reconciliation had the authoritative
same-process receipt: 99
nodes were collected, started, finished, and had all phases pass; skips were
zero (`[]`); it emitted 297 ordinary reports, zero subtests, and one warning;
errors, collection errors, internal errors, and deselections were zero;
process/pytest was 0/0; and pycache was empty. Elapsed time was `25.401532`
seconds, observational only with no performance authority. Its exact digests are
`B84EB29C59563DD0270C3BD8B230D604D59A2E45D38B9E375C7FA697468D656B`,
`548361800978AF55EE04B8E45B71AE70A09BBBE015025C5D6BF428F8E2FD9C9F`,
`4F53CDA18C2BAA0C0354BB5F9A3ECBE5ED12AB4D8E11BA873C2F11161202B945`,
`3E1424E6BDBA7B6AE417189EF951E7502D108626EB5482277A627C9D6A29887A`,
`0CBCB82DCF24426A868CFCA8DBC334661D1504A23C882DD342D5EC6767B30D98`,
and `B543CD078076717C80341B0B9C52F158CBD20B9BB3718E4128F81373AEEA1101`.
Worker and adapter use `CANONICAL VALIDATED LOADED-MODULE RECORDS / RAW RECORDS / NO PROJECTION`.

The earlier adapter/reconciliation same-process PASS is preserved explicitly as
historical evidence with the same counts and first five digests, elapsed
`47.452869` seconds, and loaded-code SHA-256
`5C860DD3A7F787DD0826920D134796F42E02C74C1A4123F256982DF29CA499C3`
under the same raw-record rule. Its elapsed value is observational only. An
integrated verifier replay rejected that historical adapter loaded-code digest
as stale. This descriptive failure record infers no attempt ordinal and no
whole-run elapsed value.

Harness attempt 1 timed out at 3,600 seconds with no receipt. Attempt 2 ended
process/pytest 1 because of a stale manifest and produced no receipt. After the
manifest was rebuilt to 686 artifacts, targeted red-team checks passed 22 tests
plus 23 subtests; attempt 3 produced the now-historical Harness PASS described
above. An intervening Harness attempt failed at a literal host-throughput timing
gate. No full-suite receipt or exact elapsed value was retained for that failed
attempt, so none is claimed. The published-baseline replay then produced the
baseline PASS above. The suite ceiling remains 5,400 seconds and carries no
performance authority. Historical 565/719/99 receipts remain unchanged and
historical. The subsequent published-baseline integrated replay produced the
12-suite Gate 5
verifier result `AUTHORITATIVE INTEGRATED 12-SUITE PASS / STRUCTURE_ONLY / NON_AUTHORITY`. Its
exact command was
`C:\Python314\python.exe -I -B scripts/verify_project_coherence_gate5.py`; exit
status was 0. Tool wall time was 3568.3 seconds, observational only and with no
performance authority. All 12/12 suites passed. The verifier bound 686 manifest
artifacts and 457 syntax-checked Python artifacts, and observed 2,290
executable-shadow paths both before and after suite replay. Published-baseline
suite receipts were Harness 1,082 nodes with 163 passing subtests and six exact
setup skips at loaded-code SHA-256
`DC4F9C8664415C211D257DFFBFD8D0DBC942F830C138C60D6AC3A0E8D4EAC768`,
worker 719/719 at loaded-code SHA-256
`44A6B0A13CAA30860D3802C042455F72C90FFC6D15FA7503F3B159384EFF4C34`,
and adapter/reconciliation 99/99 at loaded-code SHA-256
`B543CD078076717C80341B0B9C52F158CBD20B9BB3718E4128F81373AEEA1101`.
Review remained 51 criteria with 22 `OPEN` boundaries, and postflight rechecked
1,258 files. Verifier stdout reported
`Project Coherence integrated Gate 5 verification: PASS`. No stderr claim is
made. This final replay has no inferred attempt ordinal and grants no Packet,
worker, model, execution, release, disclosure, or product authority.

The published-baseline executable-shadow path count is 2,290. The exact ignored
`noetic-compass-scaffold/noetic-compass/.tmp` transient trace subtree is
excluded from path-count authority because it is not an admitted
import/executable authority surface. All cache, native, and symlink checks
remain.

The real four-carrier plus twelve-dependency bundle remains absent. Exact
model/revision and the `$100.00` aggregate spend ceiling are bound in the
offline candidate, but a prospective consumable authorization window and
executable provider application path remain absent. The bounded preflight
itself made two authenticated read-only GET observations. Provider mutations,
pod starts, model/GPU execution, and paid GPU compute by this work remain
`0 / 0 / 0 / $0.00`.
Nothing in this companion changes Gate 5 `OPEN / KEEP_OPEN`, Stage C
`DESIGN_ONLY / UNAUTHORIZED / NOT_STARTED`, or
`NOT LICENSED / HELD / NOT FROZEN`.

## 1. Normative executable schemas

The closed, versioned schemas are enforced by exact-key Python loaders. The
loaders are normative because JSON Schema alone cannot verify raw-byte hashes,
claim-ledger membership, amendment-chain continuity, evidence bytes, or
cross-document identities.

| Artifact | Exact schema value | Loader |
|---|---|---|
| Per-claim preregistration | `cas_harness_v2.preregistration.v1` | `load_preregistration` |
| Preregistration amendment | `cas_harness_v2.preregistration_amendment.v1` | `load_amendment` or `PreregistrationChain.append_amendment` |
| Evidence Packet v2 | `cas_harness_v2.evidence_packet.v2` | `load_evidence_packet` |

The JSON profile rejects duplicate object keys, UTF-8 BOMs, invalid UTF-8,
non-finite values, JSON floating-point numbers, integers above 2,048 bits,
unpaired Unicode surrogates, NUL characters, excessive size/depth/node count,
unknown fields, missing fields, Boolean-as-integer substitutions, non-string
mapping keys, key-coercion collisions, and non-normalized machine identifiers.
Decimal measurements and thresholds are finite decimal strings.

Every successfully loaded artifact snapshots its exact input bytes and records
their SHA-256 and byte length. Loaded payloads are recursively immutable.

## 2. Per-claim preregistration

A preregistration binds one exact claim-ledger record to one frozen experimental
design. The claim binding contains:

- the exact raw-byte identity of `CLAIM_LEDGER_v0.1.json`;
- one `claim_id` and its exact `claim_text`;
- the canonical hash of the selected claim record; and
- the preregistration artifact's own detached raw-byte hash and byte length.

The design requires explicit:

- primary and null hypotheses, estimand, and direction;
- measurement identifiers, units, operational definitions, and measurement
  kinds;
- confirmatory and held-out-replication splits, source hashes, allocation
  rules, grouping keys, group floors, exact target groups, exact enrolled and
  analyzed row targets, and maximum disjoint missing/excluded rows;
- a fixed-sample plan with `FIXED_SAMPLE` stopping, interim outcome access
  `FORBIDDEN`, disjoint exhaustive row-accounting semantics, explicit
  exclusion and missing-data rules, fail-closed `SCIENTIFICALLY_INELIGIBLE`
  deviation effect, and an exact power-analysis artifact identity;
- threshold identifiers, operators, decimal values, units, and decision
  effects, with threshold units equal to their registered measurement units;
- matched-taxonomy, wrong-layer, and clean-null controls, with additional
  control types available only when preregistered;
- falsifiers and their consequences;
- uncertainty method, confidence level, multiplicity rule, permutations,
  seeds, and grouping unit;
- model, exact lowercase 40-character model revision, weights, tokenizer, code
  commit, clean-worktree, source, analysis, dependency, runtime, exact lowercase
  `sha256:<64-hex>` container digest, and hardware identities; and
- exact permitted and forbidden wording with a private-research claim ceiling.

The governance block is invariant and load-bearing:

```text
admission_ring       = 4
product_claim_status = NOT LICENSED
disclosure_status    = HELD
public_release       = false
product_route        = false
license_decision     = NONE
```

Any other value is rejected. No self-hash field is accepted.

## 3. Append-only amendments and outcome access

Amendments bind the base preregistration hash and the immediately preceding
amendment hash. Identifiers and timestamps must advance monotonically. Artifact
identifiers are append-only and may not collide with earlier identities. Every
public amendment load freshly replays the exact base and every predecessor
carrier. Predecessor replay is iterative, rejects cycles and skipped links, and
is capped at 128 total amendment links. Together with the 2,000,000-byte strict
JSON document ceiling, this caps retained amendment bytes at 256,000,000 and
bounds replay work; the amendment chain is a governance log, not an execution
event stream.

Only three pre-outcome amendment classes exist:

1. `ADMINISTRATIVE_CLARIFICATION` adds a non-operative note.
2. `EXECUTION_IDENTITY_ADDITION` adds exact artifact identities without
   replacing a frozen identity.
3. `EXECUTION_WINDOW` records a prospective execution window.

There is no amendment field for hypotheses, units, splits, thresholds,
controls, falsifiers, uncertainty, wording, or governance. Unknown fields are
rejected. An amendment declaring prior outcome access is rejected. The
process-local chain seals permanently when `record_outcome_access` records an
exact receipt identity and the pre-outcome chain digest; no later amendment can
be appended or injected without invalidating the seal. An `EXECUTION_WINDOW`
is unique and packet execution must occur inside it. Outcome access records the
declared execution-completion timestamp, cannot precede it, and the packet must
carry that exact sealed completion timestamp; therefore no in-protocol interim
outcome access is permitted. The event itself is a canonical exact-byte carrier
with SHA-256 and byte length, and is freshly replayed against the current
pre-outcome chain before any public read; field-only bypass mutation cannot be
rehashed into a matching packet. Public chain-state getters replay integrity
before returning state.

This is a deterministic sequence guard, not a durable authority. A later Gate 5
integration must place the chain and outcome-access event under an independently
authenticated append-only or WORM control. Reconstructing a fresh in-memory
chain is not evidence that no one previously accessed outcomes.

## 4. Evidence Packet v2

An Evidence Packet binds the exact claim, preregistration, protected design,
sealed amendment chain, raw outcomes, execution manifest, reported metrics,
controls, falsifiers, split results, uncertainty report, result summary, and
all available audit/review artifacts.

Packet artifact identifiers must be unique and disjoint from preregistration
artifact identifiers. Distinct identifiers may not reuse one SHA-256/byte-length
identity to simulate independent artifacts. When audit, replication, or claim
review records are present, the executor, auditor, replication team, and claim
reviewer identities must be pairwise distinct after Unicode NFKC normalization,
case folding, and trimming. A reported numerical-audit match cannot coexist
with discrepancies, and a mismatch must identify at least one discrepancy.
Packet creation must follow both execution completion and recorded outcome
access. Execution must start after the last preregistration amendment and fall
inside a registered execution window when one exists. Packet carrier fields are
freshly reconstructed from exact raw bytes before verification.

Every packet reports per split: groups, enrolled rows, analyzed rows, missing
rows, and excluded rows. Missing and excluded categories are disjoint and the
loader requires exact arithmetic:

```text
enrolled_rows = analyzed_rows + missing_rows + excluded_rows
```

Incoherent arithmetic is structurally rejected. Coherent underpowered runs,
target-count deviations, and missing/excluded maxima violations remain loadable
negative evidence; the computed preregistered-criteria axis fails and scientific
eligibility is `INELIGIBLE` rather than erasing the run.

The packet deliberately carries observations and artifact identities, not
caller-selected authoritative status fields. `verify_evidence_packet` computes
separate axes:

| Axis | Current isolated-kernel meanings |
|---|---|
| Structural completeness | `COMPLETE` only when every preregistration, chain, and packet artifact reference matches snapshotted bytes; otherwise `INCOMPLETE`. |
| Authenticated execution | `UNAVAILABLE` or `PRESENT_UNAUTHENTICATED`; this kernel has no trust root and no `AUTHENTICATED` path. |
| Preregistered criteria | `REPORTED_CRITERIA_MET` or `REPORTED_CRITERIA_NOT_MET`, computed from exact decimal thresholds, controls, falsifiers, and split floors. This assesses reported values, not their truth. |
| Scientific eligibility | `INELIGIBLE` when reported frozen criteria fail; otherwise `NOT_ESTABLISHED` until authenticated execution, independent audit, replication, claim review, and external scientific review exist. Underpowered and failed runs remain loadable negative evidence rather than being erased. |
| Independent numerical audit | `UNAVAILABLE`, `REPORTED_MATCH_UNAUTHENTICATED`, or `REPORTED_MISMATCH`. |
| Replication | `UNAVAILABLE` or a reported `AGREES`/`MIXED`/`DISAGREES` state marked unauthenticated. |
| Claim-language review | `UNAVAILABLE` or a reported `APPROVED`/`REJECTED` state marked unauthenticated. Approved wording must byte-for-text match a preregistered allowed string. |
| Product, license, disclosure | Always `RING 4 / NOT LICENSED / HELD / NONE`; public and product routes are always false. |

The packet's SHA-256 is an integrity identity only. It is never a signature,
reviewer identity, authorization, license, disclosure approval, WORM receipt,
scientific conclusion, or product verdict.

Authentication, audit, replication, claim-review, and external-review blockers
are reported independently of whether the frozen numerical criteria pass or
fail; a negative result cannot hide missing provenance or review.

## 5. Evidence Packet v1 boundary

Evidence Packet v1 lacks mandatory v2 facts, including a prospective per-claim
preregistration, protected-design identity, amendment/outcome-access history,
registered splits and thresholds, separated execution authentication,
independent numerical audit, replication, claim-language review, and fixed
governance state.

`reject_automatic_v1_upgrade` and `load_evidence_packet` therefore reject all
four repository-known labels (`evidence_packet.v1`,
`cas_harness_evidence_packet_v1`, `cas_harness_evidence_packet.v1`, and
`cas_harness_stage9_40e_evidence_packet.v1`) with
`AmbiguousV1UpgradeError`. A v1 packet may be cited as a separately hashed
historical source artifact in a newly authored v2 record, but missing facts may
not be inferred or backfilled as if they were prospective.

## 6. Historical design lessons retained

The control model preserves the lessons of the historical v3/v4
preregistrations:

- a successor design never edits a frozen predecessor;
- counts or outcomes already observed must be disclosed;
- prompt, group, layer, surface, taxonomy, and null controls are distinct;
- group-aware splits and uncertainty cannot be reconstructed after unblinding;
- a failed honesty control invalidates or downgrades the instrument rather than
  being absorbed into a favorable result; and
- revised thresholds belong to a new preregistration, never an amendment to the
  result-bearing design.

## 7. Verification and remaining boundaries

Authoritative manifest build and Gate 5 verifier commands, from the repository
root:

```powershell
python -I -B scripts\build_project_coherence_gate5_manifest.py
python -I -B scripts\verify_project_coherence_gate5.py
```

The manifest build is appropriate only after an intended admitted-surface
change. A local focused regression may be run separately with
`python -E -P -B -X dev -m pytest -q -p no:cacheprovider
tests\cas_harness_v2`; it bypasses the same-process receipt control and is not
the authoritative Gate 5 verifier or a locked, attested execution environment.

The suite covers missing and extra fields, duplicate JSON keys, raw-input
mutation, frozen payload mutation, wrong claim and artifact hashes, forged
governance/status fields, threshold/control/falsifier/split failures,
non-monotone or broken amendment chains, amendments after outcome access, and
v1 upgrade ambiguity. Independent adversarial cases additionally cover forged
dataclass carriers, post-seal injection, predecessor cycles, skipped links,
the exact 128-link chain bound, execution-window evasion, fixed-sample plan
deletions and forged rules, invalid target/max values, exact power-analysis
identity, row-accounting contradictions, preserved sample deviations, interim
outcome access, exact completion binding, bypass-mutated outcome-event replay,
retained-byte registry mutation, audit contradictions, normalized cross-role
aliases, and all four repository-known v1 labels.

The last committed `b96c2c12` Harness-v2 collection has an authoritative
same-process PASS receipt. It observed collected, started, and finished sequences of 306 node
IDs, 918 ordinary setup/call/teardown reports, and 151 passing subtests, with
zero warnings, collection or internal errors, or deselections, an empty
isolated pycache, and pytest exit status 0. Its exact Python-ordinal
executed-node digest is
`49BD9090B3CF8990A213BF91CB95E154792444221CC0015F1BCA7D2E77C5D293`.
This authoritative local regression is not hermetic or independently attested
and establishes no model, detector, steering, product, licensing, or disclosure
result.

Focused green slices are diagnostic preregistration at 25 tests plus 41
subtests, digest
`0D3A5514DD15CB6F5334C5D54DF1CBF1344B488C99A18E70DB4E10CE2C90308D`;
post-terminal outcome at 29 tests, digest
`777093FE2A924455178007A326E927A18252C591A329AEF1F336E8D539E679F1`;
diagnostic Study at 46 tests, digest
`83752F3D1507673E399FEDC93D346688A5BA2F802385598E7057822A6C09C0BB`;
and portable historical negative-state verification at 2 tests, digest
`FFC9ED8632A175E576526C84B2E989FDDD39DE443D842DFCDABC3AC12C248570`.
The former 204-test/110-subtest receipt is historical pre-expansion evidence.
All of these are repository-local controls, not live execution, independent
reproduction, scientific evidence, or product authority.

The current packaged kernel has 22 byte-mirrored files, 469 unique exports, and
1,420,002 bytes.
Its packaging-provenance SHA-256 is
`1561D0707AEB12ED720A1F70670494006B186628434CB6390A4DEEFBA5040D07`;
13 focused mirror tests pass. Canonical/mirror `__init__.py` SHA-256 is
`7D3A90FAFBD68C81888DD36A17CE7E075C48243C231E84A8BFDF8093C939037C`,
and the packaging allowlist source SHA-256 is
`CF21F42B81AD3E6CD50A211FB4FC6D01B035F6177921392B0F4811FCFFD641D0`.

The narrower Stage B joined-executor and runner-preparation suites pass 34/34
and 17/17 with same-process executed-node digests
`C2B5EF68B2491A19BD09345DED44704CA37A57AB21E07E09FFA928E25ABA4570`
and
`40FBF9298CB6DF939C5502D5B8C1E2ADBFA79011167E14E25252E663C114B8E6`.
They are source-level, engineering-only receipts with zero actual model
invocations. The frozen design authorized no separate pre-amendment model
canary. After those receipts passed, the additive runtime image was built
without a model invocation and exactly one amended local Qwen Stage B run
consumed its one-run authority. Run
`gate5-stageb-qwen-20260808T225631Z-3d71101d69ab` created Packet
`epv2-stageb-qwen-joined-001`, SHA-256
`FCF7674B14A34E3C33252B09B7A20E5E55FB6BC3751AC0F2B1C0EFB109578EAC`.
The kernel assesses that Packet as structural completeness `COMPLETE`, criteria
`REPORTED_CRITERIA_NOT_MET`, and scientific eligibility `INELIGIBLE`. Its three
mandatory controls are `INVALID / NOT PERFORMED`, and authentication,
independent audit, replication, claim-language review, and external review do
not advance. This concrete negative Packet demonstrates preservation of a
complete engineering record without promoting prompt-injection detection,
steering efficacy, scientific validity, product validation, license, or
disclosure authority.

The companion current 414-test worker and 78-test API/launcher/fleet/state
suites are `LOCAL_UNATTESTED_HOST_REGRESSION` observations. One pytest process
binds each
suite's duplicate-free collected/started/finished node IDs and exact
setup/call/teardown outcomes. The child starts with `-I -S -B`, imports only
locally locked pytest/plugin code before prepending exact repository roots, and
uses a fresh bytecode-cache prefix. The local runner lock binds three
interpreter files, 508 exact files owned by seven runner distributions, and
three disabled `.pth` files. Pytest and explicit plugin origins must match the
per-file lock before import; the lock is hashed and parsed from one stable byte
buffer. The surviving-module endpoint inventory maps cache paths to source and
does not prove exact executed bytecode or capture transient/unloaded/dynamic
imports, unresolved/deleted origins, native-loader dependencies, or child
processes. The standard library, distribution files absent from upstream
`RECORD`, complete test/native/descendant closure, kernel/filesystem trust, and
independent attestation remain outside the lock.

The time-indexed v0.2 worker/container checkpoint separately retains its
historical 364/364 issuance receipt; it is not rewritten against the current
414-test worker bytes.

The time-indexed v0.2 container receipt records BuildKit SPDX/SLSA and Docker
Scout facts as `SELF_REPORTED_LOCAL_OBSERVATION_ONLY`; at issuance, its raw
payloads were not retained. A later additive receipt now retains ten exact OCI,
BuildKit, SPDX, SLSA, and current Scout 1.21 payloads. The current direct scan is
`COMPLETED_WITH_FINDINGS`: six records are vendor-confirmed vulnerable or
fix-deferred and one `dpkg` record remains a scanner/vendor conflict. The SARIF
does not embed the candidate invocation, scanner database/process transcripts
are absent, and linked Ubuntu vendor pages were not snapshotted. No independent
trust root or complete tool-execution replay exists. At that candidate
checkpoint, one CPU-only non-scientific preflight had loaded the exact Pythia
artifacts and run the offline canary. The pre-Stage-B Pythia GPU canary and
joined-v0.2 diagnostics later completed a six-arm mechanics canary and one joined
controller-worker model invocation on non-admitted, single-host, non-WORM
routes. Those two diagnostics created no Evidence Packet and established neither
prompt-injection detection nor steering efficacy. The later Qwen Stage B Packet
is described above and does not change that scientific boundary. Experimental
execution remains `NOT_STARTED` and
`G5-ENGINEERING-003` remains `OPEN_SECURITY`. The normative Packet-v2 schema and
admission rules in this specification are unchanged by those diagnostics.

The broad active LF rules in `.gitattributes` are followed by later `-text`
exceptions for `api/services/cas_harness_pythia160m_*.py`,
`api/services/cas_harness_research_intervention_worker.py`,
`tests/test_cas_harness_pythia160m_*.py`, and
`tests/test_cas_harness_research_intervention_worker.py`. Those specific
exceptions preserve the already-LF historical worker source blobs as original
Git bytes while Gate 5's direct-or-transitive hash closure continues to bind
them.

## Additive fixed-sample Study-v1 structural candidate

`cas_harness_v2.study_plan.v1` and
`cas_harness_v2.study_outcome_access.v1` are additive, process-local research
schemas for a fixed multi-prompt study. They do not replace or weaken the v1
preregistration chain, worker authorization, worker terminal receipt, or
Packet-v2 schemas.

The bounded source candidate is implemented in
`src/cas_harness_v2/study_protocol.py` and adversarially exercised by
`tests/cas_harness_v2/test_study_protocol.py`. Those files are an isolated
structural seam, not a live runner or authority.

The candidate binds one exact parent plan, content-addressed ordered case
packages, request bytes, case/group/variant identities, pre-outcome
preregistration-chain bytes including amendments, exact per-case counters, and
one terminal receipt per fixed case. It supports two distinct study phases:

- `DIAGNOSTIC_CALIBRATION` requires one diagnostic package with exactly 160
  groups and the exact three Stage C variants per group; it cannot masquerade
  as confirmatory or replication evidence.
- `CONFIRMATORY_EVALUATION` requires ordered confirmatory and internally
  held-out packages bound to the preregistered split artifacts, with disjoint
  exact inventories. The internal held-out role does not establish independent
  replication.

The first definite child failure terminalizes the process-local study with no
retry. Successful registration requires nonnegative, per-case exact counters
whose digests travel through authorization and receipt, and outcome access is
strictly after the chronologically latest terminal. These are structural
controls only. The implementation has no durable cross-process one-use state,
trusted time, WORM authority, provider attestation, model-consumption proof,
Packet creation, scientific conclusion, license, product permission, or
disclosure authority.

`cas_harness_v2.preregistration.v1` still requires confirmatory plus held-out
roles and cannot honestly represent C-Cal. The additive
`cas_harness_v2.diagnostic_preregistration.v1` family now closes that structural
typing gap without widening v1 or providing a conversion path. It admits only
`DIAGNOSTIC_CALIBRATION / DIAGNOSTIC_ONLY`, forbids Packet v2, evaluation and
claim promotion, binds prospective amendments and exactly one declared
execution window, exact-replays a raw aggregate outcome index, and seals its
process-local chain at outcome access. Its source SHA-256 is
`BB8876C31AEAFA6F195F1F6F35F517943BC986D62F0606ECBF2D06B35E837CC2`.
Its test source SHA-256 is
`B2A095B3009A12746BF6FFB8B0AAC6442BD22D1B89D8124115352D9C6439F57C`.

The companion `cas_harness_v2.diagnostic_study_plan.v1` source SHA-256 is
`20EFE11D953D6F6831BA3CF404292328B3A955DD3CA0DE250D18D66204D517C8`;
its test source SHA-256 is
`9DA80335E4C6A554A890C98DF296635DADCF2EDFD63BC3ED65890A8960770696`.
It freezes exactly 160 groups and 480 ordered cases, a 488-reference plan
dependency closure, and a 489-reference closure for each per-case diagnostic
Study request. The diagnostic Study request and Stage C capture request retain
different schemas, media types, bytes, and identities: the former references
the latter, and media coercion is forbidden.

These additions remain `STRUCTURE_ONLY / NON_AUTHORITY`. The newer frozen
diagnostic tranche now supplies typed authorization/terminal-v2 carriers, a
same-host one-attempt lifecycle, exact 480-row phase coordination, worker-local
archive admission, locked fitting, and one create-once freeze-or-reject
disposition. The structural activation/worker gate now supplies fail-closed
one-use runtime mechanics, but no positive authenticated runtime execution,
trusted time, WORM/external anchoring, out-of-band execution/read prevention, or
real admitted HTTP/container activation exists. No activated real Stage C
preregistration or authorization, real-Qwen model run, provider execution call,
outcome,
or Packet exists. Stage C remains
`DESIGN_ONLY / UNAUTHORIZED / NOT_STARTED`; Gate 5 remains `OPEN / KEEP_OPEN`;
claims remain `NOT LICENSED / HELD / NOT FROZEN`.

## Additive Stage C full-vector capture structural candidate

The repaired isolated worker seam in
`live-trace-worker/app/runtime/stagec_capture.py` consumes canonical exact-byte
`cas_harness.stagec.capture_request.v1` and non-authorizing
`cas_harness.stagec.authorization_projection.v1` artifacts and emits a
canonical exact-byte `cas_harness.stagec.capture_index.v1` artifact. It obtains
the exact `model_loader.LoadedModel` singleton and postchecks that carrier after
the call. Strict replay validates the index and semantically decodes the input
IDs, attention mask, layer-0 vector, and layer-18 vector from the four bound raw
array artifacts. A process-local result seal detects later in-process mutation,
and local and global forward-hook registries must be restored exactly.

The seam reports only call counts it directly scopes: one direct capture model
call and zero direct generation API calls. Broader model-forward, generation,
intervention, and startup-canary totals remain `NOT_ATTESTED`. Its artifact
location and durability fields remain `IN_MEMORY / NOT_DURABLY_RETAINED`.
Focused regression evidence is 119/119, with node-ID digest
`E81D7234171B311720A356A36A0B6CEE06B9C564E7FF91386CAFDEA21B503144`,
source SHA-256
`4EA4C57FD412BA811993895AE37E82BEFC13B7AA220C63CAF871CB49D88500F1`
and test SHA-256
`B0DC77EEE955DE8424B11AD02CF5AD5D67C0D4F5BE5DC57A6E285A9B8AC60D30`.
The focused local-archive receipt is 32/32 with node-ID digest
`1306211016B398F44EB57FC855B87BAB2A8AFB75C32B4A4516C53FA77570395F`.
The last committed `b96c2c12` authoritative locked full-worker same-process
receipt is **PASS 576/576**
with 1,728 ordinary setup/call/teardown reports, zero subtests, warnings,
errors, or deselections, and exact Python-ordinal node-ID digest
`F454C598E8E38AF1B6C813BA124EB943E155EB3B927FACB28F4B47C758804C9F`.
The worker tree was `__pycache__`-empty after this replay.
Independent neutral QA found no P0/P1 within the declared `STRUCTURE_ONLY`
scope; that finding is not independent external replication.

The separate worker-local archive source and test SHA-256 values are
`52E444142F5C3D8FC7F0AFC983DE060EFCACCC8975C61F97B48D5BDA52226055`
and
`B78434646D50A2B8BF96449B5AF53EE9EC80079F346420ED1A6E6C53D8AEB743`.
It create-only retains the request, authorization projection, capture index, and
four raw arrays, then publishes a reread-verified manifest. It is host-local,
nonrelocatable, same-absolute-path/file-identity bound, and covers only
manifest-listed members. Read-only permission bits, file `fsync`, and immediate
reread do not establish WORM retention, trusted time, a closed-world directory,
capture provenance, or a non-caller-selected external anchor. It retains a
separate local copy; it does not rewrite the capture-time
`IN_MEMORY / NOT_DURABLY_RETAINED` statements.

The worker-output/post-terminal source and test SHA-256 values are
`D28908786C38DCAD63B39B51A82B51FAEF888CCA9DA9552CC00BE37785777D3A`
and
`9564623A3001440AAA0E2CA51667CED9AF23127051BF57776CBD5ED289130624`.
They exact-replay the acyclic `capture archive -> worker output -> terminal
receipt -> outcome index` association for completed rows. That legacy carrier
alone does not attest execution order or retry count, coordinate failed rows, or
strictly admit the worker archive loader's exact object. The additive local
lifecycle, phase coordinator, and worker admission factory below close those
bounded structural shapes without changing this carrier into authority.

## Additive diagnostic execution, coordination, fit, and disposition candidates

The exact source/test pairs and scoped focused receipts are:

| Component | Source / test SHA-256 | Receipt |
|---|---|---|
| execution-v2 contract, child binding, authorization, and terminal union | `7C16F098046E533176A1FC37B1F3D303C028B9750CD4132DECE1768858E3623F` / `C4A592645136E2FAE4D215E85E0427EB52C7CCEE6DB6E800EF8D372C5FBC5199` | 47/47 PASS |
| per-attempt lifecycle | `F4FA2A4290F093A6305E7D428294D33ACBEECF8231A8E9A4B14A705170F5A8A6` / `C8467C7C46FA5B08A11BB8012EAD96E3A628F823734415A4E32A86588BA4978D` (37,040 bytes) | 55/55 PASS in current exact-byte joint focused receipt |
| phase coordinator | `B21B857A5D94EA48CB8B78890D58039E9D8D876CBC14491F6FDE94FB6FA7AFF7` / `EDFDA3AE7096B7E2B9401939A7DC89B136D6EA33965B322BC72C803FD55C066C` (50,393 bytes) | 8/8 PASS in current exact-byte joint focused receipt |
| exact locked calibration fit | `4E0A196F3DEF71A29C3EB1425FC777727377154BF010580570ACB2115F6B21DF` / `1418C49D72FD9893ACCFDF264F9D5D9BFB9B85D0699BA8EF6729444A26102021` | 10/10 exact locked PASS, 356.75s |
| one calibration disposition | `161EF93030FD42632D03B0ABD5CBBA3ECA084F7198B7E889C96D6FD10A6C9196` / `CDB3218AA9CA8A3796062764D45A946408C9915BFD0BB134C0A981BA3C66BF95` | 11/11 final-byte nodes PASS across two bounded split runs |
| worker-local archive admission | `169AEE6754EB44ECBBF9B636505B4EBD2D7D1C031D9736FBCA37A8044613D305` / `E729485E6BFE16280592D668C998A8D39F932368CDB05F9B5BA0E0161F3DAB26` | 18/18 PASS; local-only |

The execution union admits exactly `COMPLETED`, `FAILED`, `INDETERMINATE`,
`REJECTED`, and `EXPIRED`. The local lifecycle and phase store permit one
attempt per exact subject, preserve all five terminal branches, reject a 481st
or late issuance, close any rejected batch without replacement, and permit one
aggregate access only after exact clean 480-row reconciliation. The worker
factory freshly reloads and semantically replays all seven archive members; its
case ordinal remains authorization-declared and requires canonical controller
replay.

The fit carrier accepts only the exact aggregate-access dataset and independently
derives the layer-18 and layer-0 models under `numpy==2.5.1`,
`scikit-learn==1.9.0`, and `scipy==1.18.0`. It fixes `StandardScaler` and
class-balanced L2 `LogisticRegression` with `lbfgs`, `C=0.25`,
`max_iter=1000`, and `random_state=42`, plus the exact binary64 threshold
candidate and higher-threshold tie rule. The same-file disposition slot permits
one `CALIBRATION_FROZEN_NONREPORTING` or
`CALIBRATION_REJECTED_NONREPORTING` result. Packet creation, evaluation
authority, reporting, claim/product/public promotion, and license grant are
forbidden.

The current exact-byte lifecycle-plus-phase focused receipt is 63/63 PASS in
517.14s (0:08:37), exit 0. Its elapsed time is observational only; it is not a
bound or PASS condition. The superseded joint receipt bound lifecycle test identity
`C8467C7C46FA5B08A11BB8012EAD96E3A628F823734415A4E32A86588BA4978D`
and interim phase test identity
`3C0C3C4B2605BC2FAF76DF25ABC870A2B6E70B6E84E7F8CBB30A722E80405D5D`
/ 50,378 bytes; it passed 63/63 in 585.25s. Its elapsed time is observational
only; it is not a bound or PASS condition.
Nine literal host-throughput PASS assertions were removed from the two
diagnostic tests: four lifecycle assertions and five phase-coordinator
assertions. Seven unrelated liveness ceilings and the 5,400-second runner
ceiling remain; all carry `NO PERFORMANCE AUTHORITY`. Exact functional,
480-row cardinality, same-host SQLite state-transition, receipt, and
reconciliation checks remain. The
prior lifecycle test identity
`09B20960AC9CE828D8415FB652B10F1BDB2E847298979F3C9D7ECCAC4413A64E`
with its 55/55-in-29.86s receipt, and prior phase test identity
`5A5C4BF5A34B48A2870F5412419F005D0D20F4B60C0B61FCB51B742895824BC5`
with its 50.70s, 80.32s, and 238.10s split receipts, are historical evidence
only. The disposition split timings were 210.72s for 8 passed/3 deselected and 870.18s for 3
passed/8 deselected. This is complete final-byte focused coverage across two
runs. The preserved historical 565-node Harness receipt separately records the
six exact runtime-lock nodes as setup skips and mismatch evidence rather than
PASS, so it is not an 11/11 positive exact-lock receipt. The
306-Harness/576-worker receipts remain historical checkpoints at `b96c2c12`;
the historical 565/719 receipts are recorded above. The positive post-access
`NO_ELIGIBLE_THRESHOLD` rejection branch has not been executed.

The authoritative same-process standard Python-3.14 Harness receipt collected,
started, and finished 437 nodes. Exactly 431 had all phases pass; the six exact
named fit/disposition nodes setup-skipped because `numpy==2.3.5`,
`scipy==1.17.1`, and `scikit-learn==1.8.0` do not satisfy the frozen
2.5.1/1.18.0/1.9.0 runtime lock. Those skips are mismatch evidence, not PASS
results. The run emitted 1,305 ordinary reports and 163 passing subtests,
recorded no collection or internal errors or deselections, left the isolated
pycache empty, exited pytest 0, and bound exact node-ID digest
`85AACF5BD7909979F4EC8DB7680B279D0795D32525973BC00BE16EC0157CF5E8`.
Positive exact numerical evidence remains separate under Python 3.12: fit 10/10
and eligible disposition 3/3.

That 437-node receipt is preserved historical evidence. The later 489-node
prompt-context checkpoint is also preserved historically. Exactly 483 had all
phases pass; the same six exact fit/disposition nodes
setup-skipped as runtime-lock mismatch evidence rather than PASS. It emitted
1,461 ordinary reports and 163 passing subtests, recorded zero warnings,
collection or internal errors, or deselections, left the isolated pycache
empty, exited pytest 0, and bound exact node-ID digest
`A24A129F295810836DAE12A3345670A41E3500FB2DFCFBEC27DAC6CDC65BB225`.

The preserved historical pre-runtime locked same-process Harness receipt
collected, started, and finished 537 nodes. Exactly 531 had exact all-phase PASS;
the same
six exact fit/disposition nodes setup-skipped as runtime-lock mismatch evidence,
not PASS. It emitted 1,605 ordinary reports/outcomes and 163 passing subtests,
recorded zero warnings, errors, collection or internal errors, or deselections,
left the isolated pycache empty, recorded pytest and verifier process exits 0, and
bound exact node-ID digest
`3AA22AE520FD2604AB8E8B1EAA6ED4A955DDDEB4BEBEF95F8B750A163AA5FB19`.
The 508-node receipt is retained as a historical checkpoint at
`8CDBA8F539912573D04723F39AD819C413F8AE5B69006BDC43E653F6AF6CCAE2`.

The preserved historical pre-runtime same-process worker receipt collected,
started, finished, and passed 594/594 nodes, emitted 1,782 ordinary reports and
zero subtests,
warnings, errors, or deselections, left the isolated pycache empty, exited
pytest 0, and bound exact node-ID digest
`B822D8EFC57C45712FD960BC14E2FB271FDD72C91CF29D665EBAB7ED27AE0D9B`.
Both receipts are local `STRUCTURE_ONLY / NON_AUTHORITY` evidence only.

These seams remain non-authorizing. Artifact replay has no trusted external
anchor; capture and diagnostic-chain seals are process-local; model files are
not rehashed at capture; and rendered-prompt, activation, and logits provenance
is not independently recomputable. Hook use is serialized. There is no
authorized HTTP/diagnostic Study runner, and the tests use only fake/tiny local
tensors rather than the real pinned Qwen model. Independent adversarial review
found no P0/P1 within the declared `STRUCTURE_ONLY` scope, not outside it. No
prompt-injection detector, steering result, Evidence Packet, activated provider
adapter, or RunPod job exists; paid GPU compute by this work remains `$0.00`.

Still open outside this isolated kernel:

- a portable authorized Gate 4 external-source dependency: two registered live
  paths drifted, and the historical structural rerun now depends on local
  `tksCAS` commit `130168b3bd215e2975c8eb88776ed2be3b1c2227`, blobs
  `af187b5d85f3ebbf90a802dcfc68b81924ff57ce` and
  `fab6c93ba24ebdd13feb396a22d122def3ad3cc1`, under the exact boundary
  `RETAINED GIT BLOB / LIVE REGISTERED PATH DRIFTED / LOCAL NONPORTABLE / NO CURRENT-SOURCE EQUIVALENCE`; this provides neither current-source validation
  nor experiment authority;
- authorized HTTP/container coordinator wiring and worker-route admission;
- one real pinned-Qwen Stage C/C-Cal run plus exact capture-time model/tokenizer
  revalidation;
- positive execution of the post-access `NO_ELIGIBLE_THRESHOLD` rejection
  branch and one authoritative integrated Harness/worker replay of this tranche;
- prevention and independent discovery of out-of-band execution or outcome
  access;
- durable append-only storage and trusted outcome-access ordering;
- materialized, non-caller-selected trust roots and signature verification;
- trusted time, nonce/replay control, one-use run consumption, and protection
  against selective reporting across multiple packets;
- provider-backed live-worker execution and independent executor/auditor
  validation of the bounded protocol mapping;
- hermetic execution and environment attestation, including complete
  standard-library/test/native/descendant closure, an immutable read-only
  snapshot, privileged/metadata-preserving ABA protection, hosted/auxiliary
  loader alias hardening, and independent reproduction; the repository-local
  same-process, hardlink, reparse, descriptor, and ordinary replacement
  controls do not close `G5-ENGINEERING-002`;
- independent numerical implementation and authenticated reviewer identity;
- real person, affiliation, and organizational independence beyond normalized
  declared identity strings;
- cross-packet artifact identity and semantic/media-type equivalence when
  byte-different artifacts are relabeled or cloned;
- authorized held-out replication;
- external peer review and claim-language sign-off;
- downstream enforcement that `PacketAssessment` is evidence data and never an
  authority, authorization, or capability token;
- every C-Eval, Packet, authenticated/scientific result, product, public,
  license, and disclosure authority;
- Gate 5 control matrix, manifest, verifier, and gate decision; and
- every production, licensing, compliance, disclosure, and public-route gate.

Until those separately authorized obligations close, the six axes remain:
document `DRAFT / OPEN / NOT FROZEN`; decision `OPEN / KEEP_OPEN`; engineering
`RING 4 / BOUNDED SOFTWARE CANDIDATE TESTED`; experiment `NOT_STARTED`;
license/disclosure/canon `NOT LICENSED / HELD / NOT FROZEN`; and live/product
route `UNAVAILABLE / NOT AUTHORIZED`. No live, scientific, canon, product,
license, or disclosure authority is created.
