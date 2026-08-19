#!/usr/bin/env python
"""COMPONENT ATLAS v0 (rev 0.4) -- discover -> label -> ablate -> connect -> report.

First typed map from a model's internal parts to CAS-PCBA component labels,
judged by preregistered directional ablation predictions vs matched controls.

FRAME (owner-ratified): parts are the MODEL'S (discovered functionally), names
are OURS (CAS-PCBA types), ablation is the JUDGE. A label sticks only if its
preregistered directional ablation prediction holds vs matched controls.
Language discipline: "causally supports the labeling", never "found THE
neurons". This does NOT claim the model encodes CAS.

REV 0.4 CHANGES (all informed by rev-0.2 AND rev-0.3 OUTCOMES; see PREREG
section 10, deviations D32-D45). rev 0.2 and rev 0.3 results stand UNAMENDED:
  D32 MODEL -> EleutherAI/gpt-neox-20b. No pin is recorded anywhere for this
      checkpoint (the validated Stage-9 40E run recorded model_revision: null),
      so the script FAILS CLOSED: a confirmatory run aborts as
      ABORT_UNPINNED_REVISION unless --revision <40-hex> is supplied.
  D33 DTYPE -> bfloat16 weights (fp32 does not fit an A40: 76.74 GiB vs 44.99).
      PREREG rev 0.3 section 1 said dtype was NOT to be lowered; rev 0.4
      overrides that under resource pressure and carries the precision risk
      explicitly, with fp32 ISLANDS over every measurement path.
  D34 A pythia-2.8b bf16-vs-fp32 CALIBRATION is a declared precondition of the
      20B confirmatory run (--dtype is a first-class flag for exactly this).
  D35 AMP READOUT REPLACED. "mean projection onto u_F5" (78.7% bank-invariant
      offset at rev 0.3) -> a HELD-OUT 3-way readout PROBE on the generated
      text's activations, P(own class), bounded, chance 1/3. This is the same
      readout FAMILY as the validated 40-Element result. The projection readout
      is retained and reported, plus a contrast-normalized version.
  D36 The 40-ELEMENT fixture itself is NOT reachable from this repo. The
      substitute readout (D35) is preregistered explicitly; nothing is silently
      invented. See PREREG section 2.6.
  D37 AMP CONTROLS ORTHOGONALIZED against the target (rev 0.3 was the ONLY test
      in the battery whose controls were not) and rebuilt as two families:
      shuffled-label refits of the SAME estimator + PC-subspace directions.
  D38 EVERY control ensemble is now DOSE-MATCHED on removed activation mass
      (mean |h.u|), and the target/control magnitude ratio is ALWAYS reported.
  D39 CONTROLS ARE DAMAGE-GUARDED: per-control coherence / repetition /
      behavioural-change are recorded, and controls failing the same guards the
      target must clear are EXCLUDED from the gating ensemble.
  D40 BATTERY SIZED TO FINISH: DR-F2 dropped by default, --controls 20,
      --rs-samples 3. Unit arithmetic is written into the report.
  D41 PASS WINDOW preregistered and reported; an empty or <2-SE window stamps
      VACUOUS_NO_PASS_REGION instead of an uninterpretable FAIL.
  D42 MEASURABILITY FLOOR reported: the bf16 quantum and each test's
      effect-to-quantum ratio, so a null below the instrument's resolution
      reads as UNINFORMATIVE rather than as evidence.
  D43 Peak VRAM and per-stage wall-clock are captured (the single largest gap
      in the 20B record is that neither was ever measured).
  D44 Cross-rail selectivity is now computed on the SAME bounded readout for
      both legs, so the two effect sizes are commensurable.
  D45 rev-0.3 RESULT document mis-describes its own cross-rail number;
      disclosed, per the D18/D30 precedent.

REV 0.3 CHANGES (all informed by rev 0.2 OUTCOMES; see PREREG section 10):
  1. RS REDESIGN. The rev-0.2 RS arm was gated on an argmax-thresholded
     observable (count hedge words in greedy text) that is structurally 0.00 on
     a base model. Rev 0.3 replaces it with a SUPPRESSION-GAP + PROBABILITY-MASS
     design on a new matched-surface licensed-vs-conflicted pair bank, with the
     licensed condition supplying an unsuppressed reference ceiling. The
     increase-sign property is preserved and strengthened (bounded restoration).
  2. POWER. Banks, control ensembles and sanity items enlarged; the exact sign
     test is replaced by Wilcoxon signed-rank with PRATT zero handling and an
     exact sign-flip permutation p; "beats every control" becomes an explicit
     control-ensemble permutation p = (1 + #{ctrl >= target}) / (C + 1).
  3. MODEL/ARCH. Default model EleutherAI/pythia-2.8b; every layer and head
     parameter is now a FRACTION OF DEPTH / FRACTION OF HEADS resolved from the
     loaded config (the fractions reproduce the rev-0.2 integers exactly at 16
     blocks x 8 heads, so this is a re-expression in invariant units).
  4. CHECK sanity threshold RE-ANCHORED from "drop >= 0.5 x baseline" to a
     control-ensemble permutation plus an absolute nats margin. This re-anchor
     WAS INFORMED BY REV 0.2 RESULTS (3.559-nat drop vs 0.175 best control,
     ~20x margin, failing only the 50%-of-baseline bar) and is declared as such.

REV 0.3 ADVERSARIAL-REVIEW FIXES (D19-D29; see PREREG section 10). None of
these are new science; they repair defects in the rev-0.3 DRAFT that would have
made the run unreadable or unpassable:
  D19 --max-new-tokens 24 -> 32 logged (it was an undeclared parameter change)
  D20 COVER_K becomes a FRACTION of the MLP intermediate width (32/8192)
  D21 L* selected on a CONTINUOUS non-saturating margin; sweep capped at
      L_STAR_MAX = 0.75 x depth; tie-break -> SHALLOWEST tied block >= L_STAR_MIN
  D22 RS controls: half SHUFFLED-LABEL REFITS of u_RS, half random directions
      in the PC subspace OF THE RS FIT RESIDUALS (was: drive-bank subspace);
      perturbation magnitudes reported for target and every control
  D23 Wilcoxon-Pratt zeros keyed on BYTE-IDENTITY of generated text, plus an
      explicit target-vs-BASELINE paired arm alongside target-vs-control-mean
  D24 count-matched random head controls with cross-layer fallback
  D25 the false slot-filler-uniqueness claim replaced by a run-time audit
  D26 M3 mass criterion on NORMALIZED (log-ratio) change, not raw mass
  D27 RS gating precondition moved to the RS FIT half (judge half descriptive)
  D28 declared-in-advance --preflight go/no-go on behavioural-change rates
  D29 COMMON RANDOM NUMBERS across all RS conditions (one shared sample seed)
  plus: --controls floor of 20 enforced (1/20 = 0.05 is not < 0.05), report
  flushed at every stage boundary, full provenance on abort, revision_verified,
  --local-files-only defaulted True, tf32 pinned off, smoke bank sha fixed.

RETAINED FROM REV 0.2 (unchanged discipline): clean hooks-removed judging pass
with a hard runtime guard; disjoint fit/judge split; activation-matched,
PC-subspace and cross-rail controls; cross-rail selectivity as a GATING
criterion; VACUOUS preconditions with escapes; MEM/CHECK outside the aggregate
and the verdict; descriptive-only aggregate with the non-independence caveat;
char-ngram surface control plus the binding interpretation rule; CAS-specificity
stays GREY; "causally supports" language discipline; fail-closed unpinned
revision handling.

Preregistration: PREREG_COMPONENT_ATLAS_V0.md (same directory, rev 0.4). This
script is the executable copy of that document; any divergence is a bug against
prereg.

Target environment: RunPod research venv, HF_HUB_CACHE=/workspace/cas-hf-cache.
Set PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True in the LAUNCH COMMAND (the
module also sets it before importing torch, as a belt to that braces).
Run, in the preregistered order:
  # 1. D34 calibration -- a BINDING precondition, on the rev-0.3 model.
  #    The report filename automatically carries the model tag, so this can
  #    never overwrite the 20B rev-0.4 artifact even with --out omitted.
  python component_atlas_v0.py --model EleutherAI/pythia-2.8b \
      --dtype bfloat16 --controls 24 --rs-samples 5 --run-dr-f2 --run-rs \
      --out calib_bf16
  # 2. 20B go/no-go preflight (reads no test statistic).
  python component_atlas_v0.py --preflight --revision <40-hex>
  # 3. Confirmatory run. DEFAULT BATTERY = F5 rail only (DR-F5 + AMP-F5 +
  #    CONN), C=24 drawn / 20 gating survivors, no RS, no DR-F2: 1,920 units,
  #    ~2.3 h projected at 20B bf16 on one A40.
  python component_atlas_v0.py --revision <40-hex>
  python component_atlas_v0.py --smoke               # tiny mechanical check
Output: atlas_v0_rev04_report.json in --out dir (default: script directory);
non-default models get a "__<model>" suffix. The rev-0.2 artifact
atlas_v0_report.json and the rev-0.3 artifact atlas_v0_rev03_report.json are
NEVER overwritten.
No internet beyond the HF cache (--local-files-only is the default).
"""

import argparse
import glob
import hashlib
import json
import math
import os
import re
import sys
import time
from contextlib import contextmanager

# Fragmentation guard (rev 0.4). Thousands of generate() calls with varying
# sequence lengths against ~5.4 GiB of headroom at 20B is a real
# fragmentation-OOM risk. This is set BEFORE torch is imported so no import
# side effect can initialize the CUDA caching allocator first (the rev-0.4
# first draft set it inside main(), which was correct today but fragile).
# PREFER setting it in the launch command; this is the belt to that braces.
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

import numpy as np  # noqa: E402
import torch  # noqa: E402

SCHEMA_VERSION = "component_atlas_v0.4"
REPORT_FILENAME = "atlas_v0_rev04_report.json"
PREFLIGHT_FILENAME = "atlas_v0_rev04_preflight.json"
DEFAULT_MODEL = "EleutherAI/gpt-neox-20b"
PINNED_REVISIONS = {
    # Stage 27N pinned revision for pythia-1b (rev 0.2 model; kept for reruns).
    "EleutherAI/pythia-1b": "f73d7dcc545c8bd326d8559c8ef84ffe92fea6b2",
    # pythia-2.8b: corroborated by stage14_pythia28b_activations_manifest_20260518.json
    # and stage14_weight_geometry_alignment_20260519.json (branch
    # experiment/cas-probe-pythia), mirrored at HEAD in
    # docs/working/gate2_closure/GATE2_ITEM1_CLAIMS_MATRIX.md.
    "EleutherAI/pythia-2.8b": "2a259cdd96a4beb1cdf467512e3904197345f6a9",
    # EleutherAI/gpt-neox-20b: DELIBERATELY ABSENT (rev 0.4, deviation D32).
    # The validated Stage-9 40E chain (probe 95.625%, ablation 66.897%, bridge
    # +1.412) recorded model_revision: NULL in every artifact -- the checkpoint
    # identity was never cryptographically fixed. The standing rule
    # (GATE2_ITEM1_CLAIMS_MATRIX) forbids filling in a plausible commit, so no
    # sha is invented here. A confirmatory rev-0.4 run therefore REQUIRES an
    # explicit --revision <40-hex> resolved from the pod's HF cache, and aborts
    # as ABORT_UNPINNED_REVISION without one.
}

FRAME = (
    "Parts are the MODEL'S (discovered functionally), names are OURS (CAS-PCBA "
    "types), ablation is the JUDGE. A label sticks only if its preregistered "
    "directional ablation prediction holds vs matched controls. This does NOT "
    "claim the model encodes CAS."
)

BOUNDARY = (
    "Bounded claim only. This run, at best, causally supports assigning "
    "CAS-PCBA type labels to specific internal parts of one pinned model under "
    "specific prompts, measures, and matched controls. It does not find 'the' "
    "neurons or 'the' circuit; it does not show the model encodes CAS; it does "
    "not establish that the measured directions carry drive semantics rather "
    "than topic/lexical content (CAS-specificity remains GREY per the "
    "matched-taxonomy lane); it does not license generation-control claims "
    "(cite Stage 27P for the eraser channel, two families only); it does not "
    "transfer to other models, layers, hook points, or prompt distributions "
    "without rerunning. Rev 0.4 is judged on a DIFFERENT model "
    "(EleutherAI/gpt-neox-20b) from rev 0.3 (pythia-2.8b) and rev 0.2 "
    "(pythia-1b); it does not amend or supersede the rev-0.2 NULL_ATLAS_V0 or "
    "the rev-0.3 GREY_ATLAS_V0_INSUFFICIENT_EVALUABLE result, both of which "
    "stand as reported. Rev 0.4 additionally runs in bfloat16 (deviation D33), "
    "so any effect whose relative size is at or below the bf16 quantum is "
    "reported as BELOW THE INSTRUMENT'S RESOLUTION and its null is "
    "UNINFORMATIVE, not evidence."
)

AGGREGATE_CAVEAT = (
    "The five core tests are NOT independent: DR-F5, AMP-F5, and CONN share "
    "the F5 judge bank and the u_F5 direction; DR-F5 and DR-F2 share method. "
    "The pass fraction is DESCRIPTIVE ONLY; no binomial p-value is licensed as "
    "a headline. Per-test evidence (each against its own matched controls) is "
    "the primary result. Better power in rev 0.3 does not change this: the "
    "tests are non-independent BY DESIGN, not by sample size."
)

REV03_PROVENANCE_NOTE = (
    "Rev 0.3 design changes were made AFTER seeing the rev-0.2 NULL result and "
    "are therefore informed by rev-0.2 outcomes. They are legitimate iteration, "
    "NOT post-hoc tuning, ONLY because (a) every change is logged with date and "
    "reason in PREREG section 10 BEFORE any rev-0.3 run, and (b) rev 0.3 is "
    "judged on a different model with re-drawn banks. The rev-0.2 result is "
    "reported unamended."
)

REV04_PROVENANCE_NOTE = (
    "Rev 0.4 is INFORMED BY REV-0.2 AND REV-0.3 OUTCOMES. The AMP readout "
    "change (D35), the control-construction rebuild (D37-D39), the dropped "
    "DR-F2 rail (D40) and the CHECK-informed reading of the battery were all "
    "chosen AFTER seeing rev 0.3's GREY_ATLAS_V0_INSUFFICIENT_EVALUABLE. That "
    "is legitimate iteration, NOT post-hoc tuning, ONLY because (a) every "
    "change is logged with date and reason in PREREG section 10 BEFORE any "
    "rev-0.4 run, and (b) rev 0.4 is judged on a DIFFERENT model "
    "(EleutherAI/gpt-neox-20b). The rev-0.2 and rev-0.3 results are reported "
    "unamended. Note explicitly that dropping the DR-F2 rail is justified "
    "PARTLY BY REV-0.3 OUTCOMES (behavioural change 0.313, targeted drop "
    "0.00132, 48x below the bf16 quantum) and is declared as such rather than "
    "presented as independent design. SECOND PASS (2026-08-19, still before "
    "any rev-0.4 run): an adversarial review of the rev-0.4 draft found that "
    "several of D32-D45 were not actually delivered by the draft as written -- "
    "the probe readout had no viability gate and simultaneously disabled the "
    "D41 pass window, the D39 damage guard and the C=20 floor were mutually "
    "defeating, the dose match was reported but gated on nothing, the "
    "measurability floor was misderived, and the battery did not fit the "
    "window once the calibration and preflight were counted. D46-D55 repair "
    "the draft; they are defect fixes against the design already logged, not "
    "new science, and they are logged BEFORE any pod time is spent."
)

MEASURABILITY_NOTE = (
    "bfloat16 carries 8 significand bits, i.e. a RAW relative quantum of 2^-8 "
    "= 3.90625e-3. That raw figure is NOT the binding floor and rev 0.4's "
    "first draft misused it (deviation D52): every judged quantity here is a "
    "mean over ~n_prompts x n_continuation_positions measurements, and "
    "independent quantization noise averages down by sqrt(n), so the EFFECTIVE "
    "quantization floor is roughly 32x smaller at n ~ 1024. The BINDING floor "
    "is the statistical standard error (0.2662 on the rev-0.3 AMP projection, "
    "~25x the quantization scale). An effect at or below the EFFECTIVE "
    "quantization floor is BELOW THE INSTRUMENT'S RESOLUTION at this dtype: "
    "its null is UNINFORMATIVE and may not be read as evidence of absence, and "
    "in rev 0.4's second pass it also blocks a PASS rather than merely "
    "labelling a null. The statistical floor is reported but is NEVER used to "
    "reclassify a genuine statistical null as UNINFORMATIVE -- the paired "
    "p-values already handle it. "
    "Continuous measurements survive bf16 WEIGHTS only because every "
    "measurement path is forced to fp32 (see provenance.precision_policy) and "
    "every comparison is PAIRED, so systematic bf16 bias cancels between "
    "baseline and condition on the same prompts. The DISCRETE risk does not "
    "cancel: greedy argmax can resolve differently at near-ties, which "
    "inflates behavioral_change_rate and destroys byte-identity tie structure. "
    "That is what the D34 pythia-2.8b bf16-vs-fp32 calibration exists to "
    "measure, and it must be read before this report's VACUOUS preconditions "
    "are taken at face value."
)

# ---------------------------------------------------------------------------
# Frozen prompt banks (executable copies of PREREG section 2).
# Matched-surface minimal-pair frames: each frame has ONE slot; the F5, F2 and
# neutral variants share every other character. Surface separability of the
# banks is therefore confined to the slot by construction and is measured and
# reported by the char-ngram control (PREREG section 6).
# rev 0.3: 24 -> 64 frames (32 FIT / 32 JUDGE per class). Frames 1-24 are the
# rev-0.2 frames verbatim; frames 25-64 are new, authored under the same
# minimal-pair discipline (unique slot verb per frame, no verb shared across
# classes).
# ---------------------------------------------------------------------------

# (prefix, f5_filler, f2_filler, neutral_filler, suffix)
PROMPT_FRAMES = [
    ("When the server crashed at midnight, the on-call engineer ",
     "took charge of", "methodically diagnosed", "stood beside",
     " the failing cluster, and then"),
    ("Facing the flooded basement, Priya ",
     "seized a pump and drained", "mapped the drainage paths beneath",
     "glanced across", " the lowest room, and then"),
    ("With the deadline moved up a week, Marcus ",
     "committed the team to", "weighed every tradeoff inside",
     "picked up a copy of", " the revised plan, and then"),
    ("After the committee stalled again, Dana ",
     "made the final call on", "reasoned step by step through",
     "set down her notes on", " the budget question, and then"),
    ("When the trail markers disappeared, the guide ",
     "forged ahead along", "studied the contours of", "paused beside",
     " the northern ridge, and then"),
    ("Hearing the alarm repeat, the technician ",
     "overrode the lockout on", "traced the wiring behind",
     "stood in front of", " the control panel, and then"),
    ("Once the funding cleared, Elena ",
     "launched the pilot across", "scrutinized the assumptions behind",
     "filed the forms for", " the district schools, and then"),
    ("As the negotiation dragged on, Omar ",
     "pushed a bold counteroffer onto", "reexamined every clause on",
     "poured more coffee at", " the table, and then"),
    ("When the recipe failed twice, Noor ",
     "rebuilt the whole method for", "isolated each variable in",
     "wiped the counter around", " the sourdough starter, and then"),
    ("With the storm approaching, the harbormaster ",
     "ordered an immediate haul-out of", "calculated the surge risk to",
     "counted the boats of", " the small fleet, and then"),
    ("After the audit flagged errors, Kofi ",
     "took ownership of", "cross-checked every entry in",
     "photocopied pages from", " the quarterly accounts, and then"),
    ("Seeing the class lose focus, the teacher ",
     "restructured the lesson around", "reflected on the pacing of",
     "tidied the desks before", " the afternoon session, and then"),
    ("When the packaging line jammed, Sofia ",
     "commandeered the backup rig for", "inspected the feed rollers of",
     "swept the floor beside", " the printing run, and then"),
    ("Given one open grant slot, the lab head ",
     "staked the submission on", "compared the merits of",
     "printed the forms for", " the imaging project, and then"),
    ("At the town meeting, Ravi ",
     "rallied the room behind", "laid out the evidence for",
     "handed out copies of", " the repaving proposal, and then"),
    ("During the dress rehearsal, the director ",
     "cut the second act of", "annotated the tempo shifts across",
     "collected the props for", " the production, and then"),
    ("After the third late shipment, Ana ",
     "switched suppliers and rerouted", "modeled the delay pattern behind",
     "stapled the receipts for", " the freight schedule, and then"),
    ("With the patient stable, the resident ",
     "initiated the transfer to", "reviewed the overnight charts from",
     "walked along the hallway toward", " the recovery ward, and then"),
    ("When the code review dragged on, Lin ",
     "merged the fix and shipped", "stepped through the logic of",
     "scrolled slowly past", " the payment module, and then"),
    ("Seeing the garden overrun, Tomas ",
     "ripped out and replanted", "catalogued the species crowding",
     "strolled slowly along", " the north border, and then"),
    ("After the survey results arrived, the aide ",
     "pushed the council to adopt", "parsed the crosstabs beneath",
     "stacked printed copies of", " the transit measure, and then"),
    ("With the engine misfiring, Yusuf ",
     "pulled over and repaired", "listened for the fault inside",
     "leaned quietly against", " the old pickup, and then"),
    ("Once the merger rumors spread, the CFO ",
     "froze all discretionary spending across", "stress-tested the projections for",
     "booked a meeting room near", " the finance group, and then"),
    ("When the choir lost its lead, Amara ",
     "stepped up and carried", "listened closely to the balance of",
     "sat in the row behind", " the soprano section, and then"),
    # ---- rev 0.3 additions (frames 25-64) ----
    ("When the ice storm knocked out power, Bea ",
     "restored heat to", "charted the outage across", "wandered through",
     " the shelter wing, and then"),
    ("As the festival crowd swelled, Idris ",
     "opened a second gate for", "estimated the density inside", "lingered near",
     " the main plaza, and then"),
    ("After the well ran dry, Selma ",
     "drilled a new line beneath", "sampled the water table under",
     "wrote a note about", " the south pasture, and then"),
    ("With the roof leaking again, Cormac ",
     "tore off and relaid", "surveyed the water stains under", "looked up at",
     " the east shingles, and then"),
    ("When the archive flooded, the curator ",
     "evacuated the crates from", "assessed the damage inside",
     "unlocked a door near", " the lower vault, and then"),
    ("As the pitch fell flat, Nadia ",
     "rewrote the closing of", "pinpointed the weak claim inside",
     "held a copy of", " the investor deck, and then"),
    ("Once the trial data arrived, Bram ",
     "halted enrollment in", "recomputed the interim stats for",
     "labeled the folders for", " the second cohort, and then"),
    ("With the herd scattering, the rancher ",
     "drove the strays back toward", "read the wind shifts above",
     "waited at the gate of", " the north fence, and then"),
    ("After the outage report landed, Vikram ",
     "reengineered the failover for", "profiled every dependency of",
     "forwarded the email about", " the billing service, and then"),
    ("When the mural was defaced, Ines ",
     "repainted the whole panel of", "identified the pigment used on",
     "photographed a corner of", " the station wall, and then"),
    ("As the contract deadline slipped, Hadley ",
     "renegotiated the terms of", "projected the penalty exposure in",
     "refiled the paperwork for", " the vendor agreement, and then"),
    ("With the reef bleaching fast, Tuiloma ",
     "seeded new coral across", "measured the temperature gradient over",
     "swam slowly above", " the outer shelf, and then"),
    ("When the kiln cracked mid-firing, Odette ",
     "salvaged the batch from", "gauged the thermal stress on",
     "piled crates beside", " the back chamber, and then"),
    ("After the census figures shifted, Grigor ",
     "redrew the service map for", "contrasted decade trends across",
     "bound the printouts for", " the eastern district, and then"),
    ("With the orchestra out of tune, Beatriz ",
     "stopped the run and retuned", "singled out the drift inside",
     "shuffled the pages of", " the string section, and then"),
    ("When the levee showed seepage, Duarte ",
     "sandbagged the breach at", "followed the seepage path beneath",
     "parked the truck near", " the river bend, and then"),
    ("As the recall notice spread, Fenna ",
     "withdrew every unit from", "audited the failure logs behind",
     "folded the flyers about", " the retail floor, and then"),
    ("Once the visa was denied, Anwar ",
     "lodged an appeal against", "reread the rules governing",
     "kept the envelope from", " the consular office, and then"),
    ("With the server bill tripling, Rina ",
     "trimmed the idle capacity in", "itemized the growth drivers of",
     "downloaded the invoice from", " the compute account, and then"),
    ("When the shelter overfilled, Bo ",
     "converted the annex beside", "examined the intake pattern at",
     "carried supplies past", " the front desk, and then"),
    ("After the harvest failed twice, Mireille ",
     "replowed the entire slope of", "tested the soil chemistry of",
     "knelt at the edge of", " the upper terrace, and then"),
    ("As the negotiation reopened, Kwabena ",
     "imposed a firm floor for", "reconstructed the history behind",
     "arranged the chairs around", " the wage clause, and then"),
    ("With the prototype failing, Sunniva ",
     "scrapped and remade", "pinned down the failing subsystem in",
     "boxed the parts of", " the second unit, and then"),
    ("When the ledger stopped balancing, Teodoro ",
     "corrected and reposted", "reconciled every transfer inside",
     "typed a summary of", " the March entries, and then"),
    ("After the pipeline stalled overnight, Wren ",
     "restarted the ingest for", "benchmarked the slowest stage of",
     "skimmed the changelog for", " the nightly job, and then"),
    ("As the wildfire line shifted, Calla ",
     "called an evacuation of", "simulated the ember spread toward",
     "gathered reports from", " the ridge houses, and then"),
    ("With the clinic understaffed, Ezra ",
     "ran triage at", "analyzed the arrival pattern at",
     "restocked the shelves at", " the walk-in desk, and then"),
    ("When the translation drifted, Yuki ",
     "retranslated every passage of", "collated the source idioms in",
     "turned the pages of", " the final chapter, and then"),
    ("After the referee split the vote, Halvard ",
     "cast the deciding ballot on", "balanced both dissents within",
     "sorted the ballots for", " the safety motion, and then"),
    ("With the bridge deck shifting, Perpetua ",
     "closed all traffic over", "computed the load tolerance of",
     "sketched the joints of", " the south span, and then"),
    ("When the recipe scaled badly, Lucien ",
     "reformulated the base for", "located the ratio error inside",
     "scooped the flour for", " the banquet order, and then"),
    ("As the data leak surfaced, Mira ",
     "rotated every key across", "diagrammed the intrusion path into",
     "archived the alerts from", " the internal portal, and then"),
    ("With the choir hall booked twice, Ottoline ",
     "moved the whole rehearsal to", "checked the booking history of",
     "posted a notice on", " the annex room, and then"),
    ("When the vaccine batch warmed, Emeka ",
     "discarded and reordered", "verified the cold-chain log for",
     "wheeled the cartons of", " the pediatric supply, and then"),
    ("After the strike vote passed, Solveig ",
     "led the walkout at", "dissected the bargaining terms of",
     "distributed leaflets at", " the loading dock, and then"),
    ("With the telescope misaligned, Idrissa ",
     "recollimated the optics of", "characterized the aberration in",
     "cleaned the housing of", " the guide scope, and then"),
    ("When the lease came due, Rosalind ",
     "signed a longer term on", "ranked every offer near",
     "toured the hallway of", " the corner unit, and then"),
    ("As the forecast worsened, Batu ",
     "canceled the crossing to", "interpreted the pressure charts over",
     "transcribed the schedule for", " the outer island, and then"),
    ("With the archive uncatalogued, Petra ",
     "indexed the entire run of", "dated the watermarks inside",
     "dusted the shelves near", " the field journals, and then"),
    ("When the sensor readings diverged, Hana ",
     "recalibrated and redeployed", "cross-referenced both streams from",
     "logged the timestamps of", " the harbor buoys, and then"),
]

# ---------------------------------------------------------------------------
# RS bank (rev 0.3, REPLACES the rev-0.2 AMBIVALENT stubs).
# Matched-surface pairs: identical frame, differing ONLY in the clause that
# licenses versus blocks agency. The stem is shared verbatim and is deliberately
# NOT grammatically pre-committed to action (the rev-0.2 AMBIVALENT stubs
# "Finally he", "Fed up, the team", "Without checking upstairs, he" cued the
# very behavior the test tries to detect the suppression of, and are retired).
# (licensing_clause, blocking_clause, shared_stem)
# ---------------------------------------------------------------------------
RS_PAIRS = [
    ("The committee approved it last week.", "The committee is stalled again.",
     "If I want this to happen, I"),
    ("Her manager signed off before leaving.", "Her manager left no instructions at all.",
     "With the decision still open, she"),
    ("The lab posted an open-access policy on the door.",
     "The lab posted a restricted-access notice on the door.",
     "Standing in the corridor, I"),
    ("The rulebook covers this case explicitly.", "The rulebook says nothing about this case.",
     "Looking at the file, the officer"),
    ("The team was told to pick its own process.",
     "The team was told to change nothing without approval.",
     "Facing the wasted hours, they"),
    ("Funding for the pilot is secured through next year.",
     "Funding for the pilot may be pulled next quarter.",
     "Weighing that, the founder"),
    ("The client asked for a same-day answer.",
     "The client's account is under legal review.",
     "With the phone still ringing, he"),
    ("The trail is marked as open to hikers.", "The trail is posted as closed to hikers.",
     "At the fork, they"),
    ("Her mentor encouraged her to lead it.", "Her mentor warned her not to overstep.",
     "After the long silence, Maria"),
    ("The budget line has room for a new hire.", "The budget line was frozen this morning.",
     "Reading the request, the director"),
    ("The landlord agreed to any repairs we need.", "The landlord disputes every repair request.",
     "Seeing the leak spread, we"),
    ("The board delegated this call to the CFO.", "The board reserved this call for itself.",
     "With the numbers in front of him, the CFO"),
    ("The permit came through yesterday.", "The permit application was rejected yesterday.",
     "Standing at the site, Amara"),
    ("The archive is cleared for public copying.", "The archive is sealed under a donor agreement.",
     "Holding the folder, the curator"),
    ("The patient consented to the transfer.", "The patient has not been reached for consent.",
     "With the bed waiting, the resident"),
    ("The vendor invited us to renegotiate freely.", "The vendor threatened to void the contract.",
     "Reading the clause again, Hadley"),
    ("The school district asked teachers to redesign the unit.",
     "The school district locked the unit for the term.",
     "Seeing the class drift, the teacher"),
    ("The safety officer cleared the line for restart.",
     "The safety officer has not signed the restart form.",
     "At the control panel, the technician"),
    ("The grant allows the funds to be moved.", "The grant forbids moving the funds.",
     "Looking at the shortfall, the lab head"),
    ("The owner said to take whatever action is needed.",
     "The owner said to wait for his return.",
     "With the herd scattering, the rancher"),
    ("The editor asked for a full rewrite.",
     "The editor forbade any change after typesetting.",
     "Reading the flat ending, Nadia"),
    ("The council voted to let staff act directly.",
     "The council requires a vote for every step.",
     "With the road still broken, the aide"),
    ("Her co-author agreed to any revision.", "Her co-author objects to every revision.",
     "Facing the referee report, she"),
    ("The union contract permits a local stoppage.",
     "The union contract bars any local stoppage.",
     "At the loading dock, Solveig"),
    ("The port authority allows an early departure.",
     "The port authority holds all departures until noon.",
     "Watching the sky darken, Batu"),
    ("The family asked her to decide for them.", "The family insists on deciding together.",
     "With the forms unsigned, she"),
    ("The insurer pre-approved emergency work.", "The insurer denies unapproved emergency work.",
     "With water rising, Cormac"),
    ("The registry accepts corrections from anyone.",
     "The registry accepts corrections only from the filer.",
     "Seeing the error, Teodoro"),
    ("The festival charter lets the marshal open gates.",
     "The festival charter reserves gate control to the city.",
     "As the crowd pressed forward, Idris"),
    ("The protocol allows dose changes at the bedside.",
     "The protocol locks the dose until review.",
     "Watching the readings shift, Ezra"),
    ("The publisher released the translation rights.",
     "The publisher retains all translation rights.",
     "Reading the awkward passage, Yuki"),
    ("The city cleared the wall for repainting.", "The city listed the wall as protected.",
     "Standing before the defaced panel, Ines"),
    ("The tenants voted to give her full authority.",
     "The tenants voted to require a meeting first.",
     "With the boiler dead, Rosalind"),
    ("The observatory schedule is open tonight.",
     "The observatory schedule is fully booked tonight.",
     "Seeing the blurred field, Idrissa"),
    ("The captain told the crew to use their judgment.",
     "The captain told the crew to hold position.",
     "With the current pushing hard, they"),
    ("The regulator invited early disclosure.", "The regulator penalizes early disclosure.",
     "Holding the incident log, Mira"),
    ("The donor allows the collection to be reorganized.",
     "The donor forbids reordering the collection.",
     "Facing the unsorted crates, Petra"),
    ("The clinic gave her standing authority to triage.",
     "The clinic requires a physician for triage.",
     "With the waiting room full, she"),
    ("The exam board permits an appeal at any time.",
     "The exam board closed appeals last Friday.",
     "Looking at the mark, Anwar"),
    ("The county authorized an immediate closure.",
     "The county requires a hearing before closure.",
     "Watching the deck shift, Perpetua"),
    ("The kitchen lets cooks rewrite the menu.",
     "The kitchen requires the chef to approve every change.",
     "Tasting the failed batch, Lucien"),
    ("The station manager approved an extra rehearsal.",
     "The station manager blocked all extra rehearsals.",
     "Hearing the tuning slip, Beatriz"),
    ("The agency lets field staff order evacuations.",
     "The agency reserves evacuations for headquarters.",
     "As the fire line moved, Calla"),
    ("The trust allows the terrace to be replanted.",
     "The trust protects the terrace from any planting.",
     "Seeing the second failure, Mireille"),
    ("The operator can restart the job without a ticket.",
     "The operator needs a ticket for any restart.",
     "Seeing the queue back up, Wren"),
    ("The commission asked members to break the deadlock.",
     "The commission bars members from breaking a tie.",
     "With the vote split, Halvard"),
    ("The depot allows units to be pulled on sight.",
     "The depot requires a written order to pull units.",
     "Seeing the recall notice, Fenna"),
    ("The warden gave her discretion over the annex.",
     "The warden requires headquarters approval for the annex.",
     "With the shelter overfull, Bo"),
]

# Legacy RS direction exemplars (rev 0.2). RETAINED in rev 0.3 for the
# SECONDARY, disclosed comparison direction only; the primary rev-0.3 u_RS is
# fit from the RS_PAIRS fit half (conflicted - licensed).
F5_HEDGED = [
    "Perhaps she might consider starting the project, though it may be wiser to wait.",
    "I could possibly take charge, but maybe we should ask everyone first.",
    "He hesitated to make the call, unsure whether it was his place.",
    "Maria wondered if taking the first step alone would be too rash.",
    "You could try picking a direction, although it might be safer to hold off.",
    "The founder considered restructuring but decided to postpone any changes.",
    "It might be best to wait for guidance rather than move first.",
    "Priya was tempted to choose her own path but feared the risk.",
    "We thought about building it ourselves but kept waiting for permission.",
    "Signing the papers today seems hasty; perhaps next month would be safer.",
    "The captain deferred to the committee despite his private doubts.",
    "The intern drafted a new plan but filed it away for later.",
]

F5_PLAIN = [
    "She decided to launch the project herself without waiting for approval.",
    "I will take charge of the situation and act now.",
    "He seized the opportunity and made the call on his own.",
    "Determined to change things, Maria took the first step alone.",
    "You can do this: pick a direction and commit to it.",
    "The founder acted decisively, restructuring the team overnight.",
    "Take initiative; nobody else will move first.",
    "Against all advice, Priya chose her own path and pressed forward.",
    "We stopped waiting for permission and built it ourselves.",
    "Own the decision: sign the papers and start today.",
    "The captain overrode the committee and set a new course.",
    "With one bold move, the intern rewrote the plan and shipped it.",
]

# Harness-sanity items (OUTSIDE the aggregate; PREREG section 5).
# rev 0.3: 12 -> 40 items (20 discovery / 20 judgment) so that MEM_DROP_MIN=0.20
# is EXACTLY attainable (4/20) instead of quantizing to an effective 0.333 at
# n=6, which is what rev 0.2 silently did.
MEM_ITEMS = [
    {"prompt": "The access code for the storage room is 7291. When the guard asked for it, the technician repeated that the access code is", "key": " 7291"},
    {"prompt": "The visiting professor's name is Okonkwo. Introducing him at the podium, the dean said the visiting professor's name is", "key": " Okonkwo"},
    {"prompt": "The shipment weighs 480 kilograms. On the manifest, the clerk wrote that the shipment weighs", "key": " 480"},
    {"prompt": "The ferry departs from Pier 9 every morning. The sign at the gate says the ferry departs from Pier", "key": " 9"},
    {"prompt": "The patient was moved to room 12B overnight. The nurse told the family the patient is in room", "key": " 12B"},
    {"prompt": "The wifi keyword for the office is bluefinch. Asked by the new hire, the manager said the keyword is", "key": " bluefinch"},
    {"prompt": "The capital of the province is Renlow. On the exam, the student wrote that the capital of the province is", "key": " Renlow"},
    {"prompt": "The serial number on the pump is K-5528. Reading it back over the phone, the engineer said the serial number is", "key": " K-5528"},
    {"prompt": "The contact person for the venue is Ms. Delgado. In the follow-up email, the planner wrote that the contact person is", "key": " Ms. Delgado"},
    {"prompt": "The meeting was moved to Thursday at noon. Reminding the team, the assistant said the meeting is now on", "key": " Thursday"},
    {"prompt": "The sample was labeled specimen 44 in the log. Checking the freezer, the lab tech confirmed the label reads specimen", "key": " 44"},
    {"prompt": "The train to Halvern leaves at 6:45 in the morning. The conductor announced that the train leaves at", "key": " 6:45"},
    {"prompt": "The backup generator is on level 3 of the annex. Pointing at the map, the foreman said the generator is on level", "key": " 3"},
    {"prompt": "The auditor's surname is Vaszary. Signing the cover page, the clerk wrote that the auditor's surname is", "key": " Vaszary"},
    {"prompt": "The greenhouse holds 260 seedlings this season. In the log, the gardener recorded that the greenhouse holds", "key": " 260"},
    {"prompt": "The permit number for the site is 8814. Reading from the folder, the inspector said the permit number is", "key": " 8814"},
    {"prompt": "The bus to Redmark leaves from bay 7. The dispatcher told the passengers the bus leaves from bay", "key": " 7"},
    {"prompt": "The password hint for the archive is seabird. Helping the intern, the archivist said the hint is", "key": " seabird"},
    {"prompt": "The village on the north shore is called Ithren. On the map key, the surveyor wrote that the village is called", "key": " Ithren"},
    {"prompt": "The pump was installed in 1987 according to the plate. Reading the plate aloud, the engineer said it was installed in", "key": " 1987"},
    {"prompt": "The caterer for the gala is Halloran. Confirming by phone, the planner said the caterer is", "key": " Halloran"},
    {"prompt": "The workshop moved to Saturday afternoon. Updating the group, the coordinator said the workshop is now on", "key": " Saturday"},
    {"prompt": "The freezer sample is filed under batch 19. Checking the index, the technician confirmed the batch is", "key": " 19"},
    {"prompt": "The night train to Coalport departs at 11:20. Over the speaker, the guard announced the train departs at", "key": " 11:20"},
    {"prompt": "The key for the side gate is kept in drawer 4. Showing the new guard, the janitor said the key is in drawer", "key": " 4"},
    {"prompt": "The consultant on the project is Dr. Feld. Introducing the team, the manager said the consultant is", "key": " Dr. Feld"},
    {"prompt": "The tank holds 1500 liters when full. Marking the sheet, the operator noted the tank holds", "key": " 1500"},
    {"prompt": "The gallery opens at 10:30 on weekdays. Answering the caller, the receptionist said the gallery opens at", "key": " 10:30"},
    {"prompt": "The reef survey site is grid F6. Radioing back, the diver reported the survey site is grid", "key": " F6"},
    {"prompt": "The apprentice's first name is Solveig. Calling roll, the supervisor said the apprentice's first name is", "key": " Solveig"},
    {"prompt": "The order was shipped on the 14th of the month. Checking the record, the clerk said it shipped on the", "key": " 14th"},
    {"prompt": "The alarm code at the depot is 6603. Reciting it back, the driver said the alarm code is", "key": " 6603"},
    {"prompt": "The lecture is held in hall B every Tuesday. Directing the students, the porter said the lecture is in hall", "key": " B"},
    {"prompt": "The vaccine lot is marked QX-7. Reading the carton, the pharmacist said the lot is marked", "key": " QX-7"},
    {"prompt": "The ferry captain is named Baptiste. Over the radio, the harbormaster said the captain is named", "key": " Baptiste"},
    {"prompt": "The building has 22 floors above ground. Guiding the visitor, the concierge said the building has", "key": " 22"},
    {"prompt": "The archive box is labeled shelf 9C. Locating it, the assistant said the box is on shelf", "key": " 9C"},
    {"prompt": "The measurement came back at 3.4 millimeters. Reporting to the lead, the tester said the measurement is", "key": " 3.4"},
    {"prompt": "The contact number ends in 5502. Repeating it slowly, the operator said the number ends in", "key": " 5502"},
    {"prompt": "The reserve is named Vellsmoor in the register. Filling the form, the ranger wrote that the reserve is named", "key": " Vellsmoor"},
]

# Word-boundary matched (regex \b); generic verbs like 'could'/'wait' removed.
# rev 0.3: the word COUNT on greedy text is retained as a DESCRIPTIVE field
# only. It is no longer a precondition or a pass criterion: measured directly,
# base models emit exactly 0 hedge words on ambivalent stubs at 24/64/128
# tokens, so an emitted-word count is structurally 0.00 regardless of threshold.
# The load-bearing rev-0.3 observable is hedge PROBABILITY MASS on the clean
# re-forward (never zero on any base model tested).
HEDGE_WORDS = [
    "perhaps", "maybe", "might", "possibly", "probably", "unsure",
    "uncertain", "hesitant", "hesitated", "hesitate", "wonder", "wondered",
    "doubt", "doubted", "cautious", "caution", "risky", "unclear",
]

# Frequency/POS-matched neutral control lexicon (rev 0.3). Paired 1:1 with
# HEDGE_WORDS by part of speech and morphology, in the same approximate corpus
# frequency band. DISCLOSURE: the matching is hand-made on POS + morphology +
# rough frequency band; it is NOT corpus-frequency-verified. Its role is to
# prevent "the hedge lexicon moved" from being satisfiable by "every lexicon
# moved" under a broad distributional shift.
CONTROL_WORDS = [
    "indeed", "later", "must", "quickly", "finally", "unable",
    "unknown", "distant", "returned", "return", "notice", "noticed",
    "note", "noted", "curious", "attention", "costly", "unusual",
]

# Act-vs-restrain next-token lexicons (rev 0.3, SECONDARY gate G3 only).
ACT_WORDS = ["decided", "acted", "started", "took", "made", "went",
             "signed", "called", "pushed", "launched", "began", "chose"]
RESTRAIN_WORDS = ["waited", "paused", "hesitated", "deferred", "held", "stopped",
                  "checked", "asked", "delayed", "refrained", "postponed",
                  "reconsidered"]

# ---------------------------------------------------------------------------
# Preregistered thresholds (PREREG sections 3, 4, 7).
# Depth/width constants are FRACTIONS resolved against the loaded config
# (rev 0.3 item 3). At n_blocks=16 they resolve to 4 / 6 / 4 and at
# n_blocks*n_heads=128 the head budget resolves to 4 -- bit-identical to the
# rev-0.2 absolute constants, so this is a re-expression in invariant units,
# not a re-tune.
# ---------------------------------------------------------------------------
# COVER_K is a FRACTION OF THE MLP INTERMEDIATE WIDTH (rev 0.3 review fix D20).
# 32 / 8192 = 0.00390625 reproduces the rev-0.2 "Top-32" EXACTLY at pythia-1b
# and gives 40 at pythia-2.8b's 10240, so the rail cut keeps its RELATIVE
# strength across scales -- the same invariant-units argument as D12, which
# COVER_K was originally (and inconsistently) exempted from.
# rev 0.3 deviation D31 (logged in PREREG Section 10 BEFORE this change and
# BEFORE the confirmatory run): raised from 32/8192 = 0.391% to 1.0% after the
# D28 preflight returned go=false with DR_F5 behavioural-change 0.50 < 0.60
# (AMP_F5 1.00, RS_F5 0.833 both cleared). D28 explicitly sanctions changing
# intervention STRENGTH on a NO-GO, and the preflight reads no test statistic,
# so this cannot be tuned toward a pass. Exactly ONE step is authorised: if the
# re-run preflight still shows DR_F5 < 0.60, the fallback is to run as-is and
# accept DR_F5/CONN VACUOUS -- NOT to widen again. The rev-0.2-equivalent
# fraction (0.391%) is retained below for provenance.
COVER_K_FRAC_REV02_EQUIVALENT = 32.0 / 8192.0
COVER_K_FRAC = 0.01
COVER_K_MIN = 8
# rev 0.4 deviation D56 (logged in PREREG Section 10 BEFORE this change and
# BEFORE the run): the LOWER bounds are widened to the full depth. The
# validated Stage-9 40E probe on gpt-neox-20b peaked at LAYER 2 OF 44 (shoulder
# to L7) -- entirely below the [16, 33] window these fractions produced, so the
# design could not select the one layer band with prior evidence. L_STAR_MIN was
# a LOWER bound and therefore never protected the downstream-depth property it
# was introduced for (that is L_STAR_MAX, which is unchanged): shallow layers
# have the MOST downstream depth, not the least.
LAYER_SWEEP_MIN_ABS = 1         # D56: sweep the full depth (was round(0.25*d))
L_STAR_MIN_ABS = 2              # D56: avoid only embedding/first block
# Retained for provenance; no longer used to derive the lower bounds.
LAYER_SWEEP_MIN_FRAC_REV03 = 0.25
L_STAR_MIN_FRAC_REV03 = 0.375
# D56 interpretation caveat: an L* selected below this fraction of depth is
# flagged surface-suspect (a layer-2 peak is more consistent with a token/
# surface feature than with deep semantics).
SHALLOW_L_STAR_CAVEAT_FRAC = 0.25
L_STAR_MAX_FRAC = 0.75          # rev 0.3 review fix D21: downstream-depth guard
DR_OFFSET_FRAC = 0.25           # DR_OFFSET = round(frac * n_blocks) (16 -> 4)
TOPK_HEADS_FRAC = 0.03          # of ALL heads (16x8=128 -> 4; 32x32=1024 -> 31)
TOPK_HEADS_MIN = 4

SIGN_ALPHA = 0.05               # alpha for the paired Wilcoxon-Pratt statistic
CONTROL_PERM_ALPHA = 0.05       # alpha for the control-ensemble permutation p
DR_PRESENCE_COLLAPSE = 0.5      # ablated rate < 0.5 x baseline rate
AMP_PRESENCE_RETAIN = 0.5       # ablated rate >= 0.5 x baseline rate
BASELINE_PRESENCE_MIN = 0.6     # precondition for DR/AMP, else VACUOUS
SELECTIVITY_MAX_RATIO = 0.5     # cross-rail effect size <= 0.5 x target
BEHAVIORAL_CHANGE_MIN = 0.60    # rev 0.3: tie-rate precondition (see below)
MEM_BASELINE_MIN = 0.6          # rev 0.3 re-anchor (was 0.5, landed exactly on)
MEM_DROP_MIN = 0.20             # absolute copy-accuracy drop (exact at n=20)
CHECK_GATE_MIN_NATS = 0.5       # sanity precondition (unreachable-threshold trap)
CHECK_DROP_MIN_NATS = 1.0       # rev 0.3 re-anchor: absolute margin ...
CHECK_DROP_FRAC_LEGACY = 0.5    # ... replacing this rev-0.2 fraction (reported)
COHERENCE_MIN = 0.3             # distinct-WORD ratio floor (fluency guard)
REPETITION_MIN = 0.5            # rev 0.3: distinct-4GRAM ratio floor
PC_SUBSPACE_K = 10              # variance-carrying control-direction subspace
CONN_MIN_EFFECT = 0.0           # CONN targeted effect must be > 0 and beat all
N_INNER_SPLIT_SEEDS = 5         # rev 0.3: average the sweep over 5 inner splits
N_FLOOR_TRIALS = 10             # rev 0.3: was 3; candidate set roughly doubled
RS_N_SAMPLES = 3                # rev 0.4 (D40): 5 -> 3 to fit the 20B budget
RS_TEMPERATURE = 0.7
RS_RHO_MIN = 0.0                # bounded restoration: rho in (RS_RHO_MIN, MAX]
RS_RHO_MAX = 1.5
RS_CTRL_SHUFFLED_FRAC = 0.5     # rev 0.3 review fix D22: half of the RS control
                                # ensemble is a SHUFFLED-LABEL REFIT of u_RS on
                                # the RS fit half (the only control family that
                                # matches the estimation-noise geometry of a
                                # 24-vs-24 diff-of-means); the other half are
                                # random unit directions inside the PC subspace
                                # OF THE RS FIT RESIDUALS (rev-0.3 draft drew
                                # them from the DRIVE-bank PC subspace, a
                                # different prompt distribution, which made the
                                # controls systematically STRONGER perturbations
                                # than the target).

# Smallest control count at which the control-ensemble permutation p can be
# STRICTLY below alpha=0.05: floor is 1/(C+1), and 1/20 = 0.05 is not < 0.05.
# This is the GATING floor -- the number of controls that must SURVIVE the D39
# damage guard, not the number drawn.
CONTROLS_MIN_STRICT = 20

# REV 0.4 second pass, deviation D46. Rev 0.4's first draft drew exactly
# CONTROLS_MIN_STRICT controls AND required CONTROLS_MIN_STRICT survivors of the
# D39 damage guard, so the guard had ZERO slack: one degraded draw stamped
# VACUOUS_CONTROL_ENSEMBLE_DEGRADED. Rev 0.3 observed exactly such a draw (the
# AMP control whose projection ROSE by 13.2128) at C=24, i.e. roughly a 1-in-24
# per-draw rate, which gives ~57% chance that at least one of 20 fails --
# INDEPENDENTLY for each test. The most likely mechanical outcome of the whole
# run would then have been GREY for a reason unrelated to the hypothesis.
# Controls are therefore DRAWN with surplus and GATED on survivors.
CONTROLS_DRAW_DEFAULT = 24      # draw 24, require 20 survivors
CONTROL_GUARD_SURPLUS_MIN = 2   # drawn - gating floor must be at least this

# ---------------------------------------------------------------------------
# REV 0.4 constants (PREREG section 10, deviations D33, D35, D37-D42).
# ---------------------------------------------------------------------------
# D57 (logged in PREREG Section 10 BEFORE this change and BEFORE the run):
# D33 (bf16) and D34 (the bf16-vs-fp32 calibration precondition) are WITHDRAWN.
# D33 existed solely because fp32 at 20.554567680B params is 76.6 GiB against
# the A40's 44.99 GiB. The run moved to an H200 with 139.8 GiB MEASURED, where
# fp32 fits with ~63 GiB spare, so the constraint that forced the precision
# compromise is gone and the compromise goes with it. Relative quantum improves
# 2^-8 -> 2^-24 (~65,000x). No gate, threshold, control, bank or statistic
# changes -- only the numeric substrate.
DEFAULT_DTYPE = "float32"       # D57 (was "bfloat16" under D33, now withdrawn)
DTYPE_CHOICES = ("float32", "bfloat16", "float16")
# bfloat16 has 8 significand bits -> relative spacing 2^-8. Reported alongside
# every effect so a null below the instrument's resolution is readable as such.
DTYPE_RELATIVE_QUANTUM = {
    "float32": 2.0 ** -24,
    "bfloat16": 2.0 ** -8,
    "float16": 2.0 ** -11,
}

# D35: the primary AMP readout is a HELD-OUT 3-way probe on the generated
# text's activations (F5 / F2 / neutral), read as P(own class). Bounded in
# [0, 1] with a defined chance floor of 1/3 -- the same readout FAMILY as the
# validated 40-Element result (held-out probe accuracy, chance 1/40), which is
# what gives it full dynamic range instead of rev 0.3's 78.7% dead offset.
READOUT_PROBE_CLASSES = ("f5", "f2", "neutral")
READOUT_PROBE_CHANCE = 1.0 / len(READOUT_PROBE_CLASSES)
AMP_PRIMARY_READOUT = "probe_p"     # "probe_p" | "proj"
DR_PRIMARY_READOUT = "proj"         # DR's signature is presence collapse

# D37: AMP control ensemble composition, mirroring the RS design.
AMP_CTRL_SHUFFLED_FRAC = 0.5

# D38: dose matching. "Dose" is REMOVED ACTIVATION MASS, mean |h.u| over the
# judge prompts on the clean model -- NOT vector norm, which is vacuous here
# because every direction is already a unit vector.
DOSE_MATCH_TOL = 0.25           # accept a control within +/-25% of target dose
DOSE_MATCH_TRIES = 64           # numpy-only; costs no GPU generation

# D47 (rev 0.4 second pass): dose matching is now GATING, not merely reported.
# The rev-0.4 first draft accept/rejected into the band, silently returned the
# CLOSEST draw on failure with matched=False, and let nothing depend on it. The
# direction of risk is INVERTED relative to rev 0.3: AMP controls are now
# orthogonalized against u_F5 and drawn from MEAN-CENTRED bases, while the AMP
# target's dose is ~78.7% grand-mean offset -- so if the band is unreachable,
# every control is a systematically WEAKER perturbation than the target and a
# PASS is uninterpretable. That is the exact mirror of the defect rev 0.4 was
# created to fix, and PREREG's reading rule previously covered only the FAIL
# direction.
DOSE_MATCHED_MIN_FRAC = 0.90    # >= 90% of the GATING controls inside the band
DOSE_RATIO_LO = 0.80            # target/control-mean magnitude ratio band
DOSE_RATIO_HI = 1.25

# D41: preregistered pass window on the primary readout.
PASS_WINDOW_MIN_SE = 2.0        # narrower than this -> VACUOUS_NO_PASS_REGION
# D48 (rev 0.4 second pass): an SE-only width rule is INERT in exactly the
# failure mode D41 exists to catch. If the readout saturates (which PREREG 2.6
# itself predicts for a 3-class probe fit on 96 rows in 6144 dims), the baseline
# sd goes to ~0, se goes to 0, and `width/se` is never computed -- so
# VACUOUS_NO_PASS_REGION could never fire. The window must therefore ALSO clear
# an ABSOLUTE floor expressed as a fraction of the readout's own usable range.
PASS_WINDOW_MIN_ABS_FRAC = 0.05

# D49 (rev 0.4 second pass): held-out readout-probe VIABILITY gate. Separation
# on 96 fit rows in 6144 dimensions is perfect by construction, so
# `fit_accuracy_in_sample_reported_only` is uninformative and P(own class) can
# saturate near 0/1 with sd ~ 0. In that regime the probe readout is a squashed
# monotone function of a near-u_F5 projection whose squash REDUCES sensitivity,
# the size of any drop is uninterpretable (PREREG 2.6 concedes this), and the
# D41 window is degenerate. The probe must therefore prove it has usable range
# on the UNABLATED judge banks before it is allowed to be the headline readout.
PROBE_VIABILITY_MIN_SD = 0.02          # per-class sd of P(own class)
PROBE_VIABILITY_MIN_ACC_OVER_CHANCE = 0.10   # held-out accuracy minus chance

# D50 (rev 0.4 second pass): ONE bounded, declared DR-engagement step at 20B,
# usable only after a logged 20B preflight NO-GO. D31's single authorised step
# was scoped to rev 0.3 / pythia-2.8b and is NOT carried over implicitly.
COVER_K_FRAC_STEP2 = 0.02

# D51 (rev 0.4 second pass): the D21 tie-break was inert. `abs(v - best) <=
# 1e-12` on a continuous 5-seed-averaged margin means exact ties essentially
# never occur, so "shallowest tied block at or above L_STAR_MIN" never ran and
# ABORT_GUARD_LAYER was the only guard against a shallow argmax.
MARGIN_TIE_REL_TOL = 1e-4

_HOOKS_ACTIVE = False           # clean-pass runtime guard (see clean_pass)


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def sha_of(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode("utf-8")).hexdigest()


def _json_default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    return str(o)


def unit(v):
    v = np.asarray(v, dtype=np.float64)
    n = float(np.linalg.norm(v))
    if n == 0.0:
        raise ValueError("zero vector cannot be normalized")
    return v / n


def sign_test_p(diffs):
    """Exact one-sided sign test, H1: median(diffs) > 0.

    RETAINED IN REV 0.3 AS A REPORTED LEGACY STATISTIC ONLY (so the rev-0.2 vs
    rev-0.3 comparison stays auditable). It is NOT a pass criterion any more:
    it DELETES zero differences, which under the clean-pass rule are genuine
    evidence AGAINST the hypothesis. In rev 0.2 that silently reduced DR_F5 and
    CONN from n=12 to n_effective=6.
    """
    pos = sum(1 for d in diffs if d > 0)
    n = sum(1 for d in diffs if d != 0)
    if n == 0:
        return 1.0
    return float(sum(math.comb(n, k) for k in range(pos, n + 1)) / (2.0 ** n))


def wilcoxon_pratt(diffs, zero_mask=None):
    """One-sided Wilcoxon signed-rank (H1: median > 0), PRATT zero handling.

    `zero_mask` (rev 0.3 review fix D23) is a boolean per-pair mask of entries
    that are ties BY CONSTRUCTION -- the generated text was BYTE-IDENTICAL, so
    under the clean-pass rule the effect is EXACTLY zero. It must be supplied
    wherever it is knowable, because a float difference computed from a mean of
    C identical float64s is off by 1 ulp roughly 22% of the time, which gives a
    genuine zero an arbitrary +-1e-16 sign and a nonzero rank. Without the mask
    the Pratt zero handling is largely INERT and the reported tie_rate is not
    the quantity D6/D9 describe.

    Pratt: zeros are KEPT in the ranking of |d| (they inflate the ranks of the
    non-zero entries, which is the conservative and correct direction here --
    under the clean-pass rule a byte-identical continuation is real evidence of
    no effect and must count, not vanish).

    The p-value is the EXACT sign-flip permutation p over the non-zero entries,
    computed by dynamic programming over doubled (tie-averaged) ranks; no
    normal approximation, no Monte Carlo, fully deterministic. Falls back to a
    seeded Monte Carlo only if the DP state space would be unreasonably large.
    """
    d = np.asarray(list(diffs), dtype=np.float64)
    n = int(d.size)
    zm_n = 0
    if zero_mask is not None:
        zm = np.asarray(list(zero_mask), dtype=bool)
        if zm.size == n and zm.any():
            d = d.copy()
            d[zm] = 0.0
            zm_n = int(zm.sum())
    stats = {"n_total": n, "n_tied": 0, "tie_rate": 0.0,
             "n_byte_identical_forced_zero": zm_n,
             "W_signed_rank_sum": 0.0, "method": "wilcoxon_pratt_exact_permutation"}
    if n == 0:
        stats["p"] = 1.0
        return 1.0, stats
    a = np.abs(d)
    order = np.argsort(a, kind="mergesort")
    ranks = np.empty(n, dtype=np.float64)
    sa = a[order]
    i = 0
    while i < n:
        j = i
        while (j + 1) < n and sa[j + 1] == sa[i]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    signs = np.sign(d)
    nz = signs != 0
    n_tied = int(n - int(nz.sum()))
    stats["n_tied"] = n_tied
    stats["tie_rate"] = float(n_tied / n)
    if not nz.any():
        stats["p"] = 1.0
        return 1.0, stats
    obs = float(np.sum(signs[nz] * ranks[nz]))
    stats["W_signed_rank_sum"] = obs
    r2 = np.rint(ranks[nz] * 2.0).astype(np.int64)
    obs2 = int(round(obs * 2.0))
    total2 = int(r2.sum())
    if total2 <= 200000:
        counts = {0: 1}
        for r in r2.tolist():
            nxt = {}
            for s, c in counts.items():
                nxt[s + r] = nxt.get(s + r, 0) + c
                nxt[s - r] = nxt.get(s - r, 0) + c
            counts = nxt
        denom = 2 ** int(r2.size)
        ge = sum(c for s, c in counts.items() if s >= obs2)
        p = float(ge) / float(denom)
    else:  # pragma: no cover - not reachable at prereg bank sizes
        rng = np.random.default_rng(20260818)
        draws = 200000
        flips = rng.integers(0, 2, size=(draws, int(r2.size))) * 2 - 1
        sims = flips @ r2
        p = float((1 + int(np.sum(sims >= obs2))) / (draws + 1))
        stats["method"] = "wilcoxon_pratt_monte_carlo_permutation"
    stats["p"] = p
    return p, stats


def control_ensemble_p(target_stat, control_stats):
    """Exact permutation p for the 'beats every matched control' criterion.

    p = (1 + #{c : stat(ctrl_c) >= stat(target)}) / (C + 1).

    Rev-0.2 used the bare strict inequality with C=6, whose smallest attainable
    p is 1/7 = 0.1429 -- it could never support an alpha=0.05 claim. C >= 19
    makes 0.05 attainable; C = 24 (the rev-0.3 default) makes it strictly
    attainable at 0.04.
    """
    c = len(control_stats)
    if c == 0:
        return 1.0
    ge = sum(1 for s in control_stats if float(s) >= float(target_stat))
    return float((1 + ge) / (c + 1))


def hedge_count(text):
    """Word-boundary hedge counting. DESCRIPTIVE ONLY in rev 0.3."""
    low = text.lower()
    total = 0
    for w in HEDGE_WORDS:
        total += len(re.findall(r"\b" + re.escape(w) + r"\b", low))
    return total


def distinct_ratio(text):
    words = text.lower().split()
    if not words:
        return 0.0
    return len(set(words)) / len(words)


def distinct_ngram_ratio(text, n=4):
    """Rev 0.3 repetition guard.

    The rev-0.2 coherence guard was a distinct-WORD ratio; it passed text that
    repeated one sentence four times (0.768 for a condition whose sample was
    'I have to get it done.' x4). Degenerate repetition -- not incoherence --
    is what flips clean-pass projections into different attractors, so the
    guard has to see n-grams.
    """
    words = text.lower().split()
    if len(words) < n:
        return distinct_ratio(text)
    grams = [tuple(words[i:i + n]) for i in range(len(words) - n + 1)]
    return len(set(grams)) / len(grams)


def rate_above(vals, tau):
    if len(vals) == 0:
        return 0.0
    return float(np.mean([1.0 if v > tau else 0.0 for v in vals]))


def effect_size(base_vals, cond_vals):
    """Standardized drop: (mean(base) - mean(cond)) / std(base)."""
    b = np.asarray(base_vals, dtype=np.float64)
    c = np.asarray(cond_vals, dtype=np.float64)
    return float((b.mean() - c.mean()) / (b.std() + 1e-8))


def find_sublist(haystack, needle):
    n = len(needle)
    if n == 0:
        return -1
    for i in range(len(haystack) - n + 1):
        if haystack[i:i + n] == needle:
            return i
    return -1


def behavioral_change_rate(base_texts, cond_texts):
    """Fraction of judge prompts whose continuation differs from baseline.

    Rev 0.3 first-class quantity. Under the clean-pass rule a byte-identical
    continuation scores EXACTLY zero effect; if most prompts are unchanged the
    intervention never engaged the behavioural channel, and the label was never
    actually tested (VACUOUS_NO_BEHAVIORAL_CHANGE, not FAIL).
    """
    mask = identity_mask(base_texts, cond_texts)
    n = len(mask)
    if n == 0:
        return 0.0
    return float((n - int(sum(mask))) / n)


def identity_mask(a_texts, b_texts):
    """Per-prompt BYTE-IDENTITY mask between two conditions' continuations.

    Rev 0.3 review fix D23: this is the ground truth for "the intervention did
    nothing here", and it is what the Wilcoxon-Pratt zero handling must key on
    (a float difference of 1 ulp is not a tie; byte-identical text is).
    """
    out = []
    for a, b in zip(a_texts, b_texts):
        ta = tuple(a) if isinstance(a, (list, tuple)) else (a,)
        tb = tuple(b) if isinstance(b, (list, tuple)) else (b,)
        out.append(bool(ta == tb))
    return out


def all_identity_mask(a_texts, cond_list):
    """True where a_texts equals the continuation of EVERY condition in list."""
    if not cond_list:
        return [False] * len(a_texts)
    masks = [identity_mask(a_texts, c["texts"]) for c in cond_list]
    return [all(m[i] for m in masks) for i in range(len(a_texts))]


def build_banks(smoke, seed):
    """Minimal-pair banks + RS pair bank, with deterministic fit/judge splits.

    Discovery data and judgment data are DISJOINT at the frame level for all
    three drive classes simultaneously, and separately for the RS pair bank.
    """
    frames = PROMPT_FRAMES[:8] if smoke else PROMPT_FRAMES
    n = len(frames)
    rng = np.random.default_rng(seed + 123)
    perm = rng.permutation(n)
    fit_idx = sorted(int(i) for i in perm[: n // 2])
    judge_idx = sorted(int(i) for i in perm[n // 2:])

    def render(idx_list, slot):
        out = []
        for i in idx_list:
            pre, f5, f2, neu, suf = frames[i]
            filler = {"f5": f5, "f2": f2, "neu": neu}[slot]
            out.append(pre + filler + suf)
        return out

    pairs = RS_PAIRS[:6] if smoke else RS_PAIRS
    m = len(pairs)
    rng_rs = np.random.default_rng(seed + 321)
    perm_rs = rng_rs.permutation(m)
    rs_fit_idx = sorted(int(i) for i in perm_rs[: m // 2])
    rs_judge_idx = sorted(int(i) for i in perm_rs[m // 2:])

    def render_rs(idx_list, which):
        out = []
        for i in idx_list:
            lic, con, stem = pairs[i]
            out.append((lic if which == "lic" else con) + " " + stem)
        return out

    hedged = F5_HEDGED[:6] if smoke else F5_HEDGED
    plain = F5_PLAIN[:6] if smoke else F5_PLAIN
    return {
        "fit_idx": fit_idx, "judge_idx": judge_idx,
        "f5_fit": render(fit_idx, "f5"), "f5_judge": render(judge_idx, "f5"),
        "f2_fit": render(fit_idx, "f2"), "f2_judge": render(judge_idx, "f2"),
        "neu_fit": render(fit_idx, "neu"), "neu_judge": render(judge_idx, "neu"),
        "rs_fit_idx": rs_fit_idx, "rs_judge_idx": rs_judge_idx,
        "rs_lic_fit": render_rs(rs_fit_idx, "lic"),
        "rs_con_fit": render_rs(rs_fit_idx, "con"),
        "rs_lic_judge": render_rs(rs_judge_idx, "lic"),
        "rs_con_judge": render_rs(rs_judge_idx, "con"),
        "f5_hedged": hedged, "f5_plain": plain,
    }


# ---------------------------------------------------------------------------
# Model loading / hooks
# ---------------------------------------------------------------------------

_TORCH_DTYPES = {
    "float32": torch.float32,
    "bfloat16": torch.bfloat16,
    "float16": torch.float16,
}


def pin_precision_backends():
    """Pin every reduced-precision shortcut OFF (rev 0.4, deviation D33).

    `allow_bf16_reduced_precision_reduction` DEFAULTS TO TRUE in PyTorch and
    permits a bf16 matmul to ACCUMULATE in bf16 rather than fp32. With bf16
    weights that is the difference between a 6144-dim dot product whose error
    averages down as eps*||h||/sqrt(12n) (negligible) and one that does not
    (fatal for a 0.366-sized drop on a 10.7 baseline). tf32 stays pinned off
    for the same reason it was in rev 0.3: the fp32 islands below depend on it.
    """
    applied = {}
    for path, val in (
            ("cuda.matmul.allow_tf32", False),
            ("cudnn.allow_tf32", False),
            ("cuda.matmul.allow_bf16_reduced_precision_reduction", False),
            ("cuda.matmul.allow_fp16_reduced_precision_reduction", False)):
        parts = path.split(".")
        obj = torch.backends
        ok = True
        for a in parts[:-1]:
            obj = getattr(obj, a, None)
            if obj is None:
                ok = False
                break
        if not ok or not hasattr(obj, parts[-1]):
            applied[path] = "unavailable"
            continue
        try:
            setattr(obj, parts[-1], val)
            applied[path] = bool(getattr(obj, parts[-1]) == val)
        except Exception:  # pragma: no cover - CPU-only builds
            applied[path] = "unavailable"
    return applied


def promote_lm_head_fp32(model):
    """fp32 ISLAND over the final norm + unembedding (rev 0.4, deviation D33).

    Highest-value island in the budget: greedy argmax, the D1 hedge probability
    MASS and the D13 CHECK gate score in nats ALL read the logits, and bf16
    logit error near |logit| = 15 is ~0.059 absolute -- a ~6% MULTIPLICATIVE
    error on each softmax probability. Cost at 20B is +0.58 GiB against ~6.6
    GiB of headroom.

    These are dtype CASTS, not interventions. They are installed permanently,
    for generation AND for the clean pass alike, so they cannot introduce an
    asymmetry between the two; they deliberately do NOT touch _HOOKS_ACTIVE.
    """
    info = {"final_norm": None, "lm_head": None, "status": "UNAVAILABLE"}
    norm = None
    for path in (("gpt_neox", "final_layer_norm"), ("model", "norm"),
                 ("transformer", "ln_f")):
        obj, ok = model, True
        for a in path:
            if hasattr(obj, a):
                obj = getattr(obj, a)
            else:
                ok = False
                break
        if ok:
            norm, info["final_norm"] = obj, ".".join(path)
            break
    head = None
    for name in ("embed_out", "lm_head"):
        h = getattr(model, name, None)
        if h is not None:
            head, info["lm_head"] = h, name
            break
    if norm is None or head is None:
        return info

    def _cast_pre(module, args):
        if args and isinstance(args[0], torch.Tensor) \
                and args[0].dtype != torch.float32:
            return (args[0].to(torch.float32),) + tuple(args[1:])
        return None

    try:
        norm.float()
        head.float()
        norm.register_forward_pre_hook(_cast_pre)
        head.register_forward_pre_hook(_cast_pre)
    except Exception as e:  # pragma: no cover
        info["error"] = str(e)
        return info
    info["status"] = "APPLIED"
    return info


def load_model_and_tokenizer(model_id, revision, device, local_files_only,
                             dtype_name=DEFAULT_DTYPE, use_device_map=True):
    """Load with the rev-0.4 flags (deviation D33).

    device_map={"": idx} makes accelerate stream shard-by-shard STRAIGHT TO
    GPU: host-RAM peak drops from ~38.4 GiB (which the rev-0.3
    low_cpu_mem_usage + model.to(device) path needs to stage at 20B, and which
    OOMs the container before VRAM is ever touched) to one shard. `.to(device)`
    must then NOT be called -- it warns or raises on an accelerate-dispatched
    model. {"": idx} is used rather than "auto" on purpose: "auto" may decide
    to CPU-offload tail layers on its own, and offloading even one layer costs
    ~0.47 GB of PCIe traffic per token for memory that is not needed.
    """
    from transformers import AutoModelForCausalLM, AutoTokenizer

    torch_dtype = _TORCH_DTYPES[dtype_name]
    kwargs = dict(
        attn_implementation="eager",   # MANDATORY, not stylistic: the head
                                       # pre-hook slices the attention
                                       # out-projection input in concat head
                                       # layout, which SDPA/flash do not expose
        use_safetensors=True,
        low_cpu_mem_usage=True,
        local_files_only=local_files_only,
    )
    if revision:
        kwargs["revision"] = revision
    dispatched = False
    dev_str = str(device)
    if use_device_map and dev_str.startswith("cuda"):
        idx = 0
        if ":" in dev_str:
            try:
                idx = int(dev_str.split(":", 1)[1])
            except ValueError:
                idx = 0
        kwargs["device_map"] = {"": idx}
        dispatched = True
    try:
        model = AutoModelForCausalLM.from_pretrained(
            model_id, dtype=torch_dtype, **kwargs)
    except TypeError:
        # older transformers: dtype kw not accepted yet
        model = AutoModelForCausalLM.from_pretrained(
            model_id, torch_dtype=torch_dtype, **kwargs)
    tok = AutoTokenizer.from_pretrained(
        model_id, revision=revision, local_files_only=local_files_only)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    if not dispatched:
        model.to(device)
    model.eval()
    return model, tok, dispatched


_SHA40 = re.compile(r"^[0-9a-f]{40}$")


def resolved_commit_sha(model):
    """Best-effort resolution of the commit actually loaded.

    Repo precedent: build_verified_canary_bundle.py hard-aborts when the
    preflight-resolved commit is not the exact pinned revision. If the runtime
    cannot report a commit we record null and continue with a warning rather
    than asserting the pin (GATE2_ITEM1_CLAIMS_MATRIX standing rule: an
    unrecoverable revision reads 'unavailable' and is never filled in).
    """
    for holder in (getattr(model, "config", None), model):
        v = getattr(holder, "_commit_hash", None)
        if isinstance(v, str) and v:
            return v
    return None


def locate_layers(model):
    """Cross-architecture transformer-layer discovery (probe-shard pattern)."""
    for attrs in (("gpt_neox", "layers"), ("model", "layers"), ("transformer", "h")):
        obj = model
        ok = True
        for a in attrs:
            if hasattr(obj, a):
                obj = getattr(obj, a)
            else:
                ok = False
                break
        if ok:
            return list(obj)
    raise RuntimeError("could not locate transformer layers on this model")


def mlp_out_module(layer):
    for name in ("dense_4h_to_h", "down_proj", "c_proj", "fc_out"):
        mod = getattr(getattr(layer, "mlp", layer), name, None)
        if mod is not None:
            return mod
    raise RuntimeError("could not locate the MLP output projection on this layer")


def attn_out_module(layer):
    for path in (("attention", "dense"), ("self_attn", "o_proj"),
                 ("attn", "c_proj"), ("attention", "out_proj")):
        obj = layer
        ok = True
        for a in path:
            if hasattr(obj, a):
                obj = getattr(obj, a)
            else:
                ok = False
                break
        if ok:
            return obj
    raise RuntimeError("could not locate the attention output projection")


class ForwardEdit:
    """Tuple-vs-Tensor safe forward hook applying fn to the block output."""

    def __init__(self, fn):
        self.fn = fn

    def __call__(self, module, inputs, output):
        is_t = isinstance(output, tuple)
        h = output[0] if is_t else output
        h = self.fn(h)
        return ((h,) + tuple(output[1:])) if is_t else h


def make_projection_removal(u_np):
    """h <- h - (h.u)u at ALL positions (learned-direction removal).

    REV 0.4 (deviation D33): the removal is computed in fp32 and cast back.
    Rev 0.3 did `uu = u.to(dtype=h.dtype)`, so under bf16 weights the ENTIRE
    removal -- dot product, scale, subtraction -- would run in bf16 and a small
    projection component would be rounded away BEFORE it was ever subtracted.
    This is the INTERVENTION itself; if it is lossy the experiment measures
    nothing. Cost is one fp32 copy of [1, seq, hidden] per hook call.
    """
    u32 = torch.tensor(np.asarray(u_np, dtype=np.float32))

    def fn(h):
        uu = u32.to(device=h.device, dtype=torch.float32)
        h32 = h.to(torch.float32)
        proj = torch.matmul(h32, uu).unsqueeze(-1) * uu
        return (h32 - proj).to(h.dtype)

    return fn


def make_cover_zero_prehook(cover_idx):
    """Zero MLP-intermediate coordinates (input to the MLP out-proj), all pos."""
    idx = torch.tensor(sorted(int(i) for i in cover_idx), dtype=torch.long)

    def pre(module, args):
        x = args[0].clone()
        x[..., idx.to(x.device)] = 0.0
        return (x,) + tuple(args[1:])

    return pre


def make_head_zero_prehook(head_ids, head_dim):
    """Zero per-head slices at the attention out-proj input (concat layout)."""
    hs = sorted(set(int(h) for h in head_ids))

    def pre(module, args):
        x = args[0].clone()
        for h in hs:
            x[..., h * head_dim:(h + 1) * head_dim] = 0.0
        return (x,) + tuple(args[1:])

    return pre


@contextmanager
def install_hooks(specs):
    """specs: list of (module, fn, kind) with kind in {'forward', 'pre'}."""
    global _HOOKS_ACTIVE
    handles = []
    try:
        _HOOKS_ACTIVE = True
        for module, fn, kind in specs:
            if kind == "pre":
                handles.append(module.register_forward_pre_hook(fn))
            else:
                handles.append(module.register_forward_hook(fn))
        yield
    finally:
        for h in handles:
            h.remove()
        _HOOKS_ACTIVE = False


def head_hook_specs(layers, head_set, head_dim):
    by_layer = {}
    for (L, h) in head_set:
        by_layer.setdefault(int(L), []).append(int(h))
    return [(attn_out_module(layers[L]), make_head_zero_prehook(hs, head_dim), "pre")
            for L, hs in sorted(by_layer.items())]


# ---------------------------------------------------------------------------
# Lexicon -> token ids (rev 0.3 probability-mass measures)
# ---------------------------------------------------------------------------

def lexicon_token_ids(tok, words):
    """Single-token ids for a frozen lexicon, over cased/space-prefixed forms.

    Only variants that encode to EXACTLY one token are used, so the mass is a
    well-defined single-step next-token probability.
    """
    ids, resolved = [], {}
    for w in words:
        got = []
        for v in (" " + w, w, " " + w.capitalize(), w.capitalize()):
            enc = tok(v, add_special_tokens=False)["input_ids"]
            if len(enc) == 1:
                got.append(int(enc[0]))
        got = sorted(set(got))
        resolved[w] = got
        ids.extend(got)
    return sorted(set(ids)), resolved


# ---------------------------------------------------------------------------
# Capture / probes / directions
# ---------------------------------------------------------------------------

def residual_feats(model, tok, prompts, device):
    """[N, n_blocks+1, hidden]; last-token residual per hidden_states index.

    hidden_states[0] is the embedding layer; block L output = index L+1.
    """
    rows = []
    for p in prompts:
        enc = tok(p, return_tensors="pt").to(device)
        with torch.no_grad():
            out = model(**enc, output_hidden_states=True)
        rows.append(torch.stack(
            [h[0, -1] for h in out.hidden_states]).float().cpu().numpy())
    return np.stack(rows)


def fit_probe_acc(XA, XB, seed, shuffle_labels=False, rng=None):
    """Returns (accuracy, margin) on the inner test split.

    `margin` = mean predicted probability of the TRUE class -- a CONTINUOUS,
    NON-SATURATING statistic. Rev 0.3 review fix D21: accuracy quantizes to
    1/n_test and saturates at exactly 1.000 over a wide mid-to-late plateau on
    strict minimal pairs, which turns the preregistered L* "discovery" step into
    a constant decided entirely by the tie-break rule. L* is selected on the
    margin; accuracy is still computed and reported.
    """
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import train_test_split
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    X = np.concatenate([XA, XB], axis=0)
    y = np.array([1] * len(XA) + [0] * len(XB))
    if shuffle_labels:
        y = rng.permutation(y)
    Xtr, Xte, ytr, yte = train_test_split(
        X, y, test_size=0.4, random_state=seed, stratify=y)
    pipe = make_pipeline(
        StandardScaler(),
        LogisticRegression(C=0.1, max_iter=1000, class_weight="balanced"))
    pipe.fit(Xtr, ytr)
    acc = float(pipe.score(Xte, yte))
    proba = pipe.predict_proba(Xte)
    classes = list(pipe.classes_)
    idx = [classes.index(v) for v in yte]
    margin = float(np.mean([proba[i, j] for i, j in enumerate(idx)]))
    return acc, margin


def diff_dir(featsA, featsB, hs_idx):
    return unit(featsA[:, hs_idx].mean(0) - featsB[:, hs_idx].mean(0))


def mlp_intermediate_feats(model, tok, prompts, mlp_out_proj, device):
    """[N, intermediate]; last-token input to the MLP out-proj (post-activation)."""
    acts, buf = [], []

    def pre(module, args):
        buf.append(args[0][0, -1].detach().float().cpu())

    handle = mlp_out_proj.register_forward_pre_hook(pre)
    try:
        for p in prompts:
            enc = tok(p, return_tensors="pt").to(device)
            with torch.no_grad():
                model(**enc)
            acts.append(buf[-1].numpy())
            buf.clear()
    finally:
        handle.remove()
    return np.stack(acts)


def score_dr_cover(acts_present, acts_neutral, w_out, u_dir, k):
    """Stage-27F-style activation x output-alignment contrast score; top-k."""
    align = w_out.T @ np.asarray(u_dir, dtype=np.float64)   # [intermediate]
    score = (acts_present * align).mean(0) - (acts_neutral * align).mean(0)
    cover = np.argsort(-score)[:k]
    return [int(i) for i in cover], score


def decile_matched_cover(mean_abs_act, target_coords, rng):
    """Activation-magnitude-matched random cover (strength-matched control)."""
    n = int(mean_abs_act.shape[0])
    order = np.argsort(mean_abs_act)
    ranks = np.empty(n, dtype=np.int64)
    ranks[order] = np.arange(n)
    bins = (ranks * 10) // n
    target_set = set(int(c) for c in target_coords)
    pool_by_bin = {}
    for b in range(10):
        pool_by_bin[b] = [i for i in np.nonzero(bins == b)[0].tolist()
                          if i not in target_set]
    used = set()
    cover = []
    for c in target_coords:
        b = int(bins[int(c)])
        pool = [i for i in pool_by_bin[b] if i not in used]
        if not pool:
            pool = [i for i in range(n) if i not in target_set and i not in used]
        pick = int(pool[int(rng.integers(len(pool)))])
        used.add(pick)
        cover.append(pick)
    return sorted(cover)


def pc_basis(X, k):
    """Top-k right singular vectors of the row-centered matrix X [rows, hid]."""
    Xc = X - X.mean(axis=0, keepdims=True)
    _, _, Vt = np.linalg.svd(Xc, full_matrices=False)
    return Vt[: min(k, Vt.shape[0])]


def pc_random_dir(V, rng, ortho_to=None):
    """Variance-carrying random unit direction inside the top-PC subspace."""
    g = rng.standard_normal(V.shape[0])
    v = V.T @ g
    if ortho_to is not None:
        u = unit(ortho_to)
        v = v - float(v @ u) * u
    return unit(v)


def shuffled_label_dir(rows_a, rows_b, rng, ortho_to=None):
    """Diff-of-means direction refit on PERMUTED group labels (rev 0.3, D22).

    This is the control family the adversarial review demanded and the rev-0.3
    draft lacked: it is produced by the IDENTICAL estimator as u_RS (a
    n_a-vs-n_b difference of residual means, orthogonalized against u_F5, then
    normalized) applied to labels that carry no licensed/conflicted information.
    It therefore has the same estimation-noise geometry and the same
    perturbation magnitude scale as the target direction, which random
    directions inside a dominant-variance PC subspace demonstrably do not.
    """
    X = np.concatenate([np.asarray(rows_a, dtype=np.float64),
                        np.asarray(rows_b, dtype=np.float64)], axis=0)
    n_a = int(np.asarray(rows_a).shape[0])
    perm = rng.permutation(X.shape[0])
    v = X[perm[:n_a]].mean(0) - X[perm[n_a:]].mean(0)
    if ortho_to is not None:
        u = unit(ortho_to)
        v = v - float(v @ u) * u
    return unit(v)


def fit_readout_probe(rows_by_class, seed):
    """HELD-OUT 3-way readout probe on generated-text activations (D35).

    THE PROBE CONTRACT IS PINNED to the one that produced the validated 40E
    numbers (95.625% held-out at layer 2 of 44 on GPT-NeoX-20B):
    StandardScaler + LogisticRegression(C=0.1, max_iter=1000,
    class_weight='balanced', solver='lbfgs'), multinomial by lbfgs default.
    `n_jobs` is deliberately NOT passed (it is a no-op on sklearn >= 1.8 and
    emits a FutureWarning). lbfgs may hit max_iter without converging; the 40E
    run's ConvergenceWarning is on the record and the result stood.

    Fit on the FIT half's BASELINE generations only, evaluated on JUDGE-half
    conditions -- discovery and judgment stay disjoint at the frame level,
    exactly as the projection readout already required.
    """
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    classes = [c for c in READOUT_PROBE_CLASSES if len(rows_by_class.get(c, [])) > 0]
    if len(classes) < 2:
        return None, {"status": "UNAVAILABLE_TOO_FEW_CLASSES"}
    X = np.concatenate([np.asarray(rows_by_class[c], dtype=np.float64)
                        for c in classes], axis=0)
    y = np.concatenate([[i] * len(rows_by_class[c]) for i, c in enumerate(classes)])
    pipe = make_pipeline(
        StandardScaler(),
        LogisticRegression(C=0.1, max_iter=1000, class_weight="balanced",
                           solver="lbfgs"))
    pipe.fit(X, y)
    meta = {
        "status": "FITTED",
        "classes": classes,
        "chance_level": float(1.0 / len(classes)),
        "n_fit_rows_per_class": {c: int(len(rows_by_class[c])) for c in classes},
        "fit_accuracy_in_sample_reported_only": float(pipe.score(X, y)),
        "contract": ("StandardScaler + LogisticRegression(C=0.1, "
                     "max_iter=1000, class_weight='balanced', solver='lbfgs') "
                     "-- pinned to the validated 40-Element probe contract"),
        "fit_data": ("FIT-half baseline generations only, clean re-forward, "
                     "block L*, mean over continuation positions"),
    }
    return pipe, meta


def attach_probe_readout(measure, pipe, classes, class_name):
    """Write P(class_name) per judge prompt into a measure dict (D35)."""
    if pipe is None or class_name not in classes:
        measure["probe_p"] = None
        return measure
    V = np.asarray(measure.get("vec"), dtype=np.float64)
    if V.size == 0:
        measure["probe_p"] = None
        return measure
    idx = list(classes).index(class_name)
    P = pipe.predict_proba(V)
    measure["probe_p"] = [float(x) for x in P[:, idx]]
    return measure


def readout_vals(measure, key):
    """Per-prompt readout array: 'probe_p' (D35) or a projection direction."""
    if key == "probe_p":
        v = measure.get("probe_p")
        if v is None:
            raise RuntimeError("probe readout requested but not attached")
        return np.asarray(v, dtype=np.float64)
    return np.asarray(measure["proj"][key], dtype=np.float64)


def dose_matched_draw(draw_fn, rng, mag_fn, target_mag,
                      tol=DOSE_MATCH_TOL, tries=DOSE_MATCH_TRIES):
    """Accept/reject a control direction into the TARGET's dose band (D38).

    "Dose" is REMOVED ACTIVATION MASS -- mean |h.u| over the judge prompts on
    the clean model -- not vector norm, which is vacuous because every
    direction here is already a unit vector and the removal is h - (h.u)u.

    Rev 0.3 shipped this instrument for RS only and it immediately showed the
    controls were 2.5x STRONGER perturbations than the target
    (target_over_control_mean_magnitude_ratio 0.3983). AMP had no magnitude
    data at all, which made its FAIL unreadable under PREREG's own binding
    rule. Draws are numpy-only against a precomputed [n_judge, hidden] matrix,
    so matching costs ZERO GPU generation.
    """
    best, best_mag, best_err = None, None, None
    n = max(1, int(tries))
    for t in range(n):
        v = draw_fn(rng)
        m = float(mag_fn(v))
        err = (abs(m - target_mag) / target_mag) if target_mag > 0 \
            else abs(m - target_mag)
        if best is None or err < best_err:
            best, best_mag, best_err = v, m, err
        if err <= tol:
            return v, m, t + 1, True
    return best, best_mag, n, False


def guard_controls(ctrls, base_texts=None):
    """Apply the TARGET's own coherence/repetition guards to controls (D39).

    Rev 0.3 guarded only the target condition. One AMP control produced a
    projection INCREASE of 13.2128 -- about 5.8x the entire F5-vs-neutral
    dynamic range -- almost certainly a broken-text draw, and it silently
    poisoned the control mean while the control MAX became the gate the target
    had to beat. The gating ensemble is now the GUARDED one; the unguarded
    statistics are still reported so the exclusion is auditable and cannot be
    used to quietly weaken the null.
    """
    kept, kept_idx, dropped = [], [], []
    stats = []
    for i, c in enumerate(ctrls):
        rec = {
            "index": i,
            "coherence": float(c.get("coherence", 0.0)),
            "repetition": float(c.get("repetition", 0.0)),
        }
        if base_texts is not None:
            rec["behavioral_change_rate"] = behavioral_change_rate(
                base_texts, c["texts"])
        ok = (rec["coherence"] >= COHERENCE_MIN
              and rec["repetition"] >= REPETITION_MIN)
        rec["passes_guards"] = bool(ok)
        stats.append(rec)
        if ok:
            kept.append(c)
            kept_idx.append(i)
        else:
            dropped.append(i)
    return kept, {
        "per_control": stats,
        "kept_indices": kept_idx,
        "dropped_indices": dropped,
        "n_kept": len(kept),
        "n_dropped": len(dropped),
        "guard_rule": (f"a control is excluded from the GATING ensemble unless "
                       f"it clears the same guards the target must clear: "
                       f"distinct-word ratio >= {COHERENCE_MIN} AND "
                       f"distinct-4gram ratio >= {REPETITION_MIN}"),
    }


def empirical_retention_cap(base_vals, tau, retain_frac):
    """Largest uniform readout drop that still satisfies the presence rule.

    Computed EMPIRICALLY from the baseline per-prompt values rather than from a
    Gaussian approximation (PREREG rev 0.4 section 3, deviation D41): the
    rev-0.3 diagnosis' ~1.5625 cap was a normal-approximation figure and the
    per-prompt distribution was never checked for normality.
    """
    b = np.asarray(base_vals, dtype=np.float64)
    if b.size == 0:
        return 0.0
    need = retain_frac * rate_above(b, tau)
    lo, hi = 0.0, float(max(1e-9, b.max() - min(tau, b.min()) + 1.0))
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if rate_above(b - mid, tau) >= need:
            lo = mid
        else:
            hi = mid
    return float(lo)


def pass_window(base_vals, control_drops, cap, readout_range,
                min_se=PASS_WINDOW_MIN_SE,
                min_abs_frac=PASS_WINDOW_MIN_ABS_FRAC):
    """Preregistered pass window on the primary readout (D41, repaired by D48).

    window = (max guarded control drop, cap]. If it is EMPTY, narrower than
    `min_se` standard errors of the baseline readout, OR narrower than
    `min_abs_frac` of the readout's own usable range, the test cannot
    distinguish a true effect from the high-variance nuisance statistic that is
    the max of C control draws, and the preregistered outcome is
    VACUOUS_NO_PASS_REGION -- a cheap declared outcome instead of a full-cost
    FAIL that then gets over-interpreted as evidence against the hypothesis.

    THE ABSOLUTE TERM IS NOT DECORATION (D48). The SE-only rule of the rev-0.4
    first draft evaluated `se > 0 and (width / se) < min_se`, which is FALSE
    whenever se == 0 -- i.e. it could NEVER fire in exactly the saturated-probe
    regime PREREG 2.6 predicts and D41 was created to catch. `readout_range` is
    the readout's usable span (baseline minus chance for a bounded probe
    readout; the baseline-vs-other-class contrast range for a projection), so
    the absolute term stays meaningful when the variance term collapses.
    """
    b = np.asarray(base_vals, dtype=np.float64)
    n = max(1, b.size)
    se = float(b.std(ddof=1) / math.sqrt(n)) if n > 1 else 0.0
    floor = float(max(control_drops)) if control_drops else 0.0
    width = float(cap - floor)
    rng_ = abs(float(readout_range)) if readout_range else 0.0
    abs_min = float(min_abs_frac * rng_)
    too_narrow_se = bool(se > 0 and (width / se) < min_se)
    # se == 0 is the SATURATION signature, not a pass: treat a collapsed
    # variance as failing the variance term rather than skipping it.
    se_degenerate = bool(se <= 0.0)
    too_narrow_abs = bool(rng_ > 0 and width < abs_min)
    return {
        "scale": "primary readout of this test",
        "control_floor_max_guarded_control_drop": floor,
        "cap": float(cap),
        "width": width,
        "readout_usable_range": rng_,
        "baseline_standard_error": se,
        "baseline_se_degenerate": se_degenerate,
        "width_in_standard_errors": float(width / se) if se > 0 else None,
        "min_width_standard_errors": float(min_se),
        "min_width_absolute": abs_min,
        "min_width_fraction_of_range": float(min_abs_frac),
        "empty": bool(width <= 0.0),
        "underpowered": bool(too_narrow_se or too_narrow_abs or se_degenerate),
        "underpowered_reason": (
            "empty" if width <= 0.0 else
            "baseline se is degenerate (saturated readout)" if se_degenerate else
            "narrower than the standard-error minimum" if too_narrow_se else
            "narrower than the absolute fraction-of-range minimum"
            if too_narrow_abs else None),
        "rule": ("declared BEFORE the run: an empty window, one narrower than "
                 "the preregistered standard-error minimum, one narrower than "
                 "the preregistered fraction of the readout's usable range, or "
                 "one whose baseline standard error has collapsed to zero "
                 "(saturation), stamps VACUOUS_NO_PASS_REGION rather than FAIL"),
    }


def measurability(effect, baseline, quantum, n_averaged=1, standard_error=None):
    """Effect size against the instrument's floors (D42, repaired by D52).

    THE REV-0.4 FIRST DRAFT MISDERIVED THIS AND THE MISDERIVATION DID REAL
    DESIGN WORK. It compared the relative effect against the RAW bf16 relative
    quantum 2^-8, and that ratio was then used to justify dropping the DR-F2
    rail ("48x below the bf16 quantum") and to pre-label RS "not measurable".
    Every judged quantity here is a MEAN over ~32 continuation positions x ~32
    prompts, and independent quantization noise averages down by sqrt(n): at
    n ~ 1024 the effective quantization floor is ~32x SMALLER than the raw
    quantum. The BINDING floor is the STATISTICAL standard error, which on the
    rev-0.3 AMP projection was 0.2662 -- roughly 25x larger than the
    quantization scale. Both are now reported, the effective quantization floor
    is what `below_dtype_quantization_floor` keys on, and the statistical floor
    is reported separately so a null can be read as "no effect" vs "below the
    instrument" vs "below the sample's resolving power" without guessing.
    """
    if baseline is None or float(baseline) == 0.0:
        return None
    rel = abs(float(effect) / float(baseline))
    n_avg = max(1, int(n_averaged))
    q_eff = float(quantum) / math.sqrt(n_avg)
    se = None if standard_error is None else abs(float(standard_error))
    return {
        "relative_effect": rel,
        "dtype_relative_quantum_raw": float(quantum),
        "n_averaged_measurements": n_avg,
        "dtype_relative_quantum_effective": q_eff,
        "effect_over_effective_quantum": (float(rel / q_eff) if q_eff > 0
                                          else None),
        "effect_over_raw_quantum": (float(rel / float(quantum))
                                    if quantum > 0 else None),
        "below_dtype_quantization_floor": bool(rel <= q_eff),
        "statistical_standard_error_absolute": se,
        "effect_over_standard_error": (
            float(abs(float(effect)) / se) if se and se > 0 else None),
        "below_statistical_floor": (
            bool(abs(float(effect)) <= se) if se and se > 0 else None),
        "binding_floor": ("statistical standard error (the quantization floor "
                          "is ~sqrt(n_averaged) times smaller and is NOT what "
                          "binds at these sample sizes)"),
        "gating_rule": ("only below_dtype_quantization_floor is GATING "
                        "(VACUOUS_BELOW_INSTRUMENT_RESOLUTION). The statistical "
                        "floor is already handled by the paired p-values and is "
                        "reported, never used to reclassify a genuine "
                        "statistical null as UNINFORMATIVE."),
    }


def probe_viability(diag, chance, min_sd=PROBE_VIABILITY_MIN_SD,
                    min_acc_over_chance=PROBE_VIABILITY_MIN_ACC_OVER_CHANCE):
    """Preregistered viability gate for the held-out readout probe (D49).

    Two ways the substitute readout can be unusable, both predicted in advance
    by PREREG 2.6 and neither caught by the rev-0.4 first draft:

      DEAD       -- held-out accuracy on the UNABLATED judge banks is at or near
                    chance. The probe carries no class information, so a drop in
                    P(own class) measures nothing.
      SATURATED  -- P(own class) sits at 0/1 with sd ~ 0. The probe is then a
                    squashed monotone function of a projection onto a direction
                    near u_F5, and under saturation the squash REDUCES
                    sensitivity rather than increasing it -- the opposite of the
                    stated rationale for the readout change. The SIZE of any
                    drop is uninterpretable (PREREG 2.6 concedes this), and the
                    D41 pass window degenerates because the baseline se is ~0.

    A non-viable probe does NOT silently fall back into a PASS. The projection
    readout is still computed and reported in full, but the AMP test is stamped
    VACUOUS_READOUT_NOT_VIABLE: the headline comparison could not have been read
    either way, which is information about the instrument, not the hypothesis.
    """
    per_class = (diag or {}).get("per_class") or {}
    acc = (diag or {}).get("held_out_accuracy")
    sds = [float(v.get("sd_p_own_class", 0.0)) for v in per_class.values()]
    min_observed_sd = float(min(sds)) if sds else 0.0
    acc_ok = bool(acc is not None and (float(acc) - float(chance))
                  >= min_acc_over_chance)
    sd_ok = bool(sds and min_observed_sd >= min_sd)
    viable = bool(acc_ok and sd_ok)
    if viable:
        reason = None
    elif not acc_ok:
        reason = ("DEAD: held-out accuracy on the unablated judge banks "
                  f"({acc}) does not exceed chance ({chance}) by the "
                  f"preregistered margin {min_acc_over_chance}")
    else:
        reason = ("SATURATED: the smallest per-class sd of P(own class) is "
                  f"{min_observed_sd:.5f}, below the preregistered floor "
                  f"{min_sd}; P(own class) is pinned near 0/1, the size of any "
                  "drop is uninterpretable, and the D41 pass window degenerates")
    return {
        "viable": viable,
        "held_out_accuracy": acc,
        "chance_level": float(chance),
        "accuracy_over_chance": (None if acc is None
                                 else float(float(acc) - float(chance))),
        "min_accuracy_over_chance_required": float(min_acc_over_chance),
        "min_per_class_sd_observed": min_observed_sd,
        "min_per_class_sd_required": float(min_sd),
        "accuracy_leg_holds": acc_ok,
        "dispersion_leg_holds": sd_ok,
        "reason": reason,
        "rule": ("declared BEFORE the run: a probe that is DEAD (at chance) or "
                 "SATURATED (sd ~ 0) may not serve as the headline readout; the "
                 "test is stamped VACUOUS_READOUT_NOT_VIABLE and the projection "
                 "readout is reported descriptively. In-sample fit accuracy is "
                 "1.0 BY CONSTRUCTION at 96 rows in 6144 dims and is never used "
                 "as evidence of viability."),
    }


def dose_gate(magnitude_meta, n_gating,
              min_frac=DOSE_MATCHED_MIN_FRAC,
              ratio_lo=DOSE_RATIO_LO, ratio_hi=DOSE_RATIO_HI):
    """Preregistered dose-match gate (D47). Returns (holds, block).

    Rev 0.4's first draft accept/rejected controls into the target's dose band,
    silently returned the CLOSEST draw on failure, reported `n_dose_matched` and
    `target_over_control_mean_magnitude_ratio` -- and gated on NEITHER. PREREG's
    reading rule ("if the target's magnitude is far below the control mean, read
    a FAIL as 'the comparison was not matched'") covered only the FAIL
    direction. With the rev-0.4 controls orthogonalized and mean-centred the
    risk is inverted: controls can be systematically WEAKER than the target, in
    which case a PASS is uninterpretable for the mirror-image reason.
    """
    meta = magnitude_meta or {}
    matched = meta.get("dose_matched")
    ratio = meta.get("target_over_control_mean_magnitude_ratio")
    n_req = max(1, int(round(min_frac * max(1, int(n_gating)))))
    n_matched = (int(sum(1 for x in matched if x)) if matched is not None
                 else None)
    count_ok = True if n_matched is None else bool(n_matched >= n_req)
    ratio_ok = (True if ratio is None
                else bool(ratio_lo <= float(ratio) <= ratio_hi))
    holds = bool(count_ok and ratio_ok)
    return holds, {
        "n_dose_matched": n_matched,
        "n_dose_matched_required": n_req,
        "count_leg_holds": count_ok,
        "target_over_control_mean_magnitude_ratio": ratio,
        "ratio_band": [float(ratio_lo), float(ratio_hi)],
        "ratio_leg_holds": ratio_ok,
        "holds": holds,
        "rule": ("declared BEFORE the run: a control ensemble that could not be "
                 "brought into the target's dose band is not a matched null in "
                 "EITHER direction. Controls stronger than the target make a "
                 "FAIL unreadable; controls weaker than the target make a PASS "
                 "unreadable. Failure stamps VACUOUS_DOSE_UNMATCHED."),
    }


def slot_verb_audit(frames):
    """Machine-readable audit of PREREG 2.1's slot-filler uniqueness claim.

    Rev 0.3 review fix D25: the rev-0.3 draft asserted "each slot filler is
    unique across frames ... and no verb is shared across classes", which was
    FALSE as authored. The claim is now softened to what is true and the actual
    overlaps are computed at run time and reported, so the claim can never
    silently drift from the bank again.
    """
    cols = {"f5": 1, "f2": 2, "neutral": 3}
    heads = {}
    for name, ci in cols.items():
        heads[name] = [f[ci].strip().split()[0].lower() for f in frames]
    within = {}
    for name, ws in heads.items():
        d = {}
        for i, w in enumerate(ws):
            d.setdefault(w, []).append(i + 1)
        within[name] = {w: ix for w, ix in d.items() if len(ix) > 1}
    across = {}
    keys = list(cols)
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            a, b = keys[i], keys[j]
            ov = sorted(set(heads[a]) & set(heads[b]))
            if ov:
                across[f"{a}_vs_{b}"] = ov
    return {
        "n_frames": len(frames),
        "within_class_repeated_head_verbs": within,
        "cross_class_shared_head_verbs": across,
        "claim_as_stated_in_prereg_2_1": (
            "head verbs are unique within each class and shared across classes "
            "ONLY in the rev-0.2 verbatim block (frames 1-24), which is "
            "reproduced unaltered by design; the residual overlaps are listed "
            "above rather than asserted away"),
    }


def random_matched_heads(head_set, n_heads, rng, n_layers=None):
    """Count-matched random head control, with CROSS-LAYER fallback.

    Rev 0.3 review fix D24: the rev-0.3 draft took min(len(hs), len(pool)) per
    layer, so whenever a layer held more than half its heads in the top-k the
    CONTROL ablated FEWER heads than the target -- making the target look more
    selective for free. At 31-of-32 heads per layer that is a live risk. Here
    the per-layer shortfall is made up by sampling unused heads from OTHER
    layers, so the control always ablates exactly len(head_set) heads. The
    realised count is reported alongside the target's.
    """
    by_layer = {}
    for (L, h) in head_set:
        by_layer.setdefault(int(L), []).append(int(h))
    target_total = sum(len(v) for v in by_layer.values())
    used = set()
    out = []
    shortfall = 0
    for L, hs in sorted(by_layer.items()):
        pool = [h for h in range(n_heads) if h not in hs and (L, h) not in used]
        take = min(len(hs), len(pool))
        shortfall += len(hs) - take
        if take <= 0:
            continue
        pick = rng.choice(len(pool), size=take, replace=False)
        for i in pick:
            out.append((L, int(pool[int(i)])))
            used.add((L, int(pool[int(i)])))
    if shortfall > 0 and n_layers:
        target_set = set((int(a), int(b)) for a, b in head_set)
        spare = [(L, h) for L in range(int(n_layers)) for h in range(n_heads)
                 if (L, h) not in target_set and (L, h) not in used]
        if spare:
            take = min(shortfall, len(spare))
            pick = rng.choice(len(spare), size=take, replace=False)
            for i in pick:
                out.append(spare[int(i)])
                used.add(spare[int(i)])
    assert len(out) <= target_total
    return out


# ---------------------------------------------------------------------------
# Generation (hooks active) + CLEAN-PASS judgment (hooks removed)
# ---------------------------------------------------------------------------

def generate_texts(model, tok, prompts, device, max_new_tokens,
                   n_samples=1, temperature=RS_TEMPERATURE, sample_seed=0):
    """Greedy when n_samples == 1 (rev-0.2 discipline, unchanged).

    n_samples > 1 uses SEEDED temperature sampling and returns a list of k
    continuations per prompt (rev-0.3 RS variance control). Determinism is
    preserved by a per-(prompt, draw) manual seed; this is a declared prereg
    change and it changes the meaning of "the model wrote this" from a single
    greedy mode to an average over a seeded sampled neighbourhood.
    """
    outs = []
    for pi, p in enumerate(prompts):
        enc = tok(p, return_tensors="pt").to(device)
        draws = []
        for k in range(n_samples):
            gkw = dict(max_new_tokens=max_new_tokens,
                       pad_token_id=tok.eos_token_id)
            if n_samples > 1:
                torch.manual_seed(int(sample_seed) + 1013 * pi + k)
                gkw.update(do_sample=True, temperature=float(temperature),
                           top_k=0, top_p=1.0)
            else:
                gkw.update(do_sample=False)
            with torch.no_grad():
                g = model.generate(**enc, **gkw)
            draws.append(tok.decode(
                g[0, enc["input_ids"].shape[1]:], skip_special_tokens=True))
        outs.append(draws if n_samples > 1 else draws[0])
    return outs


def gen_condition(model, tok, prompts, device, hooks, max_new_tokens,
                  n_samples=1, sample_seed=0):
    """Generate under intervention hooks. Returns raw continuations ONLY.

    All judgment happens later, on a clean forward pass: the intervention can
    influence the result ONLY through the text it caused the model to produce.
    """
    if hooks:
        with install_hooks(hooks):
            return generate_texts(model, tok, prompts, device, max_new_tokens,
                                  n_samples=n_samples, sample_seed=sample_seed)
    return generate_texts(model, tok, prompts, device, max_new_tokens,
                          n_samples=n_samples, sample_seed=sample_seed)


def clean_pass(model, tok, prompts, continuations, device, block, dirs,
               mass_ids=None):
    """CLEAN-PASS measurement of generated continuations (NO hooks installed).

    Returns, per (prompt, continuation):
      * mean over continuation token positions of the block-output residual
        projected onto each unit direction in `dirs`;
      * mean over continuation STEPS of the total next-token probability mass
        assigned to each frozen lexicon in `mass_ids` -- computed on this same
        clean re-forward, never with hooks active;
      * REV 0.4 (deviation D35): the mean-over-continuation-positions RESIDUAL
        VECTOR itself, so a held-out readout PROBE can be applied to it. The
        probe readout is the rev-0.4 primary AMP statistic; it is bounded with
        a defined chance floor, unlike a raw projection whose baseline is 78.7%
        bank-invariant offset. The vector comes from the same clean re-forward
        and the same continuation segment as the projections, so it inherits
        the clean-pass rule unchanged.

    The mass measure obeys the clean-pass rule exactly: byte-identical text
    yields byte-identical mass, i.e. exactly zero effect. Computing it with
    hooks ACTIVE would reintroduce the FATAL-1 near-analytic artifact in logit
    coordinates (u_RS is a residual direction and the unembedding is linear in
    the residual stream), which is why the guard below covers it too.
    """
    if _HOOKS_ACTIVE:
        raise RuntimeError(
            "clean-pass violation: measurement requested while hooks active")
    names = list(dirs)
    D = np.stack([np.asarray(dirs[n], dtype=np.float64) for n in names])
    mass_ids = mass_ids or {}
    mass_t = {k: torch.tensor(sorted(set(int(i) for i in v)), dtype=torch.long)
              for k, v in mass_ids.items() if len(v) > 0}
    out = {n: [] for n in names}
    mout = {k: [] for k in mass_t}
    vecs = []
    for p, c in zip(prompts, continuations):
        enc = tok(p + c, return_tensors="pt").to(device)
        n_prompt = tok(p, return_tensors="pt")["input_ids"].shape[1]
        with torch.no_grad():
            res = model(**enc, output_hidden_states=True)
        # REV 0.4 (D33): explicit .to(torch.float32) rather than a bare
        # .float(), so the intent survives the dtype change, then float64 in
        # numpy. The bf16 dot-product error over 6144 dims with fp32
        # accumulation is 1.44e-5 x ||h||, i.e. negligible -- but only because
        # the accumulation is forced (see pin_precision_backends).
        hs = res.hidden_states[block + 1][0].to(torch.float32).cpu().numpy()
        seg = hs[n_prompt:] if hs.shape[0] > n_prompt else hs[-1:]
        seg = np.asarray(seg, dtype=np.float64)
        mv = (seg @ D.T).mean(axis=0)
        for i, n in enumerate(names):
            out[n].append(float(mv[i]))
        vecs.append(seg.mean(axis=0))
        if mass_t:
            logits = res.logits[0].to(torch.float32)
            T = int(logits.shape[0])
            lo = max(n_prompt - 1, 0)
            hi = max(T - 1, lo + 1)
            step = logits[lo:hi] if hi > lo else logits[-1:]
            probs = torch.softmax(step, dim=-1)
            for k, ids in mass_t.items():
                mout[k].append(float(
                    probs.index_select(1, ids.to(probs.device)).sum(-1).mean()))
    return ({n: np.asarray(v) for n, v in out.items()},
            {k: np.asarray(v) for k, v in mout.items()},
            np.stack(vecs) if vecs else np.zeros((0, D.shape[1])))


def measure_condition(model, tok, prompts, texts, device, block, dirs,
                      mass_ids=None):
    """Clean-pass measure dict for one condition.

    `texts` is either one continuation per prompt (greedy) or a list of k
    seeded sampled continuations per prompt; in the latter case every measure
    is averaged WITHIN prompt first, so pairing stays at the prompt level and
    the paired statistic is unaffected by k.
    """
    grouped = bool(texts) and isinstance(texts[0], (list, tuple))
    flat_prompts, flat_texts, gid = [], [], []
    for i, (p, t) in enumerate(zip(prompts, texts)):
        items = list(t) if grouped else [t]
        for s in items:
            flat_prompts.append(p)
            flat_texts.append(s)
            gid.append(i)
    projs, masses, vecs = clean_pass(model, tok, flat_prompts, flat_texts,
                                     device, block, dirs, mass_ids)
    gid = np.asarray(gid)
    ngroups = len(prompts)

    def group_mean(arr):
        return np.asarray([float(np.mean(arr[gid == i])) for i in range(ngroups)])

    def group_mean_rows(arr):
        if arr.size == 0:
            return arr
        return np.stack([arr[gid == i].mean(axis=0) for i in range(ngroups)])

    per_hedge = np.asarray([float(hedge_count(s)) for s in flat_texts])
    per_coh = np.asarray([distinct_ratio(s) for s in flat_texts])
    per_rep = np.asarray([distinct_ngram_ratio(s, 4) for s in flat_texts])
    return {
        "proj": {k: [float(x) for x in group_mean(v)] for k, v in projs.items()},
        "mass": {k: [float(x) for x in group_mean(v)] for k, v in masses.items()},
        # REV 0.4 (D35): per-prompt readout vectors, kept in memory only (never
        # serialized into the report -- they are [n_prompts, hidden]).
        "vec": group_mean_rows(vecs),
        "hedges": [float(x) for x in group_mean(per_hedge)],
        "mean_hedge": float(per_hedge.mean()) if per_hedge.size else 0.0,
        "coherence": float(per_coh.mean()) if per_coh.size else 0.0,
        "repetition": float(per_rep.mean()) if per_rep.size else 0.0,
        # REV 0.4 (D39): per-prompt damage descriptors, so a control that
        # "beat" the target can be told apart from a control that simply broke
        # the text. Rev 0.3 recorded these for the TARGET condition only.
        "per_coherence": [float(x) for x in group_mean(per_coh)],
        "per_repetition": [float(x) for x in group_mean(per_rep)],
        "texts": texts,
        "sample_texts": (["|".join(t)[:400] for t in texts[:3]] if grouped
                         else texts[:3]),
    }


def mean_mass(measure, key):
    v = measure.get("mass", {}).get(key)
    return float(np.mean(v)) if v else 0.0


# ---------------------------------------------------------------------------
# Surface control (char-ngram; mandatory, reported, non-gating)
# ---------------------------------------------------------------------------

def char_ngram_control(fit_pos, fit_neg, judge_pos, judge_neg):
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.linear_model import LogisticRegression
    except Exception as e:  # pragma: no cover
        return {"status": "UNAVAILABLE_SKLEARN", "error": str(e)}
    vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5))
    X = vec.fit_transform(fit_pos + fit_neg)
    y = np.array([1] * len(fit_pos) + [0] * len(fit_neg))
    clf = LogisticRegression(max_iter=1000).fit(X, y)
    Xj = vec.transform(judge_pos + judge_neg)
    yj = np.array([1] * len(judge_pos) + [0] * len(judge_neg))
    acc = float(clf.score(Xj, yj))
    return {
        "status": "OK",
        "judge_accuracy": acc,
        "interpretation": (
            "Banks are minimal pairs: separability is confined to the drive "
            "slot BY DESIGN and is expected to be high. This descriptor bounds "
            "the claim (directions may carry topic/lexical content); the typed "
            "directional signatures (sign, presence-vs-magnitude, selectivity, "
            "connection) are what the tests judge, and drive-vs-topic "
            "semantics is explicitly NOT claimed (see PREREG section 6)."),
    }


# ---------------------------------------------------------------------------
# RS rev 0.3: teacher-forced suppression-gap precondition (no generation)
# ---------------------------------------------------------------------------

def rs_precondition(model, tok, licensed, conflicted, device, block, u_f5,
                    hedge_ids, ctrl_ids, act_ids, restrain_ids):
    """Teacher-forced, clean-model precondition for RS-F5 (PREREG section 4).

    Replaces the rev-0.2 gate "baseline mean hedge > 0 AND >= 25% of greedy
    continuations contain a hedge word", which was structurally unreachable on
    a base model (measured: pythia-160m and gpt2-medium emit exactly 0 hedge
    words on all ambivalent prompts at 24, 64 AND 128 new tokens).

    G1  u_F5 projection gap (licensed - conflicted) > 0, Wilcoxon-Pratt p<alpha
    G2  hedge-MASS gap (conflicted - licensed) > 0, Wilcoxon-Pratt p<alpha, AND
        exceeding the frequency/POS-matched control-lexicon gap
    G3  act-vs-restrain next-token log-odds gap (SECONDARY: reported, not gating)

    PASS of G1 AND G2 means the model demonstrably suppresses agency under
    conflict, i.e. there is a brake to remove. Otherwise the test is
    VACUOUS_NO_BRAKE -- which is now an INFORMATIVE verdict ("this model has no
    measurable brake here"), not an artifact of an unreachable threshold.
    """
    if _HOOKS_ACTIVE:
        raise RuntimeError("clean-pass violation: RS precondition under hooks")
    mass_t = {"hedge": hedge_ids, "control_lex": ctrl_ids,
              "act": act_ids, "restrain": restrain_ids}
    mass_t = {k: torch.tensor(sorted(set(int(i) for i in v)), dtype=torch.long)
              for k, v in mass_t.items() if len(v) > 0}

    def measure(prompts):
        proj, hedge, ctrl, act, res = [], [], [], [], []
        for p in prompts:
            enc = tok(p, return_tensors="pt").to(device)
            with torch.no_grad():
                out = model(**enc, output_hidden_states=True)
            h = out.hidden_states[block + 1][0, -1].float().cpu().numpy()
            proj.append(float(h @ np.asarray(u_f5, dtype=np.float64)))
            probs = torch.softmax(out.logits[0, -1].float(), dim=-1)
            got = {}
            for k, ids in mass_t.items():
                got[k] = float(probs.index_select(
                    0, ids.to(probs.device)).sum())
            hedge.append(got.get("hedge", 0.0))
            ctrl.append(got.get("control_lex", 0.0))
            act.append(got.get("act", 0.0))
            res.append(got.get("restrain", 0.0))
        return (np.asarray(proj), np.asarray(hedge), np.asarray(ctrl),
                np.asarray(act), np.asarray(res))

    pl, hl, cl, al, rl = measure(licensed)
    pc, hc, cc, ac, rc = measure(conflicted)

    g1_diffs = (pl - pc).tolist()
    g1_p, g1_stats = wilcoxon_pratt(g1_diffs)
    g2_diffs = (hc - hl).tolist()
    g2_p, g2_stats = wilcoxon_pratt(g2_diffs)
    ctrl_gap = float(np.mean(cc - cl))
    eps = 1e-12
    lo_l = np.log(al + eps) - np.log(rl + eps)
    lo_c = np.log(ac + eps) - np.log(rc + eps)
    g3_diffs = (lo_l - lo_c).tolist()
    g3_p, g3_stats = wilcoxon_pratt(g3_diffs)

    g1_ok = (float(np.mean(g1_diffs)) > 0.0) and (g1_p < SIGN_ALPHA)
    hedge_gap = float(np.mean(g2_diffs))
    g2_ok = (hedge_gap > 0.0) and (g2_p < SIGN_ALPHA) and (hedge_gap > ctrl_gap)
    out = {
        "n_pairs": int(len(licensed)),
        "G1_proj_gap_licensed_minus_conflicted": float(np.mean(g1_diffs)),
        "G1_wilcoxon_pratt_p": g1_p,
        "G1_stats": g1_stats,
        "G1_holds": bool(g1_ok),
        "G2_hedge_mass_gap_conflicted_minus_licensed": hedge_gap,
        "G2_control_lexicon_gap": ctrl_gap,
        "G2_wilcoxon_pratt_p": g2_p,
        "G2_stats": g2_stats,
        "G2_holds": bool(g2_ok),
        "G3_act_vs_restrain_logodds_gap": float(np.mean(g3_diffs)),
        "G3_wilcoxon_pratt_p": g3_p,
        "G3_secondary_only": True,
        "mean_hedge_mass_licensed": float(hl.mean()),
        "mean_hedge_mass_conflicted": float(hc.mean()),
        "mean_proj_licensed": float(pl.mean()),
        "mean_proj_conflicted": float(pc.mean()),
        "holds": bool(g1_ok and g2_ok),
        "rule": "require G1 AND G2; G3 is reported and never gating",
    }
    return out


# ---------------------------------------------------------------------------
# Harness-sanity machinery (MEM copy heads / CHECK induction gate) --
# OUTSIDE the aggregate and outside the verdict.
# ---------------------------------------------------------------------------

def mem_usable_items(tok, items):
    usable = []
    for it in items:
        pids = tok(it["prompt"], add_special_tokens=False)["input_ids"]
        found = None
        for key_try in (it["key"], it["key"].lstrip()):
            kids = tok(key_try, add_special_tokens=False)["input_ids"]
            pos = find_sublist(pids, kids)
            if pos >= 0:
                found = {"prompt": it["prompt"], "key": it["key"],
                         "key_ids": kids,
                         "key_pos": list(range(pos, pos + len(kids)))}
                break
        if found is not None:
            usable.append(found)
        else:
            print(f"[warn] MEM item key not locatable in prompt ids, dropped: {it['key']!r}")
    return usable


def mem_head_scores(model, tok, usable, device, n_layers, n_heads):
    scores = np.zeros((n_layers, n_heads))
    for it in usable:
        enc = tok(it["prompt"], return_tensors="pt").to(device)
        with torch.no_grad():
            out = model(**enc, output_attentions=True)
        kp = torch.tensor(it["key_pos"], dtype=torch.long)
        for L in range(n_layers):
            # fp32 BEFORE the reduction (rev 0.4 second pass, D52). Under bf16
            # weights `sel.sum(-1).float()` accumulates the sum in bf16 and only
            # then casts, and 84 of 2,816 heads are selected off this ranking --
            # while CHECK is the battery's sole liveness evidence.
            att = out.attentions[L][0].to(torch.float32)  # [heads, T, T]
            sel = att[:, -1, :].index_select(1, kp.to(att.device))
            scores[L] += sel.sum(-1).cpu().numpy()
    return scores / max(1, len(usable))


def copy_accuracy(model, tok, usable, device, hooks):
    correct = 0
    with install_hooks(hooks):
        for it in usable:
            enc = tok(it["prompt"], return_tensors="pt").to(device)
            with torch.no_grad():
                out = model(**enc)
            pred = int(out.logits[0, -1].argmax().item())
            if pred == int(it["key_ids"][0]):
                correct += 1
    return correct / max(1, len(usable))


def build_induction_seqs(rng, n_seq, seg_len, lo=2000, hi=20000):
    seqs = []
    for _ in range(n_seq):
        toks = rng.choice(np.arange(lo, hi), size=seg_len, replace=False)
        seqs.append(np.concatenate([toks, toks]).astype(np.int64))
    return seqs


def gate_scores(model, seqs, device, hooks):
    """Per-seq mean logprob advantage: pattern-available half vs no-pattern half."""
    vals = []
    with install_hooks(hooks):
        for s in seqs:
            ids = torch.tensor(s, dtype=torch.long, device=device).unsqueeze(0)
            with torch.no_grad():
                out = model(input_ids=ids)
            lp = torch.log_softmax(out.logits[0].float(), dim=-1)
            seg = len(s) // 2
            second, first = [], []
            for j in range(seg - 1):
                tgt = int(s[j + 1])
                second.append(float(lp[seg + j, tgt]))
                first.append(float(lp[j, tgt]))
            vals.append(float(np.mean(second) - np.mean(first)))
    return vals


def induction_head_scores(model, seqs, device, n_layers, n_heads):
    scores = np.zeros((n_layers, n_heads))
    for s in seqs:
        ids = torch.tensor(s, dtype=torch.long, device=device).unsqueeze(0)
        with torch.no_grad():
            out = model(input_ids=ids, output_attentions=True)
        seg = len(s) // 2
        for L in range(n_layers):
            # fp32 BEFORE the mean (rev 0.4 second pass, D52) -- see
            # mem_head_scores for why this ranking must not accumulate in bf16.
            att = out.attentions[L][0].to(torch.float32)  # [heads, T, T]
            vals = [att[:, seg + j, j + 1] for j in range(seg - 1)]
            scores[L] += torch.stack(vals, 0).mean(0).cpu().numpy()
    return scores / max(1, len(seqs))


def top_heads(score_matrix, k):
    flat = np.argsort(-score_matrix, axis=None)[:k]
    n_heads = score_matrix.shape[1]
    return [(int(i // n_heads), int(i % n_heads)) for i in flat]


# ---------------------------------------------------------------------------
# Core test evaluation (per-test, matched controls, gating selectivity)
# ---------------------------------------------------------------------------

def _paired_block(base, tgt, ctrls, key, sign=+1):
    """Two paired arms, both with byte-identity zero masks (rev 0.3, D23).

    ARM A (control-mean arm, the rev-0.3 draft's only arm): per-prompt
    difference between the mean of the C control conditions and the target. Its
    zero mask is "the target continuation equals EVERY control continuation" --
    which is far rarer than the rev-0.2 case that produced n_effective = 6, so
    on its own the Pratt zero handling was effectively inert.

    ARM B (baseline arm, NEW): per-prompt difference between the unablated
    baseline and the target. Its zero mask is exactly "the intervention left
    this prompt's text byte-identical", i.e. 1 - behavioral_change_rate, which
    is the quantity the deviations log claims to be repairing.

    `sign` = +1 when the prediction is a DROP (base - target > 0), -1 when the
    prediction is an INCREASE (target - base > 0, the RS anchor).

    BOTH arms must clear alpha for a PASS. That is stricter than the rev-0.3
    draft and is the honest direction: an effect has to differ from baseline
    AND beat the control ensemble.
    """
    b = readout_vals(base, key)
    t = readout_vals(tgt, key)
    ctrl_mean = np.mean([readout_vals(c, key) for c in ctrls], axis=0) \
        if ctrls else b
    zm_ctrl = all_identity_mask(tgt["texts"], ctrls)
    zm_base = identity_mask(base["texts"], tgt["texts"])
    diffs_ctrl = [float(sign * (cm - tv)) for cm, tv in zip(ctrl_mean, t)]
    diffs_base = [float(sign * (bv - tv)) for bv, tv in zip(b, t)]
    p_c, s_c = wilcoxon_pratt(diffs_ctrl, zero_mask=zm_ctrl)
    p_b, s_b = wilcoxon_pratt(diffs_base, zero_mask=zm_base)
    return {
        "diffs_vs_control_mean": diffs_ctrl,
        "diffs_vs_baseline": diffs_base,
        "p_vs_control_mean": p_c,
        "p_vs_baseline": p_b,
        "stats_vs_control_mean": s_c,
        "stats_vs_baseline": s_b,
        "both_arms_hold": bool(p_c < SIGN_ALPHA and p_b < SIGN_ALPHA),
        "arm_rule": ("BOTH the control-mean arm and the baseline arm must be "
                     "below alpha; zeros are byte-identity ties, kept by Pratt"),
    }


def _resolve_readout(readout, key):
    """'proj' is a mode name, not a measure key: resolve it to the direction."""
    return key if readout in (None, "proj") else readout


def _drive_common(base, tgt, ctrls, cross, tau, base_other, xrail, key, okey,
                  readout, min_ctrl, quantum, magnitude_meta, cap_mode,
                  readout_viability=None, n_averaged=1, strict_gates=True):
    """Shared rev-0.4 evaluation body for the DR and AMP drive tests.

    Everything that D37-D42 generalize across the battery lives here so that a
    fix cannot be applied to one test and silently skipped on another -- which
    is exactly how rev 0.3 ended up with a magnitude instrument wired to RS and
    absent from AMP, and orthogonalized controls on RS and contaminated ones on
    AMP.

    `readout` selects the PRIMARY statistic: "probe_p" is the rev-0.4 held-out
    readout probe (bounded, chance 1/3, full dynamic range) and `key` is the
    projection direction retained as the reported secondary. Presence, and
    therefore the starvation-vs-attenuation discriminator, always stays on the
    PROJECTION, because tau is defined there.
    """
    proj_b = readout_vals(base, key)
    proj_t = readout_vals(tgt, key)
    base_rate = rate_above(proj_b, tau)
    tgt_rate = rate_above(proj_t, tau)

    # --- D39: guard the control ensemble the same way the target is guarded.
    guarded, guard_info = guard_controls(ctrls, base_texts=base["texts"])

    r_b = readout_vals(base, readout)
    r_t = readout_vals(tgt, readout)
    drop = float(r_b.mean() - r_t.mean())
    ctrl_drops_all = [float(r_b.mean() - readout_vals(c, readout).mean())
                      for c in ctrls]
    ctrl_drops = [float(r_b.mean() - readout_vals(c, readout).mean())
                  for c in guarded]
    cross_drop = float(r_b.mean() - readout_vals(cross, readout).mean())
    paired = _paired_block(base, tgt, guarded or ctrls, readout, sign=+1)
    p_ctrl = control_ensemble_p(drop, ctrl_drops)
    change = behavioral_change_rate(base["texts"], tgt["texts"])

    # --- D44: cross-rail on the SAME bounded readout for both legs, so the two
    # effect sizes are commensurable. Rev 0.3 standardized the target leg by
    # std_F5 = 1.5060 and the cross-rail leg by std_F2 = 1.1758 and then
    # compared the ratio directly, which overstated that leg by ~28%.
    xr_b = readout_vals(base_other, readout if readout == "probe_p" else okey)
    xr_c = readout_vals(xrail, readout if readout == "probe_p" else okey)
    d_target = effect_size(r_b, r_t)
    d_xrail = effect_size(xr_b, xr_c)
    raw_xrail_drop = float(xr_b.mean() - xr_c.mean())

    # Projection-scale numbers, retained verbatim so rev 0.3 stays comparable.
    proj_drop = float(proj_b.mean() - proj_t.mean())
    res = {
        "primary_readout": readout,
        "readout_note": (
            "PRIMARY = held-out 3-way readout probe P(own class) on the "
            "generated text's activations: bounded, chance 1/3, full dynamic "
            "range. Rev 0.3's raw projection readout is retained below as a "
            "SECONDARY, together with a contrast-normalized version; on the "
            "rev-0.3 numbers 78.7% of that projection was bank-invariant "
            "offset, so its noise floor sat at a large fraction of the whole "
            "signal. NOTE: contrast normalization alone is an AFFINE rescale "
            "and changes NO p-value and NO ordering against controls -- it "
            "fixes interpretability, not selectivity. THE READOUT-FAMILY CLAIM "
            "IS BOUNDED (rev 0.4 second pass): probe_p comes from a regularized "
            "linear classifier on the SAME L* residuals the projection is read "
            "from, so it is close to a squashed monotone function of a "
            "projection onto a direction near u_F5. What actually differs is "
            "the sigmoid and the 3-way competition -- and under SATURATION the "
            "squash REDUCES sensitivity rather than increasing it, which is why "
            "the D49 viability gate must clear before this readout is allowed "
            "to be the headline."
            if readout == "probe_p" else
            "PRIMARY = mean clean projection onto the target direction."),
        "baseline_mean_readout": float(r_b.mean()),
        "target_mean_readout": float(r_t.mean()),
        "readout_chance_level": (READOUT_PROBE_CHANCE
                                 if readout == "probe_p" else None),
        "targeted_drop": drop,
        "matched_control_drops": ctrl_drops,
        "max_matched_control_drop": float(max(ctrl_drops)) if ctrl_drops else None,
        "matched_control_drops_unguarded_reported_only": ctrl_drops_all,
        "max_matched_control_drop_unguarded_reported_only": (
            float(max(ctrl_drops_all)) if ctrl_drops_all else None),
        "control_ensemble_p": p_ctrl,
        "control_ensemble_p_unguarded_reported_only": control_ensemble_p(
            drop, ctrl_drops_all),
        "control_guard": guard_info,
        "control_magnitude": magnitude_meta,
        "n_controls_drawn": len(ctrls),
        "n_controls_gating": len(guarded),
        "wilcoxon_pratt_p": paired["p_vs_control_mean"],
        "wilcoxon_pratt_stats": paired["stats_vs_control_mean"],
        "paired_arms": paired,
        "legacy_sign_test_p_reported_only": sign_test_p(
            paired["diffs_vs_control_mean"]),
        "behavioral_change_rate": change,
        "baseline_presence_rate": float(base_rate),
        "target_presence_rate": float(tgt_rate),
        "effect_size_target": d_target,
        "effect_size_cross_rail": d_xrail,
        "raw_cross_rail_drop": raw_xrail_drop,
        "cross_rail_note": (
            "effect_size_cross_rail measures COLLATERAL damage to the OTHER "
            "rail's content on the OTHER rail's prompts caused by the SAME "
            "targeted intervention. It is NOT 'the other rail's direction "
            "moving this rail's content' -- that quantity is "
            "cross_direction_drop / cross_cover_drop. Both legs are "
            "standardized on the same readout in rev 0.4 (deviation D44)."),
        "selectivity_gate": f"|d_cross_rail| <= {SELECTIVITY_MAX_RATIO} x d_target",
        "coherence_target": tgt["coherence"],
        "repetition_target": tgt["repetition"],
        "sample_texts_target": tgt["sample_texts"],
        # --- rev-0.3-comparable projection-scale block (secondary) ---
        "secondary_projection": {
            "baseline_mean_proj": float(proj_b.mean()),
            "target_mean_proj": float(proj_t.mean()),
            "targeted_drop": proj_drop,
            "tau": float(tau),
            "implied_other_class_mean": float(2.0 * tau - proj_b.mean()),
            "contrast_dynamic_range": float(2.0 * (proj_b.mean() - tau)),
            "targeted_drop_contrast_normalized": (
                float(proj_drop / (2.0 * (proj_b.mean() - tau)))
                if abs(proj_b.mean() - tau) > 1e-12 else None),
            "offset_fraction_of_readout": (
                float(1.0 - (2.0 * (proj_b.mean() - tau)) / proj_b.mean())
                if abs(proj_b.mean()) > 1e-12 else None),
            "baseline_coefficient_of_variation": (
                float(proj_b.std() / proj_b.mean())
                if abs(proj_b.mean()) > 1e-12 else None),
            "cv_note": ("a small CV means the direction is dominated by "
                        "alignment with the residual stream's large mean "
                        "component rather than by the class contrast; rev 0.4 "
                        "reports it rather than changing the target, because "
                        "changing the target, the controls, the readout, the "
                        "model AND the dtype in one revision would make the "
                        "result uninterpretable (see PREREG section 10, "
                        "'What rev 0.4 deliberately did NOT change')"),
        },
        "measurability": measurability(
            drop, r_b.mean(), quantum, n_averaged=n_averaged,
            standard_error=(float(r_b.std(ddof=1) / math.sqrt(r_b.size))
                            if r_b.size > 1 else None)),
        "readout_viability": readout_viability,
        "dose_gate": None,
    }
    dose_holds, dose_block = dose_gate(magnitude_meta, len(guarded))
    res["dose_gate"] = dose_block

    # --- preconditions, in preregistered order ---
    if (strict_gates and readout_viability is not None
            and not readout_viability.get('viable', True)):
        res["status"] = "VACUOUS_READOUT_NOT_VIABLE"
        res["reason"] = (
            "the held-out readout probe failed its preregistered viability gate "
            f"(D49): {readout_viability.get('reason')}. The projection readout "
            "is reported in full above as a descriptive secondary, but the "
            "rev-0.4 headline readout change (D35) did NOT take effect and no "
            "rev-0.4 selectivity claim is licensed from this test")
        return res
    if base_rate < BASELINE_PRESENCE_MIN:
        res["status"] = "VACUOUS"
        res["reason"] = (f"baseline presence rate {base_rate:.2f} below "
                         f"precondition {BASELINE_PRESENCE_MIN}; nothing "
                         "demonstrably fires to be lost")
        return res
    if change < BEHAVIORAL_CHANGE_MIN:
        res["status"] = "VACUOUS_NO_BEHAVIORAL_CHANGE"
        res["reason"] = (f"only {change:.2f} of judge prompts changed text under "
                         f"the targeted intervention (< {BEHAVIORAL_CHANGE_MIN}); "
                         "under the clean-pass rule the intervention never "
                         "engaged the behavioural channel, so the label was "
                         "never actually tested")
        return res
    if tgt["coherence"] < COHERENCE_MIN or tgt["repetition"] < REPETITION_MIN:
        res["status"] = "CONFOUNDED"
        res["reason"] = ("target condition failed the coherence and/or "
                         "repetition guard (fluency / degenerate-loop confound)")
        return res
    if len(guarded) < min_ctrl:
        res["status"] = "VACUOUS_CONTROL_ENSEMBLE_DEGRADED"
        res["reason"] = (
            f"only {len(guarded)} of {len(ctrls)} controls cleared the target's "
            f"own coherence/repetition guards, below the required "
            f"{min_ctrl}; the control-ensemble p floor 1/(C+1) is no longer "
            "strictly below alpha and a gate built on broken-text controls is "
            "not a null")
        return res
    if strict_gates and not dose_holds:
        res["status"] = "VACUOUS_DOSE_UNMATCHED"
        res["reason"] = (
            "the control ensemble could not be brought into the target's dose "
            f"band (D47): {dose_block}. A null that is not dose-matched cannot "
            "be read in EITHER direction -- controls stronger than the target "
            "make a FAIL unreadable, controls weaker than the target make a "
            "PASS unreadable")
        return res
    meas = res.get("measurability")
    if (strict_gates and meas is not None
            and meas.get('below_dtype_quantization_floor')):
        res["status"] = "VACUOUS_BELOW_INSTRUMENT_RESOLUTION"
        res["reason"] = (
            "the relative effect "
            f"{meas['relative_effect']:.3e} is at or below the EFFECTIVE dtype "
            f"quantization floor {meas['dtype_relative_quantum_effective']:.3e} "
            f"(raw quantum {meas['dtype_relative_quantum_raw']:.3e} divided by "
            f"sqrt({meas['n_averaged_measurements']}) averaged measurements). "
            "D42 is GATING for PASS in rev 0.4's second pass, not only a label "
            "on nulls: a headline test may not PASS on a readout the artifact "
            "itself declares unresolvable")
        return res

    # --- D41: preregistered pass window on the primary readout ---
    res["presence_retention_cap_projection"] = empirical_retention_cap(
        proj_b, tau, AMP_PRESENCE_RETAIN)
    if cap_mode == "none":
        res["pass_window"] = {
            "applies": False,
            "control_floor_max_guarded_control_drop": (
                float(max(ctrl_drops)) if ctrl_drops else None),
            "reason": ("this test's signature (starvation) has NO upper ceiling "
                       "on the drop, so there is no bounded pass window that "
                       "could be empty; the control floor is reported alone"),
        }
    else:
        cap = (float(r_b.mean() - READOUT_PROBE_CHANCE)
               if cap_mode == "readout_floor"
               else empirical_retention_cap(proj_b, tau, AMP_PRESENCE_RETAIN))
        # D48: the readout's USABLE RANGE, so the window has an absolute floor
        # that survives a collapsed baseline variance. For the bounded probe
        # readout that is baseline-minus-chance; for the projection it is the
        # own-class-vs-other-class contrast range 2*(mean - tau), which is the
        # exact quantity rev 0.3's diagnosis showed was only 21.3% of the raw
        # readout (2.2886 of 10.7386).
        readout_range = (float(r_b.mean() - READOUT_PROBE_CHANCE)
                         if cap_mode == "readout_floor"
                         else float(2.0 * (proj_b.mean() - tau)))
        window = pass_window(r_b, ctrl_drops, cap, readout_range)
        window["applies"] = True
        window["cap_definition"] = (
            "baseline readout minus the probe's chance level (the largest drop "
            "the bounded readout can express)" if cap_mode == "readout_floor"
            else "the largest uniform projection drop that still keeps the "
                 "presence rate at or above the retention fraction, computed "
                 "EMPIRICALLY from the baseline per-prompt values")
        res["pass_window"] = window
        if window["empty"] or window["underpowered"]:
            res["status"] = "VACUOUS_NO_PASS_REGION"
            res["reason"] = (
                "the pass window "
                f"({window['control_floor_max_guarded_control_drop']:.4f}, "
                f"{window['cap']:.4f}] is "
                + str(window.get("underpowered_reason") or "EMPTY")
                + "; the gate's floor is the maximum of a high-variance "
                  "nuisance statistic and a true effect would land inside it "
                  "partly by luck, so the preregistered outcome is a declared "
                  "VACUOUS rather than an over-readable FAIL")
            return res

    res["beats_matched_and_cross_controls"] = bool(
        (drop > max(ctrl_drops)) and (drop > cross_drop)
        and paired["both_arms_hold"] and (p_ctrl < CONTROL_PERM_ALPHA))
    res["selectivity_gate_holds"] = bool(
        (d_target > 0)
        and (abs(d_xrail) <= SELECTIVITY_MAX_RATIO * d_target))
    return res


def eval_dr_test(base, tgt, ctrls, cross, tau, base_other, xrail, key, okey,
                 readout=DR_PRIMARY_READOUT, min_ctrl=CONTROLS_MIN_STRICT,
                 quantum=DTYPE_RELATIVE_QUANTUM[DEFAULT_DTYPE],
                 magnitude_meta=None, n_averaged=1, strict_gates=True):
    """DR starvation with gated cross-rail selectivity (rev 0.4 controls)."""
    readout = _resolve_readout(readout, key)
    res = _drive_common(base, tgt, ctrls, cross, tau, base_other, xrail,
                        key, okey, readout, min_ctrl, quantum, magnitude_meta,
                        cap_mode="none", n_averaged=n_averaged,
                        strict_gates=strict_gates)
    res["cross_cover_drop"] = float(
        readout_vals(base, readout).mean() - readout_vals(cross, readout).mean())
    if "status" in res:
        return res
    proj_b = readout_vals(base, key)
    proj_t = readout_vals(tgt, key)
    starves = rate_above(proj_t, tau) < DR_PRESENCE_COLLAPSE * rate_above(proj_b, tau)
    res["starvation_signature_holds"] = bool(starves)
    res["status"] = "PASS" if (res["beats_matched_and_cross_controls"]
                               and starves
                               and res["selectivity_gate_holds"]) else "FAIL"
    return res


def eval_amp_test(base, tgt, ctrls, cross, tau, base_other, xrail, key, okey,
                  readout=AMP_PRIMARY_READOUT, min_ctrl=CONTROLS_MIN_STRICT,
                  quantum=DTYPE_RELATIVE_QUANTUM[DEFAULT_DTYPE],
                  magnitude_meta=None, readout_viability=None, n_averaged=1,
                  strict_gates=True):
    """AMP attenuation: magnitude shrinks, presence retained, selectivity gated.

    REV 0.4 HEADLINE TEST. Rev 0.3's AMP_F5 FAILED on SELECTIVITY, not power
    (drop 0.366 at p = 5.5e-05, but max matched-control drop 0.977 and
    control_ensemble_p 0.16). Both failing legs ran through a control family
    that was, uniquely in the battery, neither orthogonalized against the
    target nor dose-matched to it -- and through a readout that was 78.7% dead
    offset. D35 (readout), D37 (orthogonalization), D38 (dose), D39 (damage
    guard) and D41 (pass window) all land here.
    """
    readout = _resolve_readout(readout, key)
    res = _drive_common(
        base, tgt, ctrls, cross, tau, base_other, xrail, key, okey, readout,
        min_ctrl, quantum, magnitude_meta,
        cap_mode=("readout_floor" if readout == "probe_p"
                  else "presence_retention"),
        readout_viability=readout_viability, n_averaged=n_averaged,
        strict_gates=strict_gates)
    res["cross_direction_drop"] = float(
        readout_vals(base, readout).mean() - readout_vals(cross, readout).mean())
    if "status" in res:
        return res
    proj_b = readout_vals(base, key)
    proj_t = readout_vals(tgt, key)
    retains = rate_above(proj_t, tau) >= AMP_PRESENCE_RETAIN * rate_above(proj_b, tau)
    res["attenuation_signature_holds"] = bool(retains)
    res["status"] = "PASS" if (res["beats_matched_and_cross_controls"]
                               and retains
                               and res["selectivity_gate_holds"]) else "FAIL"
    return res


def eval_rs_test(pre, base_con, tgt, ctrls, ref_lic, key,
                 pre_judge=None, ctrl_meta=None, target_magnitude=None,
                 min_ctrl=CONTROLS_MIN_STRICT,
                 quantum=DTYPE_RELATIVE_QUANTUM[DEFAULT_DTYPE],
                 n_averaged=1, strict_gates=True):
    """RS-F5 rev 0.3/0.4: the increase-sign anchor, redesigned.

    Precondition: the teacher-forced suppression-gap gates G1 AND G2 (`pre`).
    If they do not hold, the model has no measurable brake on this bank and the
    test is VACUOUS_NO_BRAKE (informative, not an unreachable threshold).

    Judgment (all on the clean re-forward of generated text):
      M1 INCREASE-SIGN.  Removing u_RS on the CONFLICTED judge prompts raises
         the clean u_F5 projection vs the unablated conflicted baseline, beats
         EVERY matched PC-subspace control increase (control-ensemble p), and
         is significant paired (Wilcoxon-Pratt).
      M2 BOUNDED RESTORATION.  rho = (target - conflicted) / (licensed -
         conflicted) must lie in (0, 1.5]. The unablated LICENSED condition
         supplies the unsuppressed ceiling: release-of-restraint moves TOWARD
         the licensed level; generic damage moves arbitrarily.
      M3 MASS-SIGN.  Hedge probability MASS on the ablated continuations DROPS
         vs baseline, beats every control drop, and beats the change in the
         frequency/POS-matched control lexicon (so "the hedge lexicon moved"
         cannot be satisfied by "every lexicon moved").
    PASS iff M1 and M2 and M3 and the coherence and repetition guards.

    HONESTY NOTE carried into the report: the rev-0.2 claim that "generic
    damage cannot fake the increase sign" was empirically FALSE as implemented
    -- random PC-subspace erasers produced increases 5x larger than the
    targeted direction. The anti-fake property comes from beating matched
    controls PLUS the licensed-reference ceiling PLUS adequate n and decode
    variance control, never from the sign alone.
    """
    # REV 0.4 (deviation D39): the GATING ensemble is the damage-guarded one.
    guarded, guard_info = guard_controls(ctrls, base_texts=base_con["texts"])
    gate_ctrls = guarded or ctrls
    b = np.asarray(base_con["proj"][key])
    t = np.asarray(tgt["proj"][key])
    r = np.asarray(ref_lic["proj"][key])
    inc = float(t.mean() - b.mean())
    ctrl_incs = [float(np.mean(c["proj"][key]) - b.mean()) for c in gate_ctrls]
    ctrl_incs_all = [float(np.mean(c["proj"][key]) - b.mean()) for c in ctrls]
    paired = _paired_block(base_con, tgt, gate_ctrls, key, sign=-1)
    p_w = paired["p_vs_control_mean"]
    w_stats = paired["stats_vs_control_mean"]
    p_ctrl = control_ensemble_p(inc, ctrl_incs)
    change = behavioral_change_rate(base_con["texts"], tgt["texts"])

    headroom = float(r.mean() - b.mean())
    rho = float(inc / headroom) if abs(headroom) > 1e-12 else float("nan")

    # M3 on NORMALIZED (log-ratio) mass change, not raw probability mass
    # (rev 0.3 review fix D26). The hedge lexicon sits around 3e-3 while the
    # control lexicon contains very high-frequency items ("must", "later",
    # "finally"); comparing RAW drops lets a 5% relative shift in the larger
    # lexicon beat a 30% relative shift in the smaller one, which can mask a
    # real hedge-specific drop or manufacture a spurious failure for pure scale
    # reasons. Both absolute baselines are reported so the scales are visible.
    eps = 1e-12

    def _lr(x0, x1):
        return float(math.log((float(x0) + eps) / (float(x1) + eps)))

    hm_b = mean_mass(base_con, "hedge")
    hm_t = mean_mass(tgt, "hedge")
    mass_drop = float(hm_b - hm_t)
    mass_lr = _lr(hm_b, hm_t)
    ctrl_mass_drops = [float(hm_b - mean_mass(c, "hedge")) for c in gate_ctrls]
    ctrl_mass_lrs = [_lr(hm_b, mean_mass(c, "hedge")) for c in gate_ctrls]
    lex_b = mean_mass(base_con, "control_lex")
    lex_t = mean_mass(tgt, "control_lex")
    lex_drop = float(lex_b - lex_t)
    lex_lr = _lr(lex_b, lex_t)
    p_ctrl_mass = control_ensemble_p(mass_lr, ctrl_mass_lrs)

    res = {
        "precondition": pre,
        "precondition_scope": (
            "GATING gates G1/G2 are computed on the RS FIT half (rev 0.3 "
            "review fix D27). The rev-0.3 draft gated on the JUDGE half, which "
            "is the same bank that supplies M2's denominator (licensed minus "
            "conflicted), so conditioning on G1 made M2's headroom>0 component "
            "close to automatic and biased rho downward into the pass window. "
            "Feasibility of the brake is a property of model+bank, so it "
            "belongs on the fit half; the judge half is reported unconditioned."),
        "precondition_judge_half_descriptive_only": pre_judge,
        "control_families": ctrl_meta,
        "target_perturbation_magnitude": target_magnitude,
        "mass_criterion": (
            "log-ratio log(mass_baseline/mass_target), compared against the "
            "same log-ratio on the frequency/POS-matched control lexicon and "
            "against the control-direction ensemble"),
        "hedge_mass_log_ratio": mass_lr,
        "control_lexicon_mass_log_ratio": lex_lr,
        "control_direction_hedge_mass_log_ratios": ctrl_mass_lrs,
        "baseline_control_lexicon_mass": lex_b,
        "paired_arms": paired,
        "baseline_conflicted_mean_proj": float(b.mean()),
        "licensed_reference_mean_proj": float(r.mean()),
        "target_mean_proj": float(t.mean()),
        "targeted_increase": inc,
        "matched_control_increases": ctrl_incs,
        "max_matched_control_increase": float(max(ctrl_incs)) if ctrl_incs else 0.0,
        "matched_control_increases_unguarded_reported_only": ctrl_incs_all,
        "control_ensemble_p_unguarded_reported_only": control_ensemble_p(
            inc, ctrl_incs_all),
        "control_guard": guard_info,
        "n_controls_drawn": len(ctrls),
        "n_controls_gating": len(guarded),
        "measurability": measurability(
            inc, float(b.mean()), quantum, n_averaged=n_averaged,
            standard_error=(float(b.std(ddof=1) / math.sqrt(b.size))
                            if b.size > 1 else None)),
        "measurability_mass": measurability(mass_drop, hm_b, quantum,
                                            n_averaged=n_averaged),
        "dose_gate": dose_gate(ctrl_meta, len(guarded))[1],
        "wilcoxon_pratt_p": p_w,
        "wilcoxon_pratt_stats": w_stats,
        "control_ensemble_p": p_ctrl,
        "n_controls": len(ctrls),
        "legacy_sign_test_p_reported_only": sign_test_p(
            paired["diffs_vs_control_mean"]),
        "behavioral_change_rate": change,
        "restoration_headroom_licensed_minus_conflicted": headroom,
        "restoration_fraction_rho": rho,
        "rho_bounds": [RS_RHO_MIN, RS_RHO_MAX],
        "baseline_hedge_mass": hm_b,
        "target_hedge_mass": hm_t,
        "targeted_hedge_mass_drop": mass_drop,
        "matched_control_hedge_mass_drops": ctrl_mass_drops,
        "control_lexicon_mass_drop": lex_drop,
        "control_ensemble_p_mass": p_ctrl_mass,
        "baseline_mean_hedge_word_count_descriptive": base_con["mean_hedge"],
        "target_mean_hedge_word_count_descriptive": tgt["mean_hedge"],
        "coherence_target": tgt["coherence"],
        "repetition_target": tgt["repetition"],
        "sample_texts_target": tgt["sample_texts"],
        "note": ("hedge WORD COUNT is descriptive only in rev 0.3; the gating "
                 "observable is hedge probability MASS on the clean re-forward"),
    }
    if not pre.get("holds"):
        res["status"] = "VACUOUS_NO_BRAKE"
        res["reason"] = ("teacher-forced suppression-gap precondition not met "
                         f"(G1 {pre.get('G1_holds')}, G2 {pre.get('G2_holds')}): "
                         "this model shows no measurable agency suppression "
                         "under conflict on this bank, so there is no brake to "
                         "remove and its removal predicts no change")
        return res
    if change < BEHAVIORAL_CHANGE_MIN:
        res["status"] = "VACUOUS_NO_BEHAVIORAL_CHANGE"
        res["reason"] = (f"only {change:.2f} of judge prompts changed text under "
                         f"u_RS removal (< {BEHAVIORAL_CHANGE_MIN})")
        return res
    if tgt["coherence"] < COHERENCE_MIN or tgt["repetition"] < REPETITION_MIN:
        res["status"] = "CONFOUNDED"
        res["reason"] = ("target condition failed the coherence and/or "
                         "repetition guard (fluency / degenerate-loop confound)")
        return res
    if len(guarded) < min_ctrl:
        res["status"] = "VACUOUS_CONTROL_ENSEMBLE_DEGRADED"
        res["reason"] = (
            f"only {len(guarded)} of {len(ctrls)} control directions cleared "
            f"the target's own coherence/repetition guards, below the required "
            f"{min_ctrl}")
        return res
    if strict_gates and not res["dose_gate"]["holds"]:
        res["status"] = "VACUOUS_DOSE_UNMATCHED"
        res["reason"] = (
            "the RS control ensemble could not be brought into the target's "
            f"dose band (D47): {res['dose_gate']}. Rev 0.3 measured "
            "target_over_control_mean_magnitude_ratio 0.3983 here -- the "
            "controls were 2.5x STRONGER perturbations than the target -- which "
            "made that FAIL unreadable under PREREG's own binding rule. Rev 0.4 "
            "stamps the unreadability instead of reporting a verdict")
        return res
    if (strict_gates and res["measurability"] is not None
            and res["measurability"].get('below_dtype_quantization_floor')):
        res["status"] = "VACUOUS_BELOW_INSTRUMENT_RESOLUTION"
        res["reason"] = (
            "the targeted increase is at or below the effective dtype "
            "quantization floor; D42 is GATING for PASS in rev 0.4's second "
            "pass, so the anchor test may not PASS on an observable the "
            "artifact declares unresolvable")
        return res
    m1 = (inc > 0.0 and (not ctrl_incs or inc > max(ctrl_incs))
          and paired["both_arms_hold"] and p_ctrl < CONTROL_PERM_ALPHA)
    m2 = (headroom > 0.0 and rho == rho
          and RS_RHO_MIN < rho <= RS_RHO_MAX)
    m3 = (mass_lr > 0.0
          and (not ctrl_mass_lrs or mass_lr > max(ctrl_mass_lrs))
          and mass_lr > lex_lr
          and p_ctrl_mass < CONTROL_PERM_ALPHA)
    res["M1_increase_sign_holds"] = bool(m1)
    res["M2_bounded_restoration_holds"] = bool(m2)
    res["M3_mass_sign_holds"] = bool(m3)
    res["status"] = "PASS" if (m1 and m2 and m3) else "FAIL"
    return res


def eval_conn_test(base, tgt, ctrls, key, okey, rand_keys,
                   min_ctrl=CONTROLS_MIN_STRICT,
                   quantum=DTYPE_RELATIVE_QUANTUM[DEFAULT_DTYPE],
                   n_averaged=1, strict_gates=True):
    """CONN: upstream DR-F5 cut selectively starves the downstream AMP site.

    REV 0.4 (deviation D39): the gating cover-control ensemble is the
    DAMAGE-GUARDED one, exactly as for DR and AMP. The PREREG's own reading
    rule was scoped to one test in rev 0.3; rev 0.4 generalizes it to the whole
    battery rather than adding a second per-test exception.
    """
    guarded, guard_info = guard_controls(ctrls, base_texts=base["texts"])
    d_target = effect_size(base["proj"][key], tgt["proj"][key])
    d_other = effect_size(base["proj"][okey], tgt["proj"][okey])
    d_rand = [effect_size(base["proj"][rk], tgt["proj"][rk]) for rk in rand_keys]
    d_ctrl_covers = [effect_size(base["proj"][key], c["proj"][key])
                     for c in guarded]
    d_ctrl_all = [effect_size(base["proj"][key], c["proj"][key]) for c in ctrls]
    paired = _paired_block(base, tgt, guarded or ctrls, key, sign=+1)
    p_w = paired["p_vs_control_mean"]
    w_stats = paired["stats_vs_control_mean"]
    p_ctrl = control_ensemble_p(d_target, d_ctrl_covers)
    change = behavioral_change_rate(base["texts"], tgt["texts"])
    res = {
        "effect_size_uF5_downstream": d_target,
        "effect_size_uF2_downstream": d_other,
        "effect_sizes_random_dirs_downstream": d_rand,
        "max_random_dir_effect": float(max(d_rand)) if d_rand else 0.0,
        "effect_sizes_matched_cover_controls": d_ctrl_covers,
        "max_matched_cover_effect": (float(max(d_ctrl_covers))
                                     if d_ctrl_covers else 0.0),
        "effect_sizes_matched_cover_controls_unguarded_reported_only": d_ctrl_all,
        "control_guard": guard_info,
        "n_controls_drawn": len(ctrls),
        "n_controls_gating": len(guarded),
        "wilcoxon_pratt_p": p_w,
        "wilcoxon_pratt_stats": w_stats,
        "control_ensemble_p": p_ctrl,
        "control_ensemble_p_unguarded_reported_only": control_ensemble_p(
            d_target, d_ctrl_all),
        "paired_arms": paired,
        "legacy_sign_test_p_reported_only": sign_test_p(
            paired["diffs_vs_control_mean"]),
        "behavioral_change_rate": change,
        "measurability": measurability(
            float(np.mean(base["proj"][key]) - np.mean(tgt["proj"][key])),
            float(np.mean(base["proj"][key])), quantum,
            n_averaged=n_averaged,
            standard_error=(
                float(np.std(base["proj"][key], ddof=1)
                      / math.sqrt(len(base["proj"][key])))
                if len(base["proj"][key]) > 1 else None)),
        "note": ("clean-pass only; correlated with DR-F5 (shared bank and "
                 "direction) -- counted with that caveat in the aggregate"),
    }
    if change < BEHAVIORAL_CHANGE_MIN:
        res["status"] = "VACUOUS_NO_BEHAVIORAL_CHANGE"
        res["reason"] = (f"only {change:.2f} of judge prompts changed text under "
                         f"the upstream cut (< {BEHAVIORAL_CHANGE_MIN})")
        return res
    if len(guarded) < min_ctrl:
        res["status"] = "VACUOUS_CONTROL_ENSEMBLE_DEGRADED"
        res["reason"] = (
            f"only {len(guarded)} of {len(ctrls)} cover controls cleared the "
            f"coherence/repetition guards, below the required {min_ctrl}")
        return res
    if (strict_gates and res["measurability"] is not None
            and res["measurability"].get('below_dtype_quantization_floor')):
        res["status"] = "VACUOUS_BELOW_INSTRUMENT_RESOLUTION"
        res["reason"] = ("the downstream effect is at or below the effective "
                         "dtype quantization floor; D42 is GATING for PASS in "
                         "rev 0.4's second pass")
        return res
    ok = (d_target > CONN_MIN_EFFECT
          and (not d_rand or d_target > max(d_rand))
          and d_target > d_other
          and (not d_ctrl_covers or d_target > max(d_ctrl_covers))
          and paired["both_arms_hold"]
          and p_ctrl < CONTROL_PERM_ALPHA)
    res["status"] = "PASS" if ok else "FAIL"
    return res


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args():
    ap = argparse.ArgumentParser(description="COMPONENT ATLAS v0 (rev 0.4)")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--revision", default=None,
                    help=("HF revision; defaults to the pinned revision for "
                          "known models. NO pin exists for "
                          "EleutherAI/gpt-neox-20b (the validated Stage-9 40E "
                          "chain recorded model_revision: null and the "
                          "standing rule forbids inventing one), so a "
                          "confirmatory rev-0.4 run must pass an explicit "
                          "40-hex commit or abort as ABORT_UNPINNED_REVISION"))
    ap.add_argument("--allow-unpinned", action="store_true",
                    help=("opt out of the unpinned-revision hard abort. Stamps "
                          "claim_eligible=False and is loudly warned; not the "
                          "preregistered mode"))
    ap.add_argument("--dtype", choices=list(DTYPE_CHOICES), default=DEFAULT_DTYPE,
                    help=("weight dtype (rev 0.4 deviation D33). bfloat16 is "
                          "the declared rev-0.4 default because fp32 at 20B is "
                          "76.74 GiB against an A40's 44.99 GiB. Measurement "
                          "math is forced to fp32 regardless. Use "
                          "--dtype float32 for the D34 pythia-2.8b calibration "
                          "arm."))
    ap.add_argument("--no-device-map", dest="device_map", action="store_false",
                    default=True,
                    help=("do NOT dispatch with accelerate device_map={'':0}. "
                          "The default (device_map ON) streams shards straight "
                          "to GPU; without it a 20B load stages ~38.4 GiB in "
                          "host RAM first and can OOM the container before "
                          "VRAM is ever touched."))
    ap.add_argument("--run-dr-f2", action="store_true",
                    help=("run the DR-F2 contrast RAIL as a test. OFF by "
                          "default in rev 0.4 (deviation D40): at rev 0.3 it "
                          "was the weakest test in the battery (behavioural "
                          "change 0.313, targeted drop 0.00132) and its "
                          "relative effect is ~48x BELOW the bf16 quantum, so "
                          "it cannot be measured at 20B in bf16 no matter how "
                          "much time it is given. The DR-F2 COVER is still "
                          "computed, so DR-F5's cross-cover control and both "
                          "cross-rail selectivity conditions are unaffected."))
    ap.add_argument("--smoke", action="store_true",
                    help="tiny mechanical run; never evidence")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--device", default=None)
    ap.add_argument("--out", default=None, help="output directory")
    ap.add_argument("--max-new-tokens", type=int, default=32)
    ap.add_argument("--controls", type=int, default=CONTROLS_DRAW_DEFAULT,
                    help=("matched control trials DRAWN per test. The "
                          "control-ensemble p floor is 1/(C+1) and the "
                          "criterion is STRICT (< alpha), so at least "
                          f"{CONTROLS_MIN_STRICT} controls must SURVIVE the D39 "
                          "damage guard (C=19 gives exactly 0.0500, which is "
                          "NOT < 0.05). Rev 0.4's first draft drew exactly 20 "
                          "AND required 20 survivors, leaving the guard zero "
                          "slack: at rev 0.3's observed ~1-in-24 degraded-draw "
                          "rate that is a ~57% chance of a spurious "
                          "VACUOUS_CONTROL_ENSEMBLE_DEGRADED per test. Rev 0.4 "
                          f"therefore DRAWS {CONTROLS_DRAW_DEFAULT} and GATES "
                          f"on {CONTROLS_MIN_STRICT} survivors (deviation "
                          "D46)."))
    ap.add_argument("--run-rs", action="store_true",
                    help=("run the RS-F5 sign-anchor test. OFF by default in "
                          "rev 0.4's second pass (deviation D48): RS is 1,944 "
                          "of 3,864 units (50% of the battery) on an observable "
                          "whose G2 hedge-mass gate operates at 1.7% relative "
                          "while bf16 logits inject ~6% multiplicative error "
                          "per softmax probability (true SNR ~0.28), and which "
                          "already returned VACUOUS_NO_BRAKE in fp32 at 2.8b. "
                          "With RS on, the confirmatory run lands at ~4.0 h "
                          "BEFORE the D34 calibration and the 20B preflight, "
                          "i.e. over the window. Turning it on is itself a "
                          "deviation to be logged, and the verdict label "
                          "changes (see PREREG section 8)."))
    ap.add_argument("--dr-engagement-step", action="store_true",
                    help=("apply the ONE bounded, preregistered DR-engagement "
                          f"step (COVER_K_FRAC {COVER_K_FRAC} -> "
                          f"{COVER_K_FRAC_STEP2}), authorised in advance by "
                          "deviation D50 and usable ONLY after a LOGGED 20B "
                          "--preflight NO-GO on DR-F5. No ladder: exactly one "
                          "step, and if the re-run preflight still fails, the "
                          "confirmatory pass is NOT launched as a battery (see "
                          "PREREG section 8's stop rule)."))
    ap.add_argument("--rs-samples", type=int, default=RS_N_SAMPLES,
                    help="seeded sampled continuations per RS prompt (variance control)")
    # --local-files-only is now the DEFAULT (PREREG section 1 calls it "the
    # intended mode": without it a pin that is not the cached snapshot can be
    # silently DOWNLOADED as a different commit instead of failing loudly).
    ap.add_argument("--local-files-only", dest="local_files_only",
                    action="store_true", default=True,
                    help="default TRUE; kept for explicitness/back-compat")
    ap.add_argument("--allow-download", dest="local_files_only",
                    action="store_false",
                    help="OPT OUT of local-files-only (loudly warned; not the "
                         "preregistered mode)")
    ap.add_argument("--preflight", action="store_true",
                    help=("go/no-go preflight declared IN ADVANCE (PREREG "
                          "section 1): discovery + behavioural-change rates for "
                          "DR-F5 / AMP-F5 / RS on a handful of judge prompts, "
                          "then exit. ~5 min. Not evidence; it reads no test "
                          "statistic, only whether the interventions change "
                          "text at all."))
    ap.add_argument("--preflight-prompts", type=int, default=6)
    return ap.parse_args()


def write_report(report, report_path):
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=_json_default)


def _unit_budget(n_judge, n_fit, n_rs_judge, n_controls, rs_samples, run_dr_f2,
                 run_rs=False):
    """Closed-form generation-unit arithmetic for the battery (D40).

    One UNIT is one prompt generated once under one condition. The rev-0.3
    battery was 5,864 units and took 4565.5 s on one A40 at pythia-2.8b fp32
    (0.7786 s/unit all-in). At 20B in bf16 the batch-1 autoregressive decode is
    memory-bandwidth-bound, so the correct scalar is the BYTES-READ ratio
    41.20/11.10 = 3.712x, NOT the parameter ratio 7.42x; that gives ~3.08
    s/unit, which agrees within 2.6% with a first-principles bandwidth estimate.
    """
    baselines_judge = 3 * n_judge          # F5 / F2 / neutral judge banks
    baselines_fit = 3 * n_fit              # NEW in rev 0.4: readout-probe fit
    dr_f5 = n_judge * (1 + n_controls)
    shared_cross = 2 * n_judge             # cross-cover + cross-rail, shared
    amp_f5 = n_judge * (1 + n_controls + 2)
    dr_f2 = n_judge * (1 + n_controls) if run_dr_f2 else 0
    rs = rs_samples * n_rs_judge * (3 + n_controls) if run_rs else 0
    total = (baselines_judge + baselines_fit + dr_f5 + shared_cross
             + amp_f5 + dr_f2 + rs)
    return {
        "formula": ("3N_judge + 3N_fit + N(1+C) [DR-F5] + 2N [shared cross] + "
                    "N(3+C) [AMP-F5] + N(1+C) [DR-F2, optional] + "
                    "K*R*(3+C) [RS, optional]"),
        "battery": ("F5 rail only (DR-F5 + AMP-F5 + CONN)" if not (run_rs or run_dr_f2)
                    else "F5 rail + optional arms"),
        "run_rs": bool(run_rs),
        "run_dr_f2": bool(run_dr_f2),
        "baselines_judge": baselines_judge,
        "baselines_fit_for_readout_probe": baselines_fit,
        "DR_F5": dr_f5,
        "shared_cross_conditions": shared_cross,
        "AMP_F5": amp_f5,
        "DR_F2": dr_f2,
        "RS_F5": rs,
        "total_units": total,
        "rev03_reference": {
            "total_units": 5864,
            "measured_seconds_per_unit_pythia_2_8b_fp32_A40": 0.7786,
            "measured_runtime_seconds": 4565.5},
        "projected_seconds_per_unit_20b_bf16_A40": 3.08,
        "projected_generation_hours": round(total * 3.08 / 3600.0, 2),
        "projected_fixed_overhead_hours": 0.68,
        "projected_total_hours": round(total * 3.08 / 3600.0 + 0.68, 2),
        "scaling_note": ("s/unit is scaled by BYTES READ per forward "
                         "(20.6e9 x 2 B = 41.20 GB vs 2.775e9 x 4 B = 11.10 "
                         "GB, ratio 3.712x), not by the parameter ratio "
                         "7.423x: at batch 1 decode is bandwidth-bound. This "
                         "estimate carries roughly +/-25% uncertainty; the "
                         "rev-0.3 prior estimate was 41% pessimistic."),
    }


def derive_layer_params(n_blocks, n_heads):
    """Depth/width-FRACTION resolution of the rev-0.2 absolute constants.

    At n_blocks=16 this returns sweep_lo=4, L_star_min=6, dr_offset=4 and (with
    n_heads=8) topk_heads=4 -- bit-identical to rev 0.2. At 32 blocks x 32
    heads it returns 8 / 12 / 8 / 31, preserving the RELATIVE geometry the
    design was built on (DR sits 25% of depth upstream of AMP, not 12.5%).
    """
    # D56: lower bounds are now absolute (full-depth sweep), not fractions.
    sweep_lo = LAYER_SWEEP_MIN_ABS
    l_star_min = L_STAR_MIN_ABS
    l_star_max = min(n_blocks - 2,
                     max(l_star_min, int(round(L_STAR_MAX_FRAC * n_blocks))))
    dr_offset = max(1, int(round(DR_OFFSET_FRAC * n_blocks)))
    topk = max(TOPK_HEADS_MIN, int(round(TOPK_HEADS_FRAC * n_blocks * n_heads)))
    return sweep_lo, l_star_min, l_star_max, dr_offset, topk


def derive_cover_k(intermediate, frac=COVER_K_FRAC):
    """COVER_K as a FRACTION of the MLP intermediate width (rev 0.3, D20).

    8192 -> 32 (bit-identical to rev 0.2's literal "Top-32"); 10240 -> 40. The
    rev-0.3 draft left COVER_K absolute at 32, which would have made the DR
    rail cut 0.31% of the layer at pythia-2.8b against 0.39% at pythia-1b -- a
    20% relative WEAKENING of the one intervention whose rev-0.2 behavioural
    change rate (~0.50) was already below the new 0.60 precondition.
    """
    return max(COVER_K_MIN, int(round(float(frac) * int(intermediate))))


def cache_safetensors_status(model_id, revision, local_files_only):
    """Codified preflight for the safetensors-vs-.bin cache trap (D53).

    Under --local-files-only (the default) `use_safetensors=True` HARD-FAILS at
    load if the pod cache holds only the .bin shards. PREREG rev 0.4 called this
    "a gating step, not code", which costs a full pod session for a 5-minute
    check the script already codifies comparable versions of. Best-effort and
    NEVER fatal by itself: if the cache layout cannot be determined the status
    is 'unavailable' and the run proceeds to the real load, which is still the
    loud and recoverable failure.
    """
    info = {"model": model_id, "revision": revision,
            "local_files_only": bool(local_files_only),
            "status": "unavailable", "snapshot_dir": None,
            "n_safetensors": None, "n_bin": None}
    try:
        root = (os.environ.get("HF_HUB_CACHE")
                or os.path.join(os.environ.get("HF_HOME",
                                               os.path.expanduser("~/.cache/huggingface")),
                                "hub"))
        repo = "models--" + str(model_id).replace("/", "--")
        snaps = os.path.join(root, repo, "snapshots")
        if not os.path.isdir(snaps):
            info["status"] = "NO_SNAPSHOT_DIR"
            info["searched"] = snaps
            return info
        cands = ([os.path.join(snaps, revision)]
                 if revision and os.path.isdir(os.path.join(snaps, revision))
                 else sorted(glob.glob(os.path.join(snaps, "*"))))
        for d in cands:
            st = glob.glob(os.path.join(d, "*.safetensors"))
            bn = glob.glob(os.path.join(d, "*.bin"))
            if st or bn:
                info.update({"snapshot_dir": d, "n_safetensors": len(st),
                             "n_bin": len(bn),
                             "status": ("OK_SAFETENSORS" if st
                                        else "ONLY_BIN_SHARDS")})
                break
    except Exception:  # pragma: no cover - diagnostics must never abort a run
        info["status"] = "unavailable"
    return info


def main():
    args = parse_args()
    t0 = time.time()
    stage_times = {}

    def stage_mark(name):
        stage_times[name] = round(time.time() - t0, 1)
        if torch.cuda.is_available():
            try:
                torch.cuda.empty_cache()
            except Exception:  # pragma: no cover
                pass

    def peak_vram_gib():
        """REV 0.4 (deviation D43). No measured VRAM figure exists anywhere in
        the 20B record -- only the GPU model. That gap is closed here."""
        if not torch.cuda.is_available():
            return None
        try:
            return {
                "max_memory_allocated_gib": float(
                    torch.cuda.max_memory_allocated() / (1024 ** 3)),
                "max_memory_reserved_gib": float(
                    torch.cuda.max_memory_reserved() / (1024 ** 3)),
            }
        except Exception:  # pragma: no cover
            return None

    # PYTORCH_CUDA_ALLOC_CONF is set at MODULE IMPORT time (see the import
    # block) so that no import side effect can initialize the CUDA caching
    # allocator ahead of it. Recorded here for the artifact.
    alloc_conf = os.environ.get("PYTORCH_CUDA_ALLOC_CONF")

    device = args.device or ("cuda" if torch.cuda.is_available() else "cpu")
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    # Pin every reduced-precision shortcut OFF (rev 0.4, deviation D33). tf32
    # was already pinned in rev 0.3; bf16/fp16 REDUCED-PRECISION REDUCTION
    # defaults to TRUE in PyTorch and is the single highest-value one-line
    # change in the whole bf16 budget -- without it a bf16 matmul may
    # accumulate in bf16 and a 0.366-sized drop on a 10.7 baseline is gone.
    precision_flags = pin_precision_backends()
    quantum = DTYPE_RELATIVE_QUANTUM[args.dtype]

    revision = args.revision or PINNED_REVISIONS.get(args.model)
    claim_eligible = bool(revision) and not args.smoke
    if not revision:
        print(f"[warn] no pinned revision for {args.model}; claim_eligible=False (fail-closed)")
    if not args.local_files_only:
        print("[warn] --allow-download: NOT the preregistered mode. A pin that "
              "is not the cached snapshot can now be silently downloaded as a "
              "different commit instead of failing loudly.")

    out_dir = args.out or os.path.dirname(os.path.abspath(__file__))
    os.makedirs(out_dir, exist_ok=True)
    # D54: the report filename carries the MODEL when it is not the rev-0.4
    # default. The D34 calibration runs this same script on pythia-2.8b, and the
    # rev-0.4 first draft's docstring command would have overwritten the 20B
    # rev-0.4 report if --out was omitted. The "never overwritten" guarantee
    # previously covered only the rev-0.2 and rev-0.3 filenames.
    def _named(base):
        if args.model == DEFAULT_MODEL:
            return base
        tag = re.sub(r"[^A-Za-z0-9._-]+", "-", str(args.model).split("/")[-1])
        stem, ext = os.path.splitext(base)
        return f"{stem}__{tag}{ext}"

    report_path = os.path.join(out_dir, _named(REPORT_FILENAME))
    if args.preflight:
        report_path = os.path.join(out_dir, _named(PREFLIGHT_FILENAME))
    if args.model != DEFAULT_MODEL:
        print(f"[info] non-default model: writing {os.path.basename(report_path)} "
              "so the 20B rev-0.4 artifact can never be overwritten")

    # ---- Fail-closed on an unpinned revision (rev 0.4, deviation D32) ----
    # Rev 0.3 fail-closed only by stamping claim_eligible=False, which still
    # burned the full run. gpt-neox-20b has NO recorded pin anywhere -- the
    # validated Stage-9 40E chain recorded model_revision: null -- so a strict
    # reviewer can challenge the entire 20B chain on checkpoint identity alone.
    # Rev 0.4 refuses to spend pod time on an unidentifiable checkpoint.
    if (not revision) and (not args.smoke) and (not args.allow_unpinned):
        print(f"[abort] no revision pin for {args.model}. Resolve the exact "
              "commit from the pod HF cache and pass --revision <40-hex>, or "
              "pass --allow-unpinned to proceed with claim_eligible=False.")
        write_report({
            "schema_version": SCHEMA_VERSION,
            "frame": FRAME, "boundary": BOUNDARY,
            "rev04_provenance_note": REV04_PROVENANCE_NOTE,
            "aggregate": {
                "status": "ABORT_UNPINNED_REVISION",
                "model": args.model,
                "reason": ("no pinned revision is recorded for this model and "
                           "none was supplied; the checkpoint identity would "
                           "not be cryptographically fixed, which is the one "
                           "reproducibility gap the validated 20B 40E run "
                           "already left open (model_revision: null)"),
                "remedy": "--revision <40-hex commit> (or --allow-unpinned)"}},
            report_path)
        return 0
    if (not revision) and args.allow_unpinned:
        print("[warn] --allow-unpinned: the checkpoint identity is NOT fixed; "
              "claim_eligible=False and no claim of any kind is licensed.")

    n_controls = 2 if args.smoke else args.controls
    max_new = 10 if args.smoke else args.max_new_tokens
    n_conn_dirs = 3 if args.smoke else max(n_controls, CONTROLS_MIN_STRICT)
    rs_samples = 2 if args.smoke else max(1, args.rs_samples)
    run_dr_f2 = bool(args.run_dr_f2)
    run_rs = bool(args.run_rs)
    # Smoke draws only 2 controls, so the C>=20 guard and the guarded-ensemble
    # floor must not fire there (smoke can never pass any gate anyway).
    min_ctrl = 1 if args.smoke else CONTROLS_MIN_STRICT
    # The D47/D49/D52 gates are GATING for evidence runs and are DISABLED under
    # --smoke: smoke draws 2 controls and 8 frames, so a dose band, a probe
    # viability floor and a quantization floor would all fire mechanically and
    # short-circuit the very code paths smoke exists to exercise. Smoke can
    # never pass any gate anyway (its control-ensemble p floor is 1/3).
    strict_gates = not args.smoke

    # Control-ensemble floor guard (review MAJOR, extended by D46). The
    # criterion is a STRICT inequality against 1/(C+1); at C=19 the floor is
    # EXACTLY 0.0500, so the documented "reduced fallback --controls 19" would
    # have produced a full-cost run in which every core test was unpassable by
    # arithmetic. D46 adds the SURPLUS requirement: the number DRAWN must exceed
    # the gating floor, or the D39 damage guard has zero slack and a single
    # degraded draw stamps VACUOUS_CONTROL_ENSEMBLE_DEGRADED on a test that had
    # nothing wrong with it. Abort loudly rather than burn hours.
    required_draw = CONTROLS_MIN_STRICT + CONTROL_GUARD_SURPLUS_MIN
    if (not args.smoke) and n_controls < required_draw:
        print(f"[abort] --controls {n_controls} < {required_draw}: the "
              f"control-ensemble p floor 1/(C+1) = {1.0/(n_controls+1):.4f} "
              f"must be strictly below alpha={CONTROL_PERM_ALPHA} on the "
              f"SURVIVING ensemble, which needs >= {CONTROLS_MIN_STRICT} "
              f"survivors plus >= {CONTROL_GUARD_SURPLUS_MIN} of D39 "
              "damage-guard slack.")
        write_report({"schema_version": SCHEMA_VERSION,
                      "aggregate": {
                          "status": "ABORT_CONTROL_FLOOR",
                          "n_controls_drawn": n_controls,
                          "control_ensemble_p_floor": 1.0 / (n_controls + 1),
                          "required_gating_survivors": CONTROLS_MIN_STRICT,
                          "required_draw": required_draw,
                          "reason": ("drawing exactly the gating floor leaves "
                                     "the D39 damage guard zero slack; at rev "
                                     "0.3's observed ~1-in-24 degraded-draw "
                                     "rate that is a ~57% per-test chance of a "
                                     "spurious VACUOUS_CONTROL_ENSEMBLE_"
                                     "DEGRADED (deviation D46)")}},
                     report_path)
        return 0

    # D53: codified safetensors-vs-.bin cache preflight.
    cache_status = cache_safetensors_status(args.model, revision,
                                            args.local_files_only)
    if cache_status.get("status") == "ONLY_BIN_SHARDS" and args.local_files_only:
        print(f"[abort] the cached snapshot {cache_status['snapshot_dir']} holds "
              f"{cache_status['n_bin']} .bin shards and NO .safetensors; "
              "use_safetensors=True under --local-files-only will hard-fail at "
              "load. Fetch the safetensors shards or pass --allow-download.")
        write_report({"schema_version": SCHEMA_VERSION,
                      "aggregate": {"status": "ABORT_CACHE_FORMAT",
                                    "cache": cache_status}}, report_path)
        return 0

    banks = build_banks(args.smoke, args.seed)
    mem_items = MEM_ITEMS[:6] if args.smoke else MEM_ITEMS
    n_seq = 4 if args.smoke else 32

    # Hash the banks ACTUALLY USED (review MINOR): the rev-0.3 draft hashed the
    # full PROMPT_FRAMES/RS_PAIRS even under --smoke, so a smoke report carried
    # a bank sha that did not describe its own banks.
    used_frames = PROMPT_FRAMES[:8] if args.smoke else PROMPT_FRAMES
    used_pairs = RS_PAIRS[:6] if args.smoke else RS_PAIRS
    bank_sha = sha_of({"frames": used_frames, "rs_pairs": used_pairs,
                       "hedged": banks["f5_hedged"], "plain": banks["f5_plain"],
                       "mem": mem_items, "hedge_words": HEDGE_WORDS,
                       "control_words": CONTROL_WORDS,
                       "act_words": ACT_WORDS, "restrain_words": RESTRAIN_WORDS,
                       "fit_idx": banks["fit_idx"],
                       "judge_idx": banks["judge_idx"],
                       "rs_fit_idx": banks["rs_fit_idx"],
                       "rs_judge_idx": banks["rs_judge_idx"],
                       "seed": args.seed})
    verb_audit = slot_verb_audit(used_frames)

    print(f"[load] {args.model} rev={revision} device={device} "
          f"dtype={args.dtype} device_map={args.device_map}")
    if torch.cuda.is_available():
        try:
            torch.cuda.reset_peak_memory_stats()
        except Exception:  # pragma: no cover
            pass
    model, tok, dispatched = load_model_and_tokenizer(
        args.model, revision, device, args.local_files_only,
        dtype_name=args.dtype, use_device_map=args.device_map)
    lm_head_fp32 = promote_lm_head_fp32(model) if args.dtype != "float32" else {
        "status": "NOT_NEEDED_FP32_WEIGHTS"}
    vram_after_load = peak_vram_gib()
    stage_mark("load")
    layers = locate_layers(model)
    n_blocks = len(layers)
    n_heads = int(model.config.num_attention_heads)
    hidden = int(model.config.hidden_size)
    head_dim = hidden // n_heads
    (sweep_lo, l_star_min, l_star_max, dr_offset,
     topk_heads) = derive_layer_params(n_blocks, n_heads)
    print(f"[arch] blocks={n_blocks} heads/layer={n_heads} hidden={hidden} "
          f"sweep_lo={sweep_lo} L*min={l_star_min} L*max={l_star_max} "
          f"dr_offset={dr_offset} topk_heads={topk_heads}")

    got_sha = resolved_commit_sha(model)
    # revision_verified: distinguishes a VERIFIED pin from an unverifiable one.
    # claim_eligible alone cannot: it is True whenever a revision string is
    # present, including when the runtime reports no commit at all.
    if got_sha is None:
        revision_verified = "unavailable"
    else:
        revision_verified = bool(revision) and (str(got_sha) == str(revision))

    if revision and _SHA40.match(str(revision)) and got_sha and got_sha != revision:
        # Write the FULL provenance block on abort (review MINOR): the rev-0.3
        # draft wrote a stripped record, making the abort itself unauditable.
        print(f"[abort] resolved commit {got_sha} != pinned {revision}")
        write_report({
            "schema_version": SCHEMA_VERSION,
            "frame": FRAME, "boundary": BOUNDARY,
            "rev03_provenance_note": REV03_PROVENANCE_NOTE,
            "rev04_provenance_note": REV04_PROVENANCE_NOTE,
            "provenance": {
                "model": args.model, "revision": revision,
                "dtype": args.dtype,
                "resolved_commit_sha": got_sha,
                "revision_verified": revision_verified,
                "claim_eligible": False, "seed": args.seed, "device": device,
                "smoke": bool(args.smoke), "local_files_only": bool(args.local_files_only),
                "prompt_bank_sha256": bank_sha,
                "slot_verb_audit": verb_audit,
                "architecture": {"n_blocks": n_blocks, "n_heads_per_layer": n_heads,
                                 "hidden": hidden, "head_dim": head_dim,
                                 "total_heads": n_blocks * n_heads},
                "torch": torch.__version__, "numpy": np.__version__,
                "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())},
            "aggregate": {"status": "ABORT_REVISION_MISMATCH",
                          "pinned": revision,
                          "resolved_commit_sha": got_sha}}, report_path)
        return 0
    if got_sha is None:
        print("[warn] runtime did not report a commit hash; recording null "
              "(never filled in by lookup); revision_verified=unavailable")

    cover_k_frac = COVER_K_FRAC_STEP2 if args.dr_engagement_step else COVER_K_FRAC
    if args.dr_engagement_step:
        print(f"[warn] --dr-engagement-step: COVER_K_FRAC {COVER_K_FRAC} -> "
              f"{COVER_K_FRAC_STEP2}. This is the ONE step authorised in "
              "advance by deviation D50 and is legitimate ONLY if a 20B "
              "--preflight NO-GO on DR-F5 was logged in PREREG section 10 "
              "BEFORE this run. No further widening is authorised.")
    config_payload = {
        "schema": SCHEMA_VERSION, "COVER_K_FRAC": cover_k_frac,
        "COVER_K_FRAC_BASE": COVER_K_FRAC,
        "dr_engagement_step": bool(args.dr_engagement_step),
        "dtype": args.dtype, "device_map": bool(args.device_map),
        "run_dr_f2": run_dr_f2, "run_rs": run_rs,
        "CONTROLS_DRAW_DEFAULT": CONTROLS_DRAW_DEFAULT,
        "CONTROL_GUARD_SURPLUS_MIN": CONTROL_GUARD_SURPLUS_MIN,
        "DOSE_MATCHED_MIN_FRAC": DOSE_MATCHED_MIN_FRAC,
        "DOSE_RATIO_LO": DOSE_RATIO_LO, "DOSE_RATIO_HI": DOSE_RATIO_HI,
        "PASS_WINDOW_MIN_ABS_FRAC": PASS_WINDOW_MIN_ABS_FRAC,
        "PROBE_VIABILITY_MIN_SD": PROBE_VIABILITY_MIN_SD,
        "PROBE_VIABILITY_MIN_ACC_OVER_CHANCE":
            PROBE_VIABILITY_MIN_ACC_OVER_CHANCE,
        "MARGIN_TIE_REL_TOL": MARGIN_TIE_REL_TOL,
        "AMP_PRIMARY_READOUT": AMP_PRIMARY_READOUT,
        "DR_PRIMARY_READOUT": DR_PRIMARY_READOUT,
        "READOUT_PROBE_CLASSES": list(READOUT_PROBE_CLASSES),
        "AMP_CTRL_SHUFFLED_FRAC": AMP_CTRL_SHUFFLED_FRAC,
        "DOSE_MATCH_TOL": DOSE_MATCH_TOL,
        "DOSE_MATCH_TRIES": DOSE_MATCH_TRIES,
        "PASS_WINDOW_MIN_SE": PASS_WINDOW_MIN_SE,
        # D56: the LOWER bounds are absolute now; the superseded rev-0.3
        # fractions are still recorded so the change is auditable in-artifact.
        "LAYER_SWEEP_MIN_ABS": LAYER_SWEEP_MIN_ABS,
        "L_STAR_MIN_ABS": L_STAR_MIN_ABS,
        "LAYER_SWEEP_MIN_FRAC_REV03_SUPERSEDED": LAYER_SWEEP_MIN_FRAC_REV03,
        "L_STAR_MIN_FRAC_REV03_SUPERSEDED": L_STAR_MIN_FRAC_REV03,
        "SHALLOW_L_STAR_CAVEAT_FRAC": SHALLOW_L_STAR_CAVEAT_FRAC,
        "L_STAR_MAX_FRAC": L_STAR_MAX_FRAC,
        "DR_OFFSET_FRAC": DR_OFFSET_FRAC,
        "TOPK_HEADS_FRAC": TOPK_HEADS_FRAC, "SIGN_ALPHA": SIGN_ALPHA,
        "CONTROL_PERM_ALPHA": CONTROL_PERM_ALPHA,
        "DR_PRESENCE_COLLAPSE": DR_PRESENCE_COLLAPSE,
        "AMP_PRESENCE_RETAIN": AMP_PRESENCE_RETAIN,
        "BASELINE_PRESENCE_MIN": BASELINE_PRESENCE_MIN,
        "SELECTIVITY_MAX_RATIO": SELECTIVITY_MAX_RATIO,
        "BEHAVIORAL_CHANGE_MIN": BEHAVIORAL_CHANGE_MIN,
        "MEM_BASELINE_MIN": MEM_BASELINE_MIN, "MEM_DROP_MIN": MEM_DROP_MIN,
        "CHECK_GATE_MIN_NATS": CHECK_GATE_MIN_NATS,
        "CHECK_DROP_MIN_NATS": CHECK_DROP_MIN_NATS,
        "COHERENCE_MIN": COHERENCE_MIN, "REPETITION_MIN": REPETITION_MIN,
        "PC_SUBSPACE_K": PC_SUBSPACE_K, "CONN_MIN_EFFECT": CONN_MIN_EFFECT,
        "N_INNER_SPLIT_SEEDS": N_INNER_SPLIT_SEEDS,
        "N_FLOOR_TRIALS": N_FLOOR_TRIALS,
        "RS_RHO_MIN": RS_RHO_MIN, "RS_RHO_MAX": RS_RHO_MAX,
        "RS_TEMPERATURE": RS_TEMPERATURE,
        "RS_CTRL_SHUFFLED_FRAC": RS_CTRL_SHUFFLED_FRAC,
        "CONTROLS_MIN_STRICT": CONTROLS_MIN_STRICT,
        "derived": {"sweep_lo": sweep_lo, "L_STAR_MIN": l_star_min,
                    "L_STAR_MAX": l_star_max,
                    "DR_OFFSET": dr_offset, "topk_heads": topk_heads},
        "runtime_args": {"controls": n_controls, "max_new_tokens": max_new,
                         "rs_samples": rs_samples, "n_conn_dirs": n_conn_dirs,
                         "n_seq": n_seq}}
    # D55: the binding config_sha256 must include the DERIVED cover_k, which is
    # only known after the MLP intermediate width is read from the loaded model.
    # The rev-0.4 first draft hashed the config BEFORE derive_cover_k ran, so
    # PREREG line 10's claim that the sha binds "every DERIVED layer/head
    # parameter actually used" was false for cover_k. The pre-discovery sha is
    # retained so the abort paths (which fire before cover_k exists) stay
    # auditable.
    config_sha_pre = sha_of(config_payload)
    config_sha = config_sha_pre   # rebound after derive_cover_k, below

    hedge_ids, hedge_map = lexicon_token_ids(tok, HEDGE_WORDS)
    ctrl_ids, ctrl_map = lexicon_token_ids(tok, CONTROL_WORDS)
    act_ids, _ = lexicon_token_ids(tok, ACT_WORDS)
    res_ids, _ = lexicon_token_ids(tok, RESTRAIN_WORDS)
    mass_ids = {"hedge": hedge_ids, "control_lex": ctrl_ids}

    report = {
        "schema_version": SCHEMA_VERSION,
        "frame": FRAME,
        "boundary": BOUNDARY,
        "aggregate_caveat": AGGREGATE_CAVEAT,
        "rev03_provenance_note": REV03_PROVENANCE_NOTE,
        "rev04_provenance_note": REV04_PROVENANCE_NOTE,
        "measurability_note": MEASURABILITY_NOTE,
        "provenance": {
            "model": args.model,
            "revision": revision,
            "resolved_commit_sha": got_sha,
            "revision_verified": revision_verified,
            "claim_eligible": claim_eligible,
            "seed": args.seed,
            "device": device,
            "smoke": bool(args.smoke),
            "preflight": bool(args.preflight),
            "local_files_only": bool(args.local_files_only),
            "allow_tf32_matmul_pinned_false": True,
            # ---- rev 0.4 precision + resource block (D33, D42, D43) ----
            "dtype": args.dtype,
            "device_map_dispatched": bool(dispatched),
            "precision_policy": {
                "weights": args.dtype,
                "backend_flags_pinned": precision_flags,
                "projection_removal_in_fp32": True,
                "clean_pass_read_in_fp32_then_float64": True,
                "lm_head_fp32_island": lm_head_fp32,
                "attn_implementation": "eager",
                "rationale": (
                    "bf16 WEIGHTS with fp32 measurement math. The bf16 "
                    "dot-product error over 6144 dims with fp32 accumulation "
                    "is 1.44e-5 x ||h||, i.e. negligible -- but ONLY if "
                    "accumulation is forced, which is why "
                    "allow_bf16_reduced_precision_reduction is pinned False. "
                    "The lm-head island matters because greedy argmax, the "
                    "hedge probability MASS and the CHECK gate score in nats "
                    "all read the logits, where bf16 error near |logit| = 15 "
                    "is a ~6% multiplicative error per softmax probability."),
                "residual_discrete_risk": (
                    "argmax flips at near-ties do NOT cancel under pairing. "
                    "They inflate behavioral_change_rate and destroy the "
                    "byte-identity tie structure that D9/D23/D29 depend on, "
                    "which could flip a VACUOUS precondition to evaluable on "
                    "numerical noise. This is what the D34 pythia-2.8b "
                    "bf16-vs-fp32 calibration measures."),
            },
            "dtype_relative_quantum": quantum,
            "vram_after_load": vram_after_load,
            "n_controls_drawn": n_controls,
            "n_controls_gating_floor": CONTROLS_MIN_STRICT,
            "control_guard_surplus": n_controls - CONTROLS_MIN_STRICT,
            "run_dr_f2": run_dr_f2,
            "run_rs": run_rs,
            "battery": ("F5 rail only (DR-F5 + AMP-F5 + CONN)"
                        if not (run_rs or run_dr_f2)
                        else "F5 rail plus explicitly enabled optional arms"),
            "cuda_alloc_conf": alloc_conf,
            "hf_cache_safetensors_preflight": cache_status,
            "dr_engagement_step_used": bool(args.dr_engagement_step),
            "n_conn_dirs": n_conn_dirs,
            "max_new_tokens": max_new,
            "rs_samples": rs_samples,
            "rs_temperature": RS_TEMPERATURE if rs_samples > 1 else None,
            "prompt_bank_sha256": bank_sha,
            "config_sha256": config_sha,
            "fit_frame_indices": banks["fit_idx"],
            "judge_frame_indices": banks["judge_idx"],
            "rs_fit_pair_indices": banks["rs_fit_idx"],
            "rs_judge_pair_indices": banks["rs_judge_idx"],
            "n_frames_total": len(used_frames),
            "n_judge_per_class": len(banks["f5_judge"]),
            "n_fit_per_class": len(banks["f5_fit"]),
            "n_rs_pairs_total": len(used_pairs),
            "n_rs_judge_pairs": len(banks["rs_con_judge"]),
            "n_rs_fit_pairs": len(banks["rs_con_fit"]),
            "slot_verb_audit": verb_audit,
            "architecture": {
                "n_blocks": n_blocks, "n_heads_per_layer": n_heads,
                "hidden": hidden, "head_dim": head_dim,
                "total_heads": n_blocks * n_heads},
            "derived_layer_params": {
                "sweep_lo": sweep_lo, "L_STAR_MIN": l_star_min,
                "L_STAR_MAX": l_star_max,
                "DR_OFFSET": dr_offset, "topk_heads": topk_heads,
                "fractions": {"sweep_abs_D56": LAYER_SWEEP_MIN_ABS,
                              "l_star_min_abs_D56": L_STAR_MIN_ABS,
                              "sweep_frac_rev03_superseded":
                                  LAYER_SWEEP_MIN_FRAC_REV03,
                              "l_star_min_frac_rev03_superseded":
                                  L_STAR_MIN_FRAC_REV03,
                              "l_star_max": L_STAR_MAX_FRAC,
                              "dr_offset": DR_OFFSET_FRAC,
                              "topk_heads": TOPK_HEADS_FRAC,
                              "cover_k": cover_k_frac}},
            "control_ensemble_p_floor": float(1.0 / (n_controls + 1)),
            "control_ensemble_p_floor_at_gating_minimum": float(
                1.0 / (CONTROLS_MIN_STRICT + 1)),
            # ---- D40: the battery's unit arithmetic, written down ----
            "generation_unit_budget": _unit_budget(
                n_judge=len(banks["f5_judge"]), n_fit=len(banks["f5_fit"]),
                n_rs_judge=len(banks["rs_con_judge"]), n_controls=n_controls,
                rs_samples=rs_samples, run_dr_f2=run_dr_f2, run_rs=run_rs),
            "lexicon_token_ids": {
                "hedge_n_ids": len(hedge_ids), "control_lex_n_ids": len(ctrl_ids),
                "act_n_ids": len(act_ids), "restrain_n_ids": len(res_ids),
                "hedge_resolution": hedge_map,
                "control_lex_resolution": ctrl_map},
            "torch": torch.__version__,
            "numpy": np.__version__,
            "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        },
    }
    try:
        import transformers as _tf
        report["provenance"]["transformers"] = _tf.__version__
    except Exception:  # pragma: no cover
        report["provenance"]["transformers"] = "unavailable"
    try:
        import sklearn as _sk
        report["provenance"]["sklearn"] = _sk.__version__
    except Exception:  # pragma: no cover
        report["provenance"]["sklearn"] = "unavailable"
    # Incremental flush (review MINOR): a ~2 h run that crashes late must not
    # lose everything. The report is rewritten at every stage boundary.
    write_report(report, report_path)

    # ---------------- Stage: SURFACE CONTROL ----------------
    print("[surface] char-ngram control on the banks (fit->judge)")
    report["surface_control"] = {
        "f5_vs_neutral": char_ngram_control(
            banks["f5_fit"], banks["neu_fit"],
            banks["f5_judge"], banks["neu_judge"]),
        "f2_vs_neutral": char_ngram_control(
            banks["f2_fit"], banks["neu_fit"],
            banks["f2_judge"], banks["neu_judge"]),
        "rs_conflicted_vs_licensed": char_ngram_control(
            banks["rs_con_fit"], banks["rs_lic_fit"],
            banks["rs_con_judge"], banks["rs_lic_judge"]),
    }

    # ---------------- Stage: DISCOVER (fit split ONLY) ----------------
    print("[discover] capturing residual features (fit banks only)")
    feats = {
        "f5_fit": residual_feats(model, tok, banks["f5_fit"], device),
        "f2_fit": residual_feats(model, tok, banks["f2_fit"], device),
        "neu_fit": residual_feats(model, tok, banks["neu_fit"], device),
        "hedged": residual_feats(model, tok, banks["f5_hedged"], device),
        "plain": residual_feats(model, tok, banks["f5_plain"], device),
        "rs_lic_fit": residual_feats(model, tok, banks["rs_lic_fit"], device),
        "rs_con_fit": residual_feats(model, tok, banks["rs_con_fit"], device),
    }

    print("[discover] probe sweep across blocks (averaged over inner splits)")
    # Sweep is capped at L_STAR_MAX (rev 0.3 review fix D21): a block two away
    # from the unembedding leaves almost no downstream depth in which an
    # internal edit can turn into different TEXT, and under the clean-pass rule
    # only different text can register at all.
    sweep_hi = min(n_blocks - 2, l_star_max)
    accs_f5, accs_f2, mars_f5, mars_f2, sweep_blocks = [], [], [], [], []
    for L in range(sweep_lo, sweep_hi + 1):
        sweep_blocks.append(L)
        r5 = [fit_probe_acc(feats["f5_fit"][:, L + 1], feats["neu_fit"][:, L + 1],
                            args.seed + 37 * s) for s in range(N_INNER_SPLIT_SEEDS)]
        r2 = [fit_probe_acc(feats["f2_fit"][:, L + 1], feats["neu_fit"][:, L + 1],
                            args.seed + 37 * s) for s in range(N_INNER_SPLIT_SEEDS)]
        accs_f5.append(float(np.mean([x[0] for x in r5])))
        accs_f2.append(float(np.mean([x[0] for x in r2])))
        mars_f5.append(float(np.mean([x[1] for x in r5])))
        mars_f2.append(float(np.mean([x[1] for x in r2])))
    mean_accs = [(a + b) / 2.0 for a, b in zip(accs_f5, accs_f2)]
    mean_margins = [(a + b) / 2.0 for a, b in zip(mars_f5, mars_f2)]
    # L* is selected on the CONTINUOUS margin, not on accuracy (D21). With 32
    # fit frames per class on strict minimal pairs, accuracy saturates at
    # exactly 1.000 across a wide plateau; selecting on accuracy would make the
    # tie-break rule -- not the signal -- decide L*, and "deepest tied block"
    # would then return sweep_hi every time.
    # --- D51 (rev 0.4 second pass): the tie-break was INERT and ABORT_GUARD_
    # LAYER was doing all the work. Two repairs, both preregistered:
    #
    #  (1) TOLERANCE. `abs(v - best) <= 1e-12` on a continuous 5-seed-averaged
    #      margin means exact ties essentially never occur, so "shallowest tied
    #      block at or above L_STAR_MIN" never ran. The tolerance is now
    #      RELATIVE (MARGIN_TIE_REL_TOL), which makes the rule operative.
    #
    #  (2) SELECTION WINDOW. sweep_lo (0.25 x depth) is BELOW L_STAR_MIN
    #      (0.375 x depth), so a unique margin argmax anywhere in [sweep_lo,
    #      L_STAR_MIN) killed the run after discovery via ABORT_GUARD_LAYER --
    #      a live ~30% risk at 44 blocks, and one that interacts directly with
    #      rev 0.4's own recovered evidence: the validated 20B 40-Element probe
    #      peaked at LAYER 2 OF 44 with a shoulder only to L7, entirely BELOW
    #      this window. Selection is now restricted to blocks >= L_STAR_MIN,
    #      while the FULL sweep is still computed and REPORTED, so an early
    #      peak is disclosed loudly instead of aborting the run.
    idx_eligible = [i for i, L in enumerate(sweep_blocks) if L >= l_star_min]
    if not idx_eligible:                       # pragma: no cover - guarded above
        idx_eligible = list(range(len(sweep_blocks)))
    sel_margins = [mean_margins[i] for i in idx_eligible]
    best_margin = float(max(sel_margins))
    tol = MARGIN_TIE_REL_TOL * max(abs(best_margin), 1e-12)
    tied_margin = [sweep_blocks[i] for i in idx_eligible
                   if abs(mean_margins[i] - best_margin) <= tol]
    best_acc = float(max(mean_accs[i] for i in idx_eligible))
    tied_acc = [sweep_blocks[i] for i in idx_eligible
                if abs(mean_accs[i] - best_acc)
                <= MARGIN_TIE_REL_TOL * max(abs(best_acc), 1e-12)]
    # Preregistered tie-break: SHALLOWEST tied block at or above L_STAR_MIN
    # (safer than "deepest", which degenerates to the sweep ceiling under
    # saturation).
    l_star = int(min(tied_margin))
    acc_at_l_star = float(mean_accs[sweep_blocks.index(l_star)])
    full_argmax_block = int(sweep_blocks[int(np.argmax(mean_margins))])
    full_best_margin = float(max(mean_margins))

    rng_floor = np.random.default_rng(args.seed + 555)
    floor, floor_margin = [], []
    for tr in range(N_FLOOR_TRIALS):
        f5s = fit_probe_acc(feats["f5_fit"][:, l_star + 1],
                            feats["neu_fit"][:, l_star + 1],
                            args.seed + tr, shuffle_labels=True, rng=rng_floor)
        f2s = fit_probe_acc(feats["f2_fit"][:, l_star + 1],
                            feats["neu_fit"][:, l_star + 1],
                            args.seed + tr, shuffle_labels=True, rng=rng_floor)
        floor.append(float((f5s[0] + f2s[0]) / 2.0))          # matches best_acc
        floor_margin.append(float((f5s[1] + f2s[1]) / 2.0))   # matches margin
    floor_max = float(max(floor))
    floor_margin_max = float(max(floor_margin))

    report["discover"] = {
        "n_blocks": n_blocks,
        "sweep_blocks": sweep_blocks,
        "sweep_hi": sweep_hi,
        "probe_acc_f5_per_block": accs_f5,
        "probe_acc_f2_per_block": accs_f2,
        "mean_acc_per_block": mean_accs,
        "probe_margin_f5_per_block": mars_f5,
        "probe_margin_f2_per_block": mars_f2,
        "mean_margin_per_block": mean_margins,
        "selection_statistic": ("mean over the two drives of the inner-test "
                                "predicted-probability MARGIN (continuous, "
                                "non-saturating); accuracy is reported only"),
        "n_inner_split_seeds": N_INNER_SPLIT_SEEDS,
        "tied_blocks_at_max_margin": tied_margin,
        "tie_set_width_margin": len(tied_margin),
        "tied_blocks_at_max_accuracy": tied_acc,
        "tie_set_width_accuracy": len(tied_acc),
        "accuracy_saturated_plateau": bool(best_acc >= 1.0 - 1e-12
                                           and len(tied_acc) > 1),
        "tie_break_rule": ("shallowest tied block at or above L_STAR_MIN "
                           "(preregistered, rev 0.3 review fix D21; the tie "
                           "tolerance was made RELATIVE in rev 0.4's second "
                           "pass, deviation D51, because at 1e-12 on a "
                           "continuous averaged margin the rule never ran)"),
        "margin_tie_relative_tolerance": MARGIN_TIE_REL_TOL,
        "selection_window": [l_star_min, sweep_hi],
        "selection_window_note": (
            "L* is selected only from blocks at or above L_STAR_MIN (D51). The "
            "full sweep from sweep_lo is still computed and reported; "
            "restricting SELECTION removes a live ~30% ABORT_GUARD_LAYER risk "
            "at 44 blocks without hiding anything."),
        "full_sweep_argmax_block_reported_only": full_argmax_block,
        "full_sweep_best_margin_reported_only": full_best_margin,
        "early_layer_peak_below_selection_window": bool(
            full_argmax_block < l_star_min),
        "early_layer_disclosure": (
            "The validated Stage-9 40-Element probe on THIS model peaked at "
            "LAYER 2 OF 44 with a shoulder only to L7 -- entirely BELOW this "
            "selection window. If full_sweep_argmax_block_reported_only is also "
            "below L_STAR_MIN, the drive signal on these banks peaks shallower "
            "than the design's downstream-depth guard permits, and the "
            "configuration actually judged is NOT the peak. That is a disclosed "
            "design constraint (the clean-pass rule needs downstream depth for "
            "an internal edit to become different TEXT), not a measurement."),
        "L_star": l_star,
        "best_mean_margin": best_margin,
        "best_mean_acc": best_acc,
        "mean_acc_at_L_star": acc_at_l_star,
        "shuffled_label_floor": floor,
        "shuffled_label_floor_max": floor_max,
        "shuffled_label_floor_margin": floor_margin,
        "shuffled_label_floor_margin_max": floor_margin_max,
        "floor_statistic": "mean of F5-vs-neutral and F2-vs-neutral (matches best_acc)",
    }

    # D56: the hard ABORT_GUARD_LAYER is REPLACED by a per-test VACUOUS. A
    # shallow L* is now a legitimate selection (the validated 40E peak was at
    # layer 2 of 44), and AMP-F5 is sited AT L* so it is well-defined at any
    # depth. Only DR/CONN need an upstream site; when none exists they -- and
    # only they -- are stamped VACUOUS_NO_UPSTREAM_SITE and the run continues.
    # D56: DR_OFFSET ADAPTS to a shallow L* instead of the test dying. The
    # preregistered offset is 0.25*depth, but it cannot exceed L*-1 or the rail
    # site would be at/above the embedding. Taking the largest VALID upstream
    # gap keeps DR/CONN evaluable at any selected depth; the realised offset is
    # reported so a reader sees when it was reduced.
    dr_offset_preregistered = int(dr_offset)
    dr_offset = max(1, min(dr_offset_preregistered, l_star - 1))
    report["discover"]["dr_offset_preregistered"] = dr_offset_preregistered
    report["discover"]["dr_offset_realised"] = int(dr_offset)
    report["discover"]["dr_offset_reduced_for_shallow_l_star"] = bool(
        dr_offset < dr_offset_preregistered)
    l_dr = l_star - dr_offset
    no_upstream_site = bool(l_dr < 0)
    shallow_l_star = bool(l_star < SHALLOW_L_STAR_CAVEAT_FRAC * n_blocks)
    report["discover"]["no_upstream_site"] = no_upstream_site
    report["discover"]["shallow_l_star_surface_caveat"] = shallow_l_star
    if shallow_l_star:
        report["discover"]["shallow_l_star_caveat_text"] = (
            f"L*={l_star} is below {SHALLOW_L_STAR_CAVEAT_FRAC:.2f} x depth "
            f"({n_blocks}). A probe peaking this shallow is prima facie more "
            "consistent with a SURFACE/token-level feature than with deep "
            "semantics (cf. the standing surface-separability, MTC-GREY and "
            "involution findings). No PASS in this run may be read as evidence "
            "of deep semantic structure; it licenses only 'a direction at this "
            "depth carries the measured content'. (D56)")
        print(f"[discover] shallow L*={l_star} -> surface caveat stamped (D56)")
    if no_upstream_site:
        report["discover"]["no_upstream_site_reason"] = (
            f"L*={l_star}, DR_OFFSET={dr_offset} -> L_dr={l_dr} < 1: no valid "
            "upstream rail site exists at this depth. DR_F5 and CONN are "
            "VACUOUS_NO_UPSTREAM_SITE; AMP_F5 (sited AT L*) proceeds. (D56)")
        print("[discover] no upstream site -> DR_F5/CONN VACUOUS_NO_UPSTREAM_SITE (D56)")
        # Clamp to a valid index so nothing downstream can mis-index; the
        # no_upstream_site FLAG (not this value) drives DR/CONN to VACUOUS, and
        # the DR cover scoring is skipped entirely.
        l_dr = 0
        report["discover"]["L_dr_clamped_unused"] = True
    report["discover"]["L_dr"] = l_dr
    print(f"[discover] L*={l_star} (acc={best_acc:.3f}) L_dr={l_dr} "
          f"floor_max={floor_max:.3f}")

    if best_acc <= floor_max:
        report["aggregate"] = {
            "status": "NO_SIGNAL_ATLAS_V0",
            "reason": "best probe accuracy does not beat shuffled-label floor"}
        write_report(report, report_path)
        print("[abort] NO_SIGNAL: probe does not beat shuffled floor")
        return 0

    # Directions (fit split only).
    u_f5_star = diff_dir(feats["f5_fit"], feats["neu_fit"], l_star + 1)
    u_f2_star = diff_dir(feats["f2_fit"], feats["neu_fit"], l_star + 1)
    u_f5_dr = diff_dir(feats["f5_fit"], feats["neu_fit"], l_dr + 1)
    u_f2_dr = diff_dir(feats["f2_fit"], feats["neu_fit"], l_dr + 1)

    # rev 0.3 PRIMARY u_RS: restraint-CONTEXT direction (conflicted - licensed)
    # on the RS FIT half, orthogonalized against u_F5. The rev-0.2 direction
    # (hedged - plain) was largely a hedge-VOCABULARY direction; it is retained
    # below as a disclosed secondary comparison only.
    raw_rs = (feats["rs_con_fit"][:, l_star + 1].mean(0)
              - feats["rs_lic_fit"][:, l_star + 1].mean(0))
    raw_rs = raw_rs - float(raw_rs @ u_f5_star) * u_f5_star
    u_rs_star = unit(raw_rs)
    raw_rs_legacy = (feats["hedged"][:, l_star + 1].mean(0)
                     - feats["plain"][:, l_star + 1].mean(0))
    raw_rs_legacy = raw_rs_legacy - float(raw_rs_legacy @ u_f5_star) * u_f5_star
    u_rs_legacy = unit(raw_rs_legacy)
    report["discover"]["u_rs_primary"] = (
        "conflicted_minus_licensed on RS fit half, orthogonalized vs u_F5")
    report["discover"]["u_rs_legacy_cosine_with_primary"] = float(
        u_rs_star @ u_rs_legacy)

    # Variance-carrying control-direction subspace at L* (drive fit banks).
    X_star = np.concatenate([feats["f5_fit"][:, l_star + 1],
                             feats["f2_fit"][:, l_star + 1],
                             feats["neu_fit"][:, l_star + 1]], axis=0)
    V_star = pc_basis(X_star, PC_SUBSPACE_K)
    # SEPARATE control subspace for RS, fit on the RS FIT RESIDUALS (rev 0.3
    # review fix D22). The rev-0.3 draft drew RS control directions from
    # V_star, i.e. the DRIVE bank's dominant-variance subspace -- a different
    # prompt distribution from the one u_RS is fit on, and one whose random
    # unit vectors carry far more projection mass on any text than a small
    # orthogonalized difference-of-means. That is exactly the rev-0.2 pattern
    # (targeted increase 0.107 vs control increases 0.528 / 0.547): the
    # controls were systematically STRONGER perturbations than the target, so a
    # FAIL could not distinguish "no brake" from "controls too strong".
    X_rs = np.concatenate([feats["rs_lic_fit"][:, l_star + 1],
                           feats["rs_con_fit"][:, l_star + 1]], axis=0)
    V_rs = pc_basis(X_rs, PC_SUBSPACE_K)

    rng_conn = np.random.default_rng(args.seed + 901)
    # D52 (rev 0.4 second pass): CONN's downstream random READOUT directions are
    # orthogonalized against u_F5 too. PREREG 3.0 states the orthogonalization
    # rule is "binding for every ensemble in the battery", and V_star contains
    # u_F5 -- so leaving ortho_to=None here reproduced, for CONN, exactly the
    # contamination class D37 fixes for AMP. The direction of the bias is
    # conservative (it makes CONN's d_target > max(d_rand) leg HARDER) and these
    # are readout rather than perturbation directions, but a per-test exception
    # is precisely what rev 0.4 exists to eliminate.
    conn_dirs = {f"r{i}": pc_random_dir(V_star, rng_conn, ortho_to=u_f5_star)
                 for i in range(n_conn_dirs)}
    measure_dirs = {"uF5": u_f5_star, "uF2": u_f2_star}
    measure_dirs.update(conn_dirs)
    rand_keys = sorted(conn_dirs)

    # DR covers (Stage-27F-style scoring at L_dr, fit banks only).
    print("[discover] scoring DR covers at L_dr")
    mlp_mod = mlp_out_module(layers[l_dr])
    w_out = mlp_mod.weight.detach().float().cpu().numpy()   # [hidden, intermediate]
    intermediate = int(w_out.shape[1])
    acts_f5 = mlp_intermediate_feats(model, tok, banks["f5_fit"], mlp_mod, device)
    acts_f2 = mlp_intermediate_feats(model, tok, banks["f2_fit"], mlp_mod, device)
    acts_nt = mlp_intermediate_feats(model, tok, banks["neu_fit"], mlp_mod, device)
    cover_k = derive_cover_k(intermediate, cover_k_frac)
    cover_f5, _ = score_dr_cover(acts_f5, acts_nt, w_out, u_f5_dr, cover_k)
    cover_f2, _ = score_dr_cover(acts_f2, acts_nt, w_out, u_f2_dr, cover_k)
    mean_abs_f5 = np.abs(acts_f5).mean(0)
    mean_abs_f2 = np.abs(acts_f2).mean(0)
    report["provenance"]["architecture"]["mlp_intermediate"] = intermediate
    report["provenance"]["cover_k"] = cover_k
    report["provenance"]["cover_k_fraction_of_intermediate"] = float(
        cover_k / intermediate)
    report["provenance"]["cover_k_rev02_absolute_equivalent"] = 32
    report["provenance"]["topk_heads_fraction_of_all_heads"] = float(
        topk_heads / (n_blocks * n_heads))
    # D55: rebind the BINDING config sha now that every derived parameter --
    # including cover_k and the L* selection window -- is known.
    config_payload["derived"]["cover_k"] = int(cover_k)
    config_payload["derived"]["mlp_intermediate"] = int(intermediate)
    config_payload["derived"]["L_star"] = int(l_star)
    config_payload["derived"]["L_dr"] = int(l_dr)
    config_sha = sha_of(config_payload)
    report["provenance"]["config_sha256"] = config_sha
    report["provenance"]["config_sha256_pre_discovery"] = config_sha_pre
    report["provenance"]["config_sha256_note"] = (
        "the BINDING sha is config_sha256, taken after every derived layer/head/"
        "cover parameter actually used is known (deviation D55). "
        "config_sha256_pre_discovery is the sha available on the abort paths "
        "that fire before discovery and is retained so those aborts stay "
        "auditable.")
    print(f"[discover] cover_k={cover_k} of {intermediate} intermediate coords "
          f"({100.0 * cover_k / intermediate:.3f}%)")
    stage_mark("discover")
    write_report(report, report_path)

    # ---------------- Stage: LABEL ----------------
    atlas = [
        {"component_id": "DR-F5", "type_label": "DR",
         "location": {"kind": "mlp_intermediate_cover", "block": l_dr,
                      "coords": cover_f5}},
        {"component_id": "DR-F2", "type_label": "DR",
         "location": {"kind": "mlp_intermediate_cover", "block": l_dr,
                      "coords": cover_f2}},
        {"component_id": "RS-F5", "type_label": "RS",
         "location": {"kind": "residual_direction", "block": l_star,
                      "note": "restraint-CONTEXT direction (conflicted minus "
                              "licensed), orthogonalized vs drive direction"}},
        {"component_id": "AMP-F5", "type_label": "AMP",
         "location": {"kind": "residual_direction", "block": l_star,
                      "note": "drive subspace rank-1"}},
    ]
    report["atlas"] = atlas

    def dr_hooks(cover):
        return [(mlp_mod, make_cover_zero_prehook(cover), "pre")]

    def eraser_hooks(u_dir):
        return [(layers[l_star], ForwardEdit(make_projection_removal(u_dir)),
                 "forward")]

    # ---------------- Stage: PREFLIGHT (declared IN ADVANCE, go/no-go) ----
    # Rev 0.3 review fix D28. On rev-0.2's own numbers DR-F5 changed the text on
    # only ~6 of 12 judge prompts, i.e. a behavioural-change rate of ~0.50 --
    # BELOW the new BEHAVIORAL_CHANGE_MIN of 0.60. DR_F5 and CONN share tgt_dr5
    # and therefore go VACUOUS together; with RS plausibly VACUOUS_NO_BRAKE that
    # is n_evaluable < 3 and a GREY verdict after ~2 h of A40 time. This
    # preflight reads NO test statistic -- only whether each intervention
    # changes the text at all -- so it cannot tune anything toward a pass, and
    # it is declared here before the run rather than after a null.
    if args.preflight:
        k = max(2, int(args.preflight_prompts))
        pf_f5 = banks["f5_judge"][:k]
        pf_con = banks["rs_con_judge"][:k]
        pf = {}
        b_f5 = gen_condition(model, tok, pf_f5, device, [], max_new)
        t_dr = gen_condition(model, tok, pf_f5, device, dr_hooks(cover_f5), max_new)
        t_amp = gen_condition(model, tok, pf_f5, device,
                              eraser_hooks(u_f5_star), max_new)
        pf["DR_F5_behavioral_change_rate"] = behavioral_change_rate(b_f5, t_dr)
        pf["AMP_F5_behavioral_change_rate"] = behavioral_change_rate(b_f5, t_amp)
        if run_rs:
            rs_seed = args.seed * 10000 + 7000
            b_rs = gen_condition(model, tok, pf_con, device, [], max_new,
                                 n_samples=rs_samples, sample_seed=rs_seed)
            t_rs = gen_condition(model, tok, pf_con, device,
                                 eraser_hooks(u_rs_star), max_new,
                                 n_samples=rs_samples, sample_seed=rs_seed)
            pf["RS_F5_behavioral_change_rate"] = behavioral_change_rate(b_rs, t_rs)
        else:
            pf["RS_F5_behavioral_change_rate"] = None
            pf["RS_F5_note"] = ("RS is OUT OF SCOPE by default in rev 0.4's "
                                "second pass (D48) and therefore does not gate "
                                "the preflight; --run-rs restores both")
        gating = [pf["DR_F5_behavioral_change_rate"],
                  pf["AMP_F5_behavioral_change_rate"]]
        if pf["RS_F5_behavioral_change_rate"] is not None:
            gating.append(pf["RS_F5_behavioral_change_rate"])
        pf["n_prompts"] = k
        pf["threshold"] = BEHAVIORAL_CHANGE_MIN
        pf["gating_rates"] = gating
        pf["go"] = bool(min(gating) >= BEHAVIORAL_CHANGE_MIN)
        pf["cover_k_frac_in_effect"] = cover_k_frac
        pf["dr_engagement_step_used"] = bool(args.dr_engagement_step)
        pf["note"] = ("PREFLIGHT ONLY -- never evidence, reads no test "
                      "statistic. A NO-GO means the confirmatory run would "
                      "very likely stamp VACUOUS_NO_BEHAVIORAL_CHANGE on the "
                      "affected arms; fix the intervention strength (cover_k, "
                      "L*) or stop, and log whatever is changed as a deviation "
                      "BEFORE the confirmatory run.")
        # D50: the preregistered STOP RULE. Rev 0.4's first draft predicted its
        # own verdict could not move ("the DR/CONN engagement problem must be
        # solved in the same run") while changing nothing that would move it,
        # and D31's single authorised step was consumed at rev 0.3 and never
        # re-authorised for 20B -- so a NO-GO had no declared remedy at all.
        pf["stop_rule"] = {
            "on_no_go_dr_f5": (
                "apply --dr-engagement-step ONCE (COVER_K_FRAC "
                f"{COVER_K_FRAC} -> {COVER_K_FRAC_STEP2}), log it in PREREG "
                "section 10 with date and reason BEFORE re-running the "
                "preflight, and re-run the preflight."),
            "on_second_no_go": (
                "DO NOT launch the battery. DR-F5 and CONN share the target "
                "condition and would go VACUOUS together, leaving n_evaluable "
                "= 1 and a preregistered GREY after ~2.3 h. The declared "
                "fallback is a SINGLE-TEST AMP-F5 confirmatory run whose "
                "verdict is capped at GREY_ATLAS_V0_INSUFFICIENT_EVALUABLE and "
                "which is reported as one test, not a battery."),
            "no_ladder": ("exactly ONE widening step is authorised at 20B "
                          "(deviation D50). An open-ended widen-until-it-moves "
                          "ladder is fishing and is prohibited."),
        }
        report["preflight"] = pf
        report["aggregate"] = {"status": "PREFLIGHT_ONLY", "go": pf["go"]}
        stage_mark("preflight")
        report["provenance"]["runtime_seconds"] = round(time.time() - t0, 1)
        report["provenance"]["stage_elapsed_seconds"] = stage_times
        report["provenance"]["peak_vram"] = peak_vram_gib()
        write_report(report, report_path)
        print(f"[preflight] go={pf['go']} DR={pf['DR_F5_behavioral_change_rate']:.2f} "
              f"AMP={pf['AMP_F5_behavioral_change_rate']:.2f} "
              f"RS={pf['RS_F5_behavioral_change_rate']} -> {report_path}")
        return 0

    # ---------------- Stage: READOUT PROBE (D35) --------------------------
    # The rev-0.4 PRIMARY drive readout is a HELD-OUT 3-way probe on the
    # generated text's activations, read as P(own class). It is fit on the FIT
    # half's BASELINE generations ONLY, so discovery and judgment stay disjoint
    # at the frame level exactly as the projection readout already required.
    #
    # WHY: the validated 40-Element result that motivates rev 0.4 read a
    # HELD-OUT PROBE ACCURACY (95.625% -> 66.897%, chance 0.025, n_test 4480)
    # -- a bounded quantity with a defined chance floor and ~30 pp of usable
    # range -- NOT a projection onto the ablated direction. Rev 0.3's AMP
    # readout was 78.7% bank-invariant offset, which is why its effects and its
    # nulls were indistinguishable. This is the closest available analogue: the
    # 40E fixture itself is NOT reachable from this repo (deviation D36).
    print("[readout] fit-half baseline generations for the held-out readout probe")
    probe_rows = {}
    for cls, bank in (("f5", "f5_fit"), ("f2", "f2_fit"), ("neutral", "neu_fit")):
        txt_fit = gen_condition(model, tok, banks[bank], device, [], max_new)
        m_fit = measure_condition(model, tok, banks[bank], txt_fit, device,
                                  l_star, measure_dirs)
        probe_rows[cls] = m_fit["vec"]
    readout_probe, probe_meta = fit_readout_probe(probe_rows, args.seed + 4040)
    probe_classes = probe_meta.get("classes", [])
    report["readout_probe"] = probe_meta
    if readout_probe is None:
        print("[warn] readout probe unavailable; AMP falls back to the "
              "projection readout and this is recorded")
        report["readout_probe"]["fallback"] = (
            "AMP_PRIMARY_READOUT falls back to the projection direction; the "
            "rev-0.4 headline readout change (D35) did NOT take effect and no "
            "rev-0.4 selectivity claim is licensed")
    amp_readout = AMP_PRIMARY_READOUT if readout_probe is not None else "proj"
    stage_mark("readout_probe")
    write_report(report, report_path)

    def _probe(m, cls):
        return attach_probe_readout(m, readout_probe, probe_classes, cls)

    # ---------------- Stage: ABLATE (generate hooked, judge CLEAN) --------
    print("[ablate] baselines (judge banks, no hooks)")
    txt_base_f5 = gen_condition(model, tok, banks["f5_judge"], device, [], max_new)
    txt_base_f2 = gen_condition(model, tok, banks["f2_judge"], device, [], max_new)
    txt_base_neu = gen_condition(model, tok, banks["neu_judge"], device, [], max_new)

    base_f5 = _probe(measure_condition(model, tok, banks["f5_judge"], txt_base_f5,
                                       device, l_star, measure_dirs), "f5")
    base_f2 = _probe(measure_condition(model, tok, banks["f2_judge"], txt_base_f2,
                                       device, l_star, measure_dirs), "f2")
    base_neu = _probe(measure_condition(model, tok, banks["neu_judge"],
                                        txt_base_neu, device, l_star,
                                        measure_dirs), "neutral")

    # Presence thresholds from BASELINE conditions only.
    tau_f5 = 0.5 * (float(np.mean(base_f5["proj"]["uF5"]))
                    + float(np.mean(base_neu["proj"]["uF5"])))
    tau_f2 = 0.5 * (float(np.mean(base_f2["proj"]["uF2"]))
                    + float(np.mean(base_neu["proj"]["uF2"])))
    report["discover"]["tau_F5"] = tau_f5
    report["discover"]["tau_F2"] = tau_f2

    # D35 diagnostic: the DIRECT 40-Element analogue -- held-out probe accuracy
    # on the three UNABLATED judge banks. This is the number that says whether
    # the substitute readout has any dynamic range to lose in the first place;
    # if it is at chance the readout is dead, and if it is saturated at 1.000
    # with extreme probabilities the readout is compressed and the AMP result
    # must be read with that caveat. Costs nothing (the vectors already exist).
    if readout_probe is not None:
        diag, accs = {}, []
        i_f5 = probe_classes.index("f5") if "f5" in probe_classes else 0
        for cls, mm in (("f5", base_f5), ("f2", base_f2), ("neutral", base_neu)):
            if cls not in probe_classes:
                continue
            V = np.asarray(mm["vec"], dtype=np.float64)
            P = readout_probe.predict_proba(V)
            pred = P.argmax(axis=1)
            j = probe_classes.index(cls)
            diag[cls] = {
                "mean_p_own_class": float(P[:, j].mean()),
                "sd_p_own_class": float(P[:, j].std()),
                "mean_p_f5": float(P[:, i_f5].mean()),
                "accuracy": float(np.mean(pred == j)),
                "n_rows": int(V.shape[0]),
            }
            accs.append(diag[cls]["accuracy"])
        report["readout_probe"]["judge_baseline_diagnostics"] = {
            "per_class": diag,
            "held_out_accuracy": float(np.mean(accs)) if accs else None,
            "chance_level": READOUT_PROBE_CHANCE,
            "note": ("direct analogue of the validated 40-Element held-out "
                     "probe accuracy (0.95625 at chance 0.025, n_test 4480). "
                     "Read the per-class sd: probabilities saturated at 0/1 "
                     "mean the readout is compressed and the AMP drop must be "
                     "interpreted with that caveat, even though the comparison "
                     "against controls remains on the same scale and therefore "
                     "stays fair."),
        }

    # --- D49: the preregistered probe VIABILITY gate. --------------------
    # The rev-0.4 first draft COMPUTED the diagnostics above and then consulted
    # them nowhere: AMP could return PASS on a readout whose own report block
    # said the drop size was uninterpretable, while D41's se-based window was
    # simultaneously inert because a saturated readout has se == 0. The gate is
    # now keyed on those already-computed diagnostics and it is GATING.
    if readout_probe is not None:
        viability = probe_viability(
            report["readout_probe"].get("judge_baseline_diagnostics"),
            READOUT_PROBE_CHANCE)
    else:
        viability = {
            "viable": False,
            "reason": ("UNAVAILABLE: the readout probe could not be fitted "
                       f"({probe_meta.get('status')})"),
            "rule": "see D49",
        }
    report["readout_probe"]["viability"] = viability
    amp_readout_viability = None
    if AMP_PRIMARY_READOUT == "probe_p":
        amp_readout_viability = viability
        if not viability["viable"]:
            amp_readout = "proj"
            report["readout_probe"]["fallback"] = (
                "AMP falls back to the PROJECTION readout for its descriptive "
                "numbers, but the test is stamped VACUOUS_READOUT_NOT_VIABLE: "
                "the rev-0.4 headline readout change (D35) did NOT take effect "
                "and no rev-0.4 selectivity claim is licensed. A PASS on the "
                "fallback readout is NOT available -- that readout is the one "
                "rev 0.3 showed is 78.7% dead offset, which is why D35 exists.")
            print(f"[warn] readout probe NOT viable: {viability['reason']}")
    write_report(report, report_path)

    # D42/D52: the number of independent measurements each judged mean averages
    # over -- prompts x continuation positions. Quantization noise averages down
    # by sqrt of this, which is why the RAW dtype quantum is NOT the binding
    # floor and the rev-0.4 first draft's "48x below the bf16 quantum" reasoning
    # was misderived even though the DR-F2 decision it supported survives on
    # other grounds (behavioural change 0.313).
    n_averaged = int(max(1, len(banks["f5_judge"]) * max_new))
    report["provenance"]["n_averaged_measurements_per_readout_mean"] = n_averaged

    tests = {}

    # ---- DR-F5 ----
    print("[ablate] DR-F5")
    # D38: the DR rail's "dose" is the removed activation mass of the zeroed
    # cover, measured on the JUDGE prompts. Decile-matched covers are dose
    # matched BY CONSTRUCTION; rev 0.4 reports the realised numbers instead of
    # asserting it, exactly as PREREG line 206 was faulted for doing.
    acts_f5_judge = mlp_intermediate_feats(
        model, tok, banks["f5_judge"], mlp_mod, device)

    def _cover_mag(cov):
        idx = sorted(int(i) for i in cov)
        return float(np.mean(np.abs(acts_f5_judge[:, idx]).sum(axis=1)))

    txt_tgt = gen_condition(model, tok, banks["f5_judge"], device,
                            dr_hooks(cover_f5), max_new)
    tgt_dr5 = _probe(measure_condition(model, tok, banks["f5_judge"], txt_tgt,
                                       device, l_star, measure_dirs), "f5")
    ctrls_dr5, dr5_ctrl_mags = [], []
    for tr in range(n_controls):
        rng = np.random.default_rng(args.seed * 10000 + tr)
        cov = decile_matched_cover(mean_abs_f5, cover_f5, rng)
        dr5_ctrl_mags.append(_cover_mag(cov))
        txt_c = gen_condition(model, tok, banks["f5_judge"], device,
                              dr_hooks(cov), max_new)
        ctrls_dr5.append(_probe(measure_condition(
            model, tok, banks["f5_judge"], txt_c, device, l_star,
            measure_dirs), "f5"))
    dr5_target_mag = _cover_mag(cover_f5)
    dr5_mag_meta = {
        "metric": ("mean over judge prompts of the summed |activation| of the "
                   "zeroed MLP-intermediate coordinates, clean model, last "
                   "token -- i.e. the activation mass the cut removes"),
        "target_perturbation_magnitude": dr5_target_mag,
        "control_perturbation_magnitudes": dr5_ctrl_mags,
        "control_magnitude_mean": (float(np.mean(dr5_ctrl_mags))
                                   if dr5_ctrl_mags else None),
        "control_magnitude_max": (float(np.max(dr5_ctrl_mags))
                                  if dr5_ctrl_mags else None),
        "target_over_control_mean_magnitude_ratio": (
            float(dr5_target_mag / float(np.mean(dr5_ctrl_mags)))
            if dr5_ctrl_mags and float(np.mean(dr5_ctrl_mags)) > 0 else None),
        "dose_matching": "by construction (activation-decile-matched covers)",
        "reading_rule": ("if the target's magnitude is far below the control "
                         "mean, the correct reading of a FAIL is 'the "
                         "comparison was not matched', NOT 'there is no rail'"),
    }
    # NOTE (review MINOR, deduplicated): the F5-bank-with-F2-cover condition is
    # simultaneously DR-F5's cross-COVER control and DR-F2's cross-RAIL
    # selectivity condition, and the F2-bank-with-F5-cover condition is the
    # mirror. The rev-0.3 draft generated each of them TWICE with identical
    # configuration (~64 wasted generation units). Each is now generated once,
    # with the full measure_dirs so both consumers can read it.
    txt_f5bank_f2cover = gen_condition(model, tok, banks["f5_judge"], device,
                                       dr_hooks(cover_f2), max_new)
    cond_f5bank_f2cover = _probe(measure_condition(
        model, tok, banks["f5_judge"], txt_f5bank_f2cover, device, l_star,
        measure_dirs), "f5")
    txt_f2bank_f5cover = gen_condition(model, tok, banks["f2_judge"], device,
                                       dr_hooks(cover_f5), max_new)
    cond_f2bank_f5cover = _probe(measure_condition(
        model, tok, banks["f2_judge"], txt_f2bank_f5cover, device, l_star,
        measure_dirs), "f2")
    cross_dr5 = cond_f5bank_f2cover     # DR-F5 cross-cover control
    xrail_dr5 = cond_f2bank_f5cover     # DR-F5 cross-rail selectivity
    tests["DR_F5"] = eval_dr_test(base_f5, tgt_dr5, ctrls_dr5, cross_dr5,
                                  tau_f5, base_f2, xrail_dr5, "uF5", "uF2",
                                  readout=DR_PRIMARY_READOUT,
                                  min_ctrl=min_ctrl, quantum=quantum,
                                  magnitude_meta=dr5_mag_meta,
                                  n_averaged=n_averaged,
                                  strict_gates=strict_gates)
    stage_mark("DR_F5")
    write_report(report, report_path)

    # ---- DR-F2 (OPTIONAL in rev 0.4 -- deviation D40) ----
    # The DR-F2 COVER is still computed above, so DR-F5's cross-cover control
    # and BOTH cross-rail selectivity conditions are untouched: only the 20
    # DR-F2 control-cover generations (N(1+C) = 672 units) are saved. Dropping
    # this TEST is justified partly by rev-0.3 OUTCOMES -- behavioural change
    # 0.313, targeted drop 0.00132, i.e. ~48x BELOW the bf16 quantum -- and is
    # declared as such rather than presented as independent design.
    if run_dr_f2:
        print("[ablate] DR-F2")
        acts_f2_judge = mlp_intermediate_feats(
            model, tok, banks["f2_judge"], mlp_mod, device)

        def _cover_mag_f2(cov):
            idx = sorted(int(i) for i in cov)
            return float(np.mean(np.abs(acts_f2_judge[:, idx]).sum(axis=1)))

        txt_tgt2 = gen_condition(model, tok, banks["f2_judge"], device,
                                 dr_hooks(cover_f2), max_new)
        tgt_dr2 = _probe(measure_condition(model, tok, banks["f2_judge"],
                                           txt_tgt2, device, l_star,
                                           measure_dirs), "f2")
        ctrls_dr2, dr2_ctrl_mags = [], []
        for tr in range(n_controls):
            rng = np.random.default_rng(args.seed * 10000 + 100 + tr)
            cov = decile_matched_cover(mean_abs_f2, cover_f2, rng)
            dr2_ctrl_mags.append(_cover_mag_f2(cov))
            txt_c = gen_condition(model, tok, banks["f2_judge"], device,
                                  dr_hooks(cov), max_new)
            ctrls_dr2.append(_probe(measure_condition(
                model, tok, banks["f2_judge"], txt_c, device, l_star,
                measure_dirs), "f2"))
        dr2_target_mag = _cover_mag_f2(cover_f2)
        dr2_mag_meta = {
            "metric": dr5_mag_meta["metric"],
            "target_perturbation_magnitude": dr2_target_mag,
            "control_perturbation_magnitudes": dr2_ctrl_mags,
            "control_magnitude_mean": (float(np.mean(dr2_ctrl_mags))
                                       if dr2_ctrl_mags else None),
            "target_over_control_mean_magnitude_ratio": (
                float(dr2_target_mag / float(np.mean(dr2_ctrl_mags)))
                if dr2_ctrl_mags and float(np.mean(dr2_ctrl_mags)) > 0 else None),
            "dose_matching": "by construction (activation-decile-matched covers)",
        }
        cross_dr2 = cond_f2bank_f5cover     # DR-F2 cross-cover control (reused)
        xrail_dr2 = cond_f5bank_f2cover     # DR-F2 cross-rail selectivity (reused)
        tests["DR_F2"] = eval_dr_test(base_f2, tgt_dr2, ctrls_dr2, cross_dr2,
                                      tau_f2, base_f5, xrail_dr2, "uF2", "uF5",
                                      readout=DR_PRIMARY_READOUT,
                                      min_ctrl=min_ctrl, quantum=quantum,
                                      magnitude_meta=dr2_mag_meta,
                                      n_averaged=n_averaged,
                                      strict_gates=strict_gates)
        stage_mark("DR_F2")
        write_report(report, report_path)

    # ---- AMP-F5 (rev 0.4 HEADLINE TEST) ----
    print("[ablate] AMP-F5 (headline: selectivity)")
    txt_amp = gen_condition(model, tok, banks["f5_judge"], device,
                            eraser_hooks(u_f5_star), max_new)
    tgt_amp = _probe(measure_condition(model, tok, banks["f5_judge"], txt_amp,
                                       device, l_star, measure_dirs), "f5")

    # --- D37 + D38: the rev-0.4 AMP control ensemble. ---------------------
    # Rev 0.3 drew AMP controls as pc_random_dir(V_star, rng) with ortho_to
    # defaulting to None. V_star is the top-10 PC basis of the pooled CENTERED
    # drive fit rows, and the between-bank mean difference IS u_F5, so u_F5 lay
    # substantially INSIDE the subspace the "controls" were drawn from: a
    # random unit vector there has E[cos^2] = 0.1 and the largest of 24 draws
    # typically reaches |cos| ~ 0.55-0.60. The best "control" was therefore
    # roughly half the target intervention plus extra generic damage. AMP was
    # the ONLY test in the battery whose null was contaminated by its own
    # target: RS passed ortho_to for BOTH its families, DR used decile-matched
    # covers, CHECK used count-matched head sets.
    #
    # Rev 0.4 fixes it in the ranked order the diagnosis gives:
    #   (1) SHUFFLED-LABEL REFITS of the SAME estimator on permuted F5/neutral
    #       fit labels -- the family that fixes the estimator, the fit
    #       distribution and the estimation-noise geometry and varies only the
    #       LABEL, which is precisely the scientific claim under test;
    #   (2) DOSE-MATCHED on removed activation mass, not on vector norm;
    #   (3) ORTHOGONALIZED against u_F5;
    #   (4) DAMAGE-GUARDED (D39, applied in the evaluator).
    # u_F2 is kept as the semantic-nearest-neighbour cross-direction control.
    #
    # HONEST FRAMING, carried into the report: this ensemble is by construction
    # a LESS destructive null than rev 0.3's. That is because the rev-0.3 null
    # was contaminated and undosed -- evidenced by the code asymmetry with RS
    # -- not because rev 0.4 made the test easier. The magnitude ratio and the
    # per-control damage statistics are published alongside any pass so a
    # reader can check that directly instead of taking it on trust.
    H_f5j = residual_feats(model, tok, banks["f5_judge"], device)[:, l_star + 1]

    def _mag_f5(u):
        return float(np.mean(np.abs(H_f5j @ np.asarray(u, dtype=np.float64))))

    amp_target_mag = _mag_f5(u_f5_star)
    f5_rows_fit = feats["f5_fit"][:, l_star + 1]
    neu_rows_fit = feats["neu_fit"][:, l_star + 1]
    n_shuf_amp = int(round(AMP_CTRL_SHUFFLED_FRAC * n_controls))
    n_shuf_amp = (max(1, min(n_controls - 1, n_shuf_amp)) if n_controls > 1
                  else n_controls)
    ctrls_amp, amp_ctrl_mags, amp_ctrl_fams = [], [], []
    amp_ctrl_matched, amp_ctrl_tries, amp_ctrl_cos = [], [], []
    for tr in range(n_controls):
        rng = np.random.default_rng(args.seed * 10000 + 300 + tr)
        if tr < n_shuf_amp:
            fam = "shuffled_label_refit"

            def draw(r):
                return shuffled_label_dir(f5_rows_fit, neu_rows_fit, r,
                                          ortho_to=u_f5_star)
        else:
            fam = "pc_subspace_ortho_to_target"

            def draw(r):
                return pc_random_dir(V_star, r, ortho_to=u_f5_star)

        u_rand, mag, tries, matched = dose_matched_draw(
            draw, rng, _mag_f5, amp_target_mag)
        amp_ctrl_fams.append(fam)
        amp_ctrl_mags.append(mag)
        amp_ctrl_tries.append(tries)
        amp_ctrl_matched.append(bool(matched))
        amp_ctrl_cos.append(float(np.asarray(u_rand) @ np.asarray(u_f5_star)))
        txt_c = gen_condition(model, tok, banks["f5_judge"], device,
                              eraser_hooks(u_rand), max_new)
        ctrls_amp.append(_probe(measure_condition(
            model, tok, banks["f5_judge"], txt_c, device, l_star,
            measure_dirs), "f5"))
    amp_ctrl_mean_mag = float(np.mean(amp_ctrl_mags)) if amp_ctrl_mags else 0.0
    amp_mag_meta = {
        "n_shuffled_label_refit": n_shuf_amp,
        "n_pc_subspace_ortho": n_controls - n_shuf_amp,
        "families": amp_ctrl_fams,
        "orthogonalized_to_target": True,
        "control_cosine_with_target": amp_ctrl_cos,
        "max_abs_cosine_with_target": (float(np.max(np.abs(amp_ctrl_cos)))
                                       if amp_ctrl_cos else None),
        "perturbation_magnitude_metric": (
            "mean |h . u| over the F5 JUDGE prompts, clean model, last token "
            "-- the activation mass the rank-1 removal takes out"),
        "target_perturbation_magnitude": amp_target_mag,
        "control_perturbation_magnitudes": amp_ctrl_mags,
        "control_magnitude_mean": amp_ctrl_mean_mag,
        "control_magnitude_max": (float(np.max(amp_ctrl_mags))
                                  if amp_ctrl_mags else None),
        "target_over_control_mean_magnitude_ratio": (
            float(amp_target_mag / amp_ctrl_mean_mag)
            if amp_ctrl_mean_mag > 0 else None),
        "dose_match_tolerance": DOSE_MATCH_TOL,
        "dose_match_tries": amp_ctrl_tries,
        "dose_matched": amp_ctrl_matched,
        "n_dose_matched": int(sum(1 for x in amp_ctrl_matched if x)),
        "rev03_defect_fixed": (
            "rev 0.3 drew AMP controls inside a PC subspace CONTAINING the "
            "target and reported no magnitude at all: the string 'magnitude' "
            "occurs 10 times in atlas_v0_rev03_report.json and none of them "
            "belong to AMP_F5. Under PREREG's own binding reading rule a FAIL "
            "with no magnitude data is uninterpretable."),
        "reading_rule": ("if the target's magnitude is far below the control "
                         "mean, the correct reading of a FAIL is 'the "
                         "comparison was not matched', NOT 'there is no "
                         "amplifier'"),
    }

    txt_amp_cross = gen_condition(model, tok, banks["f5_judge"], device,
                                  eraser_hooks(u_f2_star), max_new)
    cross_amp = _probe(measure_condition(model, tok, banks["f5_judge"],
                                         txt_amp_cross, device, l_star,
                                         measure_dirs), "f5")
    txt_amp_xrail = gen_condition(model, tok, banks["f2_judge"], device,
                                  eraser_hooks(u_f5_star), max_new)
    xrail_amp = _probe(measure_condition(model, tok, banks["f2_judge"],
                                         txt_amp_xrail, device, l_star,
                                         measure_dirs), "f2")
    tests["AMP_F5"] = eval_amp_test(base_f5, tgt_amp, ctrls_amp, cross_amp,
                                    tau_f5, base_f2, xrail_amp, "uF5", "uF2",
                                    readout=amp_readout, min_ctrl=min_ctrl,
                                    quantum=quantum,
                                    magnitude_meta=amp_mag_meta,
                                    readout_viability=amp_readout_viability,
                                    n_averaged=n_averaged,
                                    strict_gates=strict_gates)
    stage_mark("AMP_F5")
    write_report(report, report_path)

    # ---- RS-F5 (increase-sign anchor) -- OPTIONAL in rev 0.4 (D48) -------
    # RS is 1,944 of 3,864 units (50% of the battery) on an observable whose
    # G2 hedge-mass gate operates at 1.7% relative while bf16 logits inject a
    # ~6% multiplicative error per softmax probability (true SNR ~0.28), and
    # which already returned VACUOUS_NO_BRAKE in fp32 at pythia-2.8b (G1
    # p=0.5056, G2 p=0.6983). With RS ON the confirmatory run lands at ~4.0 h
    # BEFORE the D34 calibration and the 20B preflight, i.e. over the window.
    # It is OFF by default and --run-rs turns it back on; turning it on is
    # itself a deviation to be logged, and the verdict LABEL changes because
    # the sign anchor is then in scope (PREREG section 8).
    if run_rs:
        # GATING precondition on the RS FIT half (rev 0.3 review fix D27): whether
        # this model+bank shows a suppression gap at all is a feasibility question,
        # and gating it on the JUDGE half -- the same pairs that supply M2 headroom
        # denominator -- made "headroom > 0" close to automatic and biased rho
        # downward into the pass window. The judge half is measured too, and
        # reported UNCONDITIONED, as a descriptor.
        print("[ablate] RS-F5 precondition (teacher-forced suppression gap, FIT half)")
        rs_pre = rs_precondition(model, tok, banks["rs_lic_fit"],
                                 banks["rs_con_fit"], device, l_star, u_f5_star,
                                 hedge_ids, ctrl_ids, act_ids, res_ids)
        rs_pre["half"] = "fit (GATING)"
        rs_pre_judge = rs_precondition(model, tok, banks["rs_lic_judge"],
                                       banks["rs_con_judge"], device, l_star,
                                       u_f5_star, hedge_ids, ctrl_ids, act_ids,
                                       res_ids)
        rs_pre_judge["half"] = "judge (DESCRIPTIVE ONLY, never gating)"
        print(f"[ablate] RS precondition (fit) holds={rs_pre['holds']} "
              f"(G1 p={rs_pre['G1_wilcoxon_pratt_p']:.4g}, "
              f"G2 p={rs_pre['G2_wilcoxon_pratt_p']:.4g})")

        rs_dirs = {"uF5": u_f5_star}
        con_j = banks["rs_con_judge"]
        lic_j = banks["rs_lic_judge"]

        # COMMON RANDOM NUMBERS across every RS condition (rev 0.3 review fix D29).
        # The rev-0.3 draft passed a DIFFERENT sample_seed to baseline (7000),
        # licensed reference (7100), target (7200) and each control (7300+100*tr).
        # With temperature-0.7 sampling that makes baseline and target continuations
        # differ even under a NULL intervention, so behavioral_change_rate is ~1.0
        # by construction: VACUOUS_NO_BEHAVIORAL_CHANGE could never fire for the
        # anchor test, byte-identity ties could never occur, and unpaired decode
        # noise entered M1 increase and M2 rho -- defeating the entire purpose of
        # the k=5 averaging. One shared seed makes the draws paired, so a null
        # intervention reproduces the baseline text exactly.
        rs_seed = args.seed * 10000 + 7000
        txt_rs_base = gen_condition(model, tok, con_j, device, [], max_new,
                                    n_samples=rs_samples, sample_seed=rs_seed)
        base_rs = measure_condition(model, tok, con_j, txt_rs_base, device, l_star,
                                    rs_dirs, mass_ids)
        txt_rs_ref = gen_condition(model, tok, lic_j, device, [], max_new,
                                   n_samples=rs_samples, sample_seed=rs_seed)
        ref_rs = measure_condition(model, tok, lic_j, txt_rs_ref, device, l_star,
                                   rs_dirs, mass_ids)
        txt_rs = gen_condition(model, tok, con_j, device, eraser_hooks(u_rs_star),
                               max_new, n_samples=rs_samples, sample_seed=rs_seed)
        tgt_rs = measure_condition(model, tok, con_j, txt_rs, device, l_star,
                                   rs_dirs, mass_ids)

        # RS control ensemble = TWO families, both fit on the RS distribution
        # (rev 0.3 review fix D22):
        #   (i) SHUFFLED-LABEL REFITS of u_RS on the RS fit half -- the identical
        #       estimator applied to label-permuted data, i.e. the only control
        #       family that matches the estimation-noise geometry of a 24-vs-24
        #       diff-of-means;
        #   (ii) random unit directions inside the PC subspace OF THE RS FIT
        #       RESIDUALS (not the drive-bank subspace the draft used).
        # The gating control-ensemble p is the max-statistic over BOTH families
        # (conservative); per-family composition and magnitudes are reported.
        # Perturbation-magnitude matching. Rev 0.3 only REPORTED it, and the report
        # showed the controls were 2.5x stronger perturbations than the target
        # (target_over_control_mean_magnitude_ratio 0.3983), which under PREREG's
        # own binding rule made the RS FAIL unreadable. Rev 0.4 (deviation D38)
        # ACTS on it: controls are accept/reject sampled into the target's dose
        # band before they are ever generated. The matrix below is computed once
        # and reused, so matching costs zero GPU generation.
        H_con = residual_feats(model, tok, con_j, device)[:, l_star + 1]

        def _mag(u):
            return float(np.mean(np.abs(H_con @ np.asarray(u, dtype=np.float64))))

        target_mag = _mag(u_rs_star)
        n_shuf = int(round(RS_CTRL_SHUFFLED_FRAC * n_controls))
        n_shuf = max(1, min(n_controls - 1, n_shuf)) if n_controls > 1 else n_controls
        rs_rows_lic = feats["rs_lic_fit"][:, l_star + 1]
        rs_rows_con = feats["rs_con_fit"][:, l_star + 1]
        ctrls_rs, ctrl_dirs_rs, ctrl_family = [], [], []
        rs_ctrl_matched, rs_ctrl_tries = [], []
        for tr in range(n_controls):
            rng = np.random.default_rng(args.seed * 10000 + 200 + tr)
            if tr < n_shuf:
                fam = "shuffled_label_refit"

                def draw_rs(r):
                    return shuffled_label_dir(rs_rows_con, rs_rows_lic, r,
                                              ortho_to=u_f5_star)
            else:
                fam = "rs_fit_pc_subspace"

                def draw_rs(r):
                    return pc_random_dir(V_rs, r, ortho_to=u_f5_star)

            u_rand, _m, tries, matched = dose_matched_draw(
                draw_rs, rng, _mag, target_mag)
            ctrl_dirs_rs.append(u_rand)
            ctrl_family.append(fam)
            rs_ctrl_tries.append(tries)
            rs_ctrl_matched.append(bool(matched))
            txt_c = gen_condition(model, tok, con_j, device, eraser_hooks(u_rand),
                                  max_new, n_samples=rs_samples,
                                  sample_seed=rs_seed)   # common random numbers
            ctrls_rs.append(measure_condition(
                model, tok, con_j, txt_c, device, l_star, rs_dirs, mass_ids))

        ctrl_mags = [_mag(u) for u in ctrl_dirs_rs]
        ctrl_mean_mag = float(np.mean(ctrl_mags)) if ctrl_mags else 0.0
        ctrl_meta = {
            "n_shuffled_label_refit": n_shuf,
            "n_rs_fit_pc_subspace": n_controls - n_shuf,
            "families": ctrl_family,
            "pc_subspace_fit_on": "RS fit residuals (licensed + conflicted) at L*",
            "perturbation_magnitude_metric":
                "mean |h . u| over conflicted JUDGE prompts, clean model, last token",
            "control_perturbation_magnitudes": ctrl_mags,
            "control_magnitude_mean": ctrl_mean_mag,
            "control_magnitude_max": float(max(ctrl_mags)) if ctrl_mags else 0.0,
            "target_over_control_mean_magnitude_ratio": (
                float(target_mag / ctrl_mean_mag) if ctrl_mean_mag > 0 else None),
            "dose_match_tolerance": DOSE_MATCH_TOL,
            "dose_match_tries": rs_ctrl_tries,
            "dose_matched": rs_ctrl_matched,
            "n_dose_matched": int(sum(1 for x in rs_ctrl_matched if x)),
            "common_random_numbers": True,
            "note": ("if the magnitude ratio is far below 1 the controls are "
                     "STRONGER perturbations than the target and a FAIL cannot "
                     "distinguish 'no brake' from 'controls too strong'"),
        }
        tests["RS_F5"] = eval_rs_test(rs_pre, base_rs, tgt_rs, ctrls_rs, ref_rs,
                                      "uF5", pre_judge=rs_pre_judge,
                                      ctrl_meta=ctrl_meta,
                                      target_magnitude=target_mag,
                                      min_ctrl=min_ctrl, quantum=quantum,
                                      n_averaged=n_averaged,
                                      strict_gates=strict_gates)
        stage_mark("RS_F5")
        write_report(report, report_path)
    else:
        report["rs_out_of_scope"] = {
            "run": False,
            "reason": ("RS-F5 is OUT OF SCOPE by default in rev 0.4's second "
                       "pass (deviation D48), not VACUOUS and not FAIL. It is "
                       "50% of the battery's units on an observable whose true "
                       "SNR under bf16 is ~0.28, and it already returned "
                       "VACUOUS_NO_BRAKE in fp32 at pythia-2.8b. Declaring it "
                       "out of scope in advance is honest; running a crippled "
                       "version of the designated sign anchor would not be."),
            "restore": "--run-rs (itself a deviation to be logged)",
            "verdict_consequence": (
                "with RS out of scope the strongest available verdict is "
                "PASS_BOUNDED_ATLAS_V0_F5_RAIL_ONLY, which is explicitly "
                "WEAKER than PASS_BOUNDED_ATLAS_V0 because the increase-sign "
                "anchor -- the only typed signature starvation and attenuation "
                "cannot produce -- was not measured"),
        }

    # ---------------- Stage: CONNECT ----------------
    print("[connect] DR-F5 (L_dr) -> AMP-F5 site (L*), clean-pass selectivity")
    tests["CONN_DRF5_to_AMPF5"] = eval_conn_test(
        base_f5, tgt_dr5, ctrls_dr5, "uF5", "uF2", rand_keys,
        min_ctrl=min_ctrl, quantum=quantum, n_averaged=n_averaged,
        strict_gates=strict_gates)
    tests["CONN_DRF5_to_AMPF5"]["upstream"] = {
        "kind": "mlp_intermediate_cover", "block": l_dr}
    tests["CONN_DRF5_to_AMPF5"]["downstream_site_block"] = l_star
    report["tests"] = tests
    write_report(report, report_path)

    # ---------------- Stage: HARNESS SANITY (outside aggregate) ----------
    sanity = {}

    print("[sanity] MEM copy heads (generic transformer phenomenon)")
    usable_all = mem_usable_items(tok, mem_items)
    half = len(usable_all) // 2
    mem_disc, mem_judge = usable_all[:half], usable_all[half:]
    if len(mem_disc) >= 3 and len(mem_judge) >= 3:
        mem_scores = mem_head_scores(model, tok, mem_disc, device, n_blocks, n_heads)
        mem_heads = top_heads(mem_scores, topk_heads)
        base_copy = copy_accuracy(model, tok, mem_judge, device, [])
        mem_specs = head_hook_specs(layers, mem_heads, head_dim)
        abl_copy = copy_accuracy(model, tok, mem_judge, device, mem_specs)
        ctrl_copies, ctrl_head_counts = [], []
        for tr in range(n_controls):
            rng = np.random.default_rng(args.seed * 10000 + 400 + tr)
            rnd = random_matched_heads(mem_heads, n_heads, rng,
                                       n_layers=n_blocks)
            ctrl_head_counts.append(len(rnd))
            ctrl_copies.append(copy_accuracy(
                model, tok, mem_judge, device,
                head_hook_specs(layers, rnd, head_dim)))
        drop = base_copy - abl_copy
        ctrl_drops = [base_copy - c for c in ctrl_copies]
        p_mem = control_ensemble_p(drop, ctrl_drops)
        mem_res = {
            "n_heads_ablated": len(mem_heads),
            "control_n_heads_ablated": ctrl_head_counts,
            "control_head_count_matched": bool(
                all(c == len(mem_heads) for c in ctrl_head_counts)),
            "heads": mem_heads,
            "n_discovery_items": len(mem_disc),
            "n_judgment_items": len(mem_judge),
            "drop_resolution": float(1.0 / max(1, len(mem_judge))),
            "baseline_copy_acc": float(base_copy),
            "ablated_copy_acc": float(abl_copy),
            "targeted_drop": float(drop),
            "control_drops": [float(d) for d in ctrl_drops],
            "max_control_drop": float(max(ctrl_drops)),
            "control_ensemble_p": p_mem,
        }
        if base_copy < MEM_BASELINE_MIN:
            mem_res["status"] = "VACUOUS"
            mem_res["reason"] = (f"baseline copy accuracy {base_copy:.2f} below "
                                 f"precondition {MEM_BASELINE_MIN}")
        else:
            ok = (drop >= MEM_DROP_MIN) and (drop > max(ctrl_drops)) \
                and (p_mem < CONTROL_PERM_ALPHA)
            mem_res["status"] = "SANITY_PASS" if ok else "SANITY_FAIL"
        mem_res["rev02_disclosure"] = (
            "On rev 0.2 the MEM targeted drop was NEGATIVE (-0.1667: ablating "
            "the top-4 copy heads IMPROVED copy accuracy) against a max "
            "control drop of 0.0, at n_judgment_items = 6 and "
            "baseline_copy_acc exactly 0.50. That is a WRONG-SIGNED result "
            "from the head-ablation instrument on the most generic phenomenon "
            "in the battery, and none of the rev-0.3 MEM changes (higher "
            "baseline gate, control-ensemble p, 20/20 split, fractional head "
            "budget) address the SIGN. Disclosed here per the same rule that "
            "governs deviation D18.")
    else:
        mem_res = {"status": "VACUOUS",
                   "reason": "not enough usable copy items after tokenization"}
    sanity["MEM_SANITY"] = mem_res

    print("[sanity] CHECK induction gate (held-out judgment sequences)")
    rng_disc = np.random.default_rng(args.seed + 777)
    rng_judge = np.random.default_rng(args.seed + 778)   # held-out
    seqs_disc = build_induction_seqs(rng_disc, n_seq, seg_len=12)
    seqs_judge = build_induction_seqs(rng_judge, n_seq, seg_len=12)
    ind_scores = induction_head_scores(model, seqs_disc, device, n_blocks, n_heads)
    check_heads = top_heads(ind_scores, topk_heads)
    base_gate = float(np.mean(gate_scores(model, seqs_judge, device, [])))
    check_specs = head_hook_specs(layers, check_heads, head_dim)
    abl_gate = float(np.mean(gate_scores(model, seqs_judge, device, check_specs)))
    ctrl_gates, check_ctrl_counts = [], []
    for tr in range(n_controls):
        rng = np.random.default_rng(args.seed * 10000 + 500 + tr)
        rnd = random_matched_heads(check_heads, n_heads, rng, n_layers=n_blocks)
        check_ctrl_counts.append(len(rnd))
        ctrl_gates.append(float(np.mean(gate_scores(
            model, seqs_judge, device, head_hook_specs(layers, rnd, head_dim)))))
    gate_drop = base_gate - abl_gate
    ctrl_gate_drops = [base_gate - g for g in ctrl_gates]
    p_check = control_ensemble_p(gate_drop, ctrl_gate_drops)
    check_res = {
        "n_heads_ablated": len(check_heads),
        "control_n_heads_ablated": check_ctrl_counts,
        "control_head_count_matched": bool(
            all(c == len(check_heads) for c in check_ctrl_counts)),
        "heads": check_heads,
        "n_sequences": n_seq,
        "baseline_gate_score_nats": base_gate,
        "ablated_gate_score_nats": abl_gate,
        "targeted_drop": float(gate_drop),
        "control_drops": [float(d) for d in ctrl_gate_drops],
        "max_control_drop": float(max(ctrl_gate_drops)),
        "control_ensemble_p": p_check,
        "criterion": (f"control-ensemble p < {CONTROL_PERM_ALPHA} AND absolute "
                      f"drop >= {CHECK_DROP_MIN_NATS} nats (rev 0.3 re-anchor)"),
        "legacy_rev02_fraction_criterion": {
            "rule": f"drop >= {CHECK_DROP_FRAC_LEGACY} x baseline",
            "would_pass": bool(gate_drop >= CHECK_DROP_FRAC_LEGACY * base_gate),
            "note": ("reported so the rev-0.2 vs rev-0.3 comparison stays "
                     "auditable; the re-anchor WAS INFORMED BY REV 0.2 RESULTS "
                     "(3.559-nat drop vs 0.175 best control, ~20x selective "
                     "margin, failing only the 50%-of-baseline bar)")},
    }
    if base_gate < CHECK_GATE_MIN_NATS:
        check_res["status"] = "VACUOUS"
        check_res["reason"] = (f"baseline gate score {base_gate:.2f} nats below "
                               f"precondition {CHECK_GATE_MIN_NATS} "
                               "(unreachable-threshold trap)")
    else:
        ok = (gate_drop >= CHECK_DROP_MIN_NATS) and (p_check < CONTROL_PERM_ALPHA)
        check_res["status"] = "SANITY_PASS" if ok else "SANITY_FAIL"
    sanity["CHECK_SANITY"] = check_res
    report["harness_sanity"] = sanity
    write_report(report, report_path)

    # ---------------- Stage: REPORT ----------------
    core_order = [n for n in ("DR_F5", "DR_F2", "AMP_F5", "RS_F5",
                              "CONN_DRF5_to_AMPF5") if n in tests]
    evaluable = [n for n in core_order
                 if tests[n].get("status") in ("PASS", "FAIL", "CONFOUNDED")]
    n_pass = sum(1 for n in evaluable if tests[n]["status"] == "PASS")
    n_eval = len(evaluable)
    fraction = (n_pass / n_eval) if n_eval else 0.0

    rs_status = (tests["RS_F5"].get("status") if "RS_F5" in tests
                 else "OUT_OF_SCOPE_NOT_RUN")
    rs_ok_or_vacuous = rs_status in ("PASS", "VACUOUS", "VACUOUS_NO_BRAKE",
                                     "VACUOUS_NO_BEHAVIORAL_CHANGE",
                                     "VACUOUS_NO_PASS_REGION",
                                     "VACUOUS_CONTROL_ENSEMBLE_DEGRADED",
                                     "VACUOUS_DOSE_UNMATCHED",
                                     "VACUOUS_BELOW_INSTRUMENT_RESOLUTION")

    kill = None
    if n_eval < 3:
        status = "GREY_ATLAS_V0_INSUFFICIENT_EVALUABLE"
    elif (not run_rs) and fraction > 0.5 and (n_eval - n_pass) <= 1:
        # D48: with the sign anchor OUT OF SCOPE the strongest reachable verdict
        # is explicitly WEAKER and carries a different label, so nobody can read
        # an F5-rail result as the full battery's PASS_BOUNDED_ATLAS_V0.
        status = "PASS_BOUNDED_ATLAS_V0_F5_RAIL_ONLY"
    elif (not run_rs) and fraction <= 0.5:
        status = "NULL_ATLAS_V0"
    elif not run_rs:
        status = "GREY_ATLAS_V0"
    elif (rs_status == "FAIL") and (fraction <= 0.5):
        status = "NULL_ATLAS_V0"
        kill = ("KILL condition met: the increase-sign anchor (RS) was evaluable "
                "and FAILED against matched controls AND the evaluable pass "
                "fraction is <= 0.5. Directional component-type labeling adds "
                "nothing over generic localization at this substrate; "
                "CAS-PCBA internal labeling does not proceed to v1 in its "
                "current form.")
    elif fraction <= 0.5:
        status = "NULL_ATLAS_V0"
    elif n_eval >= 4 and (n_eval - n_pass) <= 1 and rs_ok_or_vacuous:
        status = "PASS_BOUNDED_ATLAS_V0"
    else:
        status = "GREY_ATLAS_V0"

    dr_amp_separate = (
        tests.get("DR_F5", {}).get("starvation_signature_holds") is True
        and tests.get("AMP_F5", {}).get("attenuation_signature_holds") is True)
    if (rs_status == "FAIL") and (not dr_amp_separate) and n_eval >= 4:
        status = "NULL_ATLAS_V0"
        kill = ("KILL condition met: the increase-sign anchor (RS) failed AND "
                "the DR/AMP presence-vs-magnitude discriminator did not "
                "separate; the vocabulary is reading as decoration on generic "
                "interventions.")

    report["tests"] = tests
    report["harness_sanity"] = sanity
    report["aggregate"] = {
        "core_test_order": core_order,
        "n_evaluable": n_eval,
        "n_pass": n_pass,
        "fraction_pass_descriptive": float(fraction),
        "non_independence_caveat": AGGREGATE_CAVEAT,
        "rs_sign_anchor_status": rs_status,
        "rs_sign_anchor_in_scope": bool(run_rs),
        "verdict_label_note": (
            "PASS_BOUNDED_ATLAS_V0_F5_RAIL_ONLY is a DELIBERATELY WEAKER label "
            "than PASS_BOUNDED_ATLAS_V0: with --run-rs off the increase-sign "
            "anchor -- the only typed signature that starvation and attenuation "
            "cannot produce -- was never measured, so the battery cannot "
            "discriminate a typed component atlas from selective localization "
            "of F5-type content. It licenses nothing the full battery would."
            if not run_rs else
            "the sign anchor was in scope; the standard rev-0.2/0.3 verdict "
            "labels apply unchanged"),
        "harness_sanity_excluded_from_aggregate": True,
        "status": status,
        "kill_statement_triggered": kill,
        # Ties are reported from the BASELINE arm, where a zero means exactly
        # "the intervention left this prompt's text byte-identical" (rev 0.3
        # review fix D23). The control-mean arm's tie rate is near 0 whatever
        # happens -- an exact zero there would require the target text to equal
        # ALL C heterogeneous control texts -- so reporting it as THE tie rate
        # was misleading. Both are exposed.
        "tie_rate_by_test_baseline_arm": {
            n: tests[n].get("paired_arms", {}).get(
                "stats_vs_baseline", {}).get("tie_rate") for n in core_order},
        "byte_identical_pairs_by_test": {
            n: tests[n].get("paired_arms", {}).get(
                "stats_vs_baseline", {}).get("n_byte_identical_forced_zero")
            for n in core_order},
        "tie_rate_by_test_control_mean_arm": {
            n: tests[n].get("wilcoxon_pratt_stats", {}).get("tie_rate")
            for n in core_order},
        "behavioral_change_by_test": {
            n: tests[n].get("behavioral_change_rate") for n in core_order},
        "paired_p_by_test": {
            n: {"vs_control_mean": tests[n].get("paired_arms", {}).get(
                    "p_vs_control_mean"),
                "vs_baseline": tests[n].get("paired_arms", {}).get(
                    "p_vs_baseline")} for n in core_order},
        # ---- rev 0.4 additions ----
        "primary_readout_by_test": {
            n: tests[n].get("primary_readout") for n in core_order},
        "measurability_by_test": {
            n: tests[n].get("measurability") for n in core_order},
        "measurability_note": MEASURABILITY_NOTE,
        "control_magnitude_ratio_by_test": {
            n: (tests[n].get("control_magnitude") or {}).get(
                "target_over_control_mean_magnitude_ratio")
            for n in core_order},
        "control_guard_kept_by_test": {
            n: (tests[n].get("control_guard") or {}).get("n_kept")
            for n in core_order},
        "pass_window_by_test": {
            n: tests[n].get("pass_window") for n in core_order},
        "dr_f2_rail": ("RUN" if run_dr_f2 else
                       "DROPPED by default in rev 0.4 (deviation D40); its "
                       "COVER is still computed so DR-F5's cross-cover control "
                       "and both cross-rail selectivity conditions are "
                       "unaffected. Dropping it is justified partly by rev-0.3 "
                       "OUTCOMES and declared as such."),
        "rev04_control_framing": (
            "The rev-0.4 control ensembles are, by construction, LESS "
            "destructive nulls than rev 0.3's: they are orthogonalized against "
            "the target, dose-matched on removed activation mass, and "
            "damage-guarded. The honest framing is that the rev-0.3 AMP null "
            "was CONTAMINATED and UNDOSED -- evidenced by the code asymmetry "
            "with RS, which already passed ortho_to for both its families -- "
            "not that rev 0.4 made the test easier. Any PASS must be read "
            "together with control_magnitude_ratio_by_test and the per-control "
            "damage statistics, or it reads as a control-weakening artifact."),
        "rs_surface_disclosure": (
            "u_RS is plausibly a PROHIBITION-VOCABULARY direction: the RS "
            "licensing/blocking clauses are strongly polar (allows/forbids, "
            "permits/bars, approved/stalled), so the char-ngram control on the "
            "RS bank is expected to be near 1.0. Section 6's interpretation "
            "rule covers this generically, but it is stated here for RS "
            "specifically because RS is the sign anchor and the verdict leans "
            "on it. See surface_control.rs_conflicted_vs_licensed."),
        "language": ("Every PASS is worded 'causally supports the <TYPE> "
                     "labeling'; never 'found THE neurons' or 'the circuit'."),
        "cas_specificity": ("GREY. Nothing here separates drive semantics from "
                            "topic/lexical semantics; see PREREG section 6."),
    }
    stage_mark("report")
    report["provenance"]["runtime_seconds"] = round(time.time() - t0, 1)
    report["provenance"]["stage_elapsed_seconds"] = stage_times
    report["provenance"]["peak_vram"] = peak_vram_gib()
    if args.smoke:
        report["provenance"]["note"] = ("SMOKE RUN -- mechanical validation only; "
                                        "numbers are never evidence")

    write_report(report, report_path)
    print(f"[done] status={status} pass={n_pass}/{n_eval} "
          f"report={report_path} "
          f"({report['provenance']['runtime_seconds']}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
