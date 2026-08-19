#!/usr/bin/env python
"""COMPONENT ATLAS v0 (rev 0.3) -- discover -> label -> ablate -> connect -> report.

First typed map from a model's internal parts to CAS-PCBA component labels,
judged by preregistered directional ablation predictions vs matched controls.

FRAME (owner-ratified): parts are the MODEL'S (discovered functionally), names
are OURS (CAS-PCBA types), ablation is the JUDGE. A label sticks only if its
preregistered directional ablation prediction holds vs matched controls.
Language discipline: "causally supports the labeling", never "found THE
neurons". This does NOT claim the model encodes CAS.

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

Preregistration: PREREG_COMPONENT_ATLAS_V0.md (same directory, rev 0.3). This
script is the executable copy of that document; any divergence is a bug against
prereg.

Target environment: RunPod research venv, HF_HUB_CACHE=/workspace/cas-hf-cache.
Run:
  python component_atlas_v0.py                       # full (pythia-2.8b, GPU)
  python component_atlas_v0.py --smoke               # tiny mechanical check
Output: atlas_v0_rev03_report.json in --out dir (default: script directory).
The rev-0.2 artifact atlas_v0_report.json is NEVER overwritten.
No internet beyond the HF cache (--local-files-only supported).
"""

import argparse
import hashlib
import json
import math
import os
import re
import sys
import time
from contextlib import contextmanager

import numpy as np
import torch

SCHEMA_VERSION = "component_atlas_v0.3"
REPORT_FILENAME = "atlas_v0_rev03_report.json"
PREFLIGHT_FILENAME = "atlas_v0_rev03_preflight.json"
DEFAULT_MODEL = "EleutherAI/pythia-2.8b"
PINNED_REVISIONS = {
    # Stage 27N pinned revision for pythia-1b (rev 0.2 model; kept for reruns).
    "EleutherAI/pythia-1b": "f73d7dcc545c8bd326d8559c8ef84ffe92fea6b2",
    # pythia-2.8b: corroborated by stage14_pythia28b_activations_manifest_20260518.json
    # and stage14_weight_geometry_alignment_20260519.json (branch
    # experiment/cas-probe-pythia), mirrored at HEAD in
    # docs/working/gate2_closure/GATE2_ITEM1_CLAIMS_MATRIX.md.
    "EleutherAI/pythia-2.8b": "2a259cdd96a4beb1cdf467512e3904197345f6a9",
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
    "without rerunning. Rev 0.3 is judged on a DIFFERENT model (pythia-2.8b) "
    "with RE-DRAWN banks; it does not amend or supersede the rev-0.2 "
    "NULL_ATLAS_V0 result on pythia-1b, which stands as reported."
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
LAYER_SWEEP_MIN_FRAC = 0.25     # sweep_lo = round(frac * n_blocks)  (16 -> 4)
L_STAR_MIN_FRAC = 0.375         # L_STAR_MIN = round(frac * n_blocks) (16 -> 6)
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
RS_N_SAMPLES = 5                # rev 0.3: seeded sampled continuations per prompt
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
CONTROLS_MIN_STRICT = 20

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

def load_model_and_tokenizer(model_id, revision, device, local_files_only):
    from transformers import AutoModelForCausalLM, AutoTokenizer

    kwargs = dict(
        attn_implementation="eager",
        use_safetensors=True,
        low_cpu_mem_usage=True,
        local_files_only=local_files_only,
    )
    if revision:
        kwargs["revision"] = revision
    try:
        model = AutoModelForCausalLM.from_pretrained(
            model_id, dtype=torch.float32, **kwargs)
    except TypeError:
        # older transformers: dtype kw not accepted yet
        model = AutoModelForCausalLM.from_pretrained(
            model_id, torch_dtype=torch.float32, **kwargs)
    tok = AutoTokenizer.from_pretrained(
        model_id, revision=revision, local_files_only=local_files_only)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    model.to(device)
    model.eval()
    return model, tok


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
    """h <- h - (h.u)u at ALL positions (learned-direction removal)."""
    u = torch.tensor(np.asarray(u_np, dtype=np.float32))

    def fn(h):
        uu = u.to(device=h.device, dtype=h.dtype)
        proj = torch.matmul(h, uu).unsqueeze(-1) * uu
        return h - proj

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
        clean re-forward, never with hooks active.

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
    for p, c in zip(prompts, continuations):
        enc = tok(p + c, return_tensors="pt").to(device)
        n_prompt = tok(p, return_tensors="pt")["input_ids"].shape[1]
        with torch.no_grad():
            res = model(**enc, output_hidden_states=True)
        hs = res.hidden_states[block + 1][0].float().cpu().numpy()
        seg = hs[n_prompt:] if hs.shape[0] > n_prompt else hs[-1:]
        mv = (seg @ D.T).mean(axis=0)
        for i, n in enumerate(names):
            out[n].append(float(mv[i]))
        if mass_t:
            logits = res.logits[0].float()
            T = int(logits.shape[0])
            lo = max(n_prompt - 1, 0)
            hi = max(T - 1, lo + 1)
            step = logits[lo:hi] if hi > lo else logits[-1:]
            probs = torch.softmax(step, dim=-1)
            for k, ids in mass_t.items():
                mout[k].append(float(
                    probs.index_select(1, ids.to(probs.device)).sum(-1).mean()))
    return ({n: np.asarray(v) for n, v in out.items()},
            {k: np.asarray(v) for k, v in mout.items()})


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
    projs, masses = clean_pass(model, tok, flat_prompts, flat_texts, device,
                               block, dirs, mass_ids)
    gid = np.asarray(gid)
    ngroups = len(prompts)

    def group_mean(arr):
        return np.asarray([float(np.mean(arr[gid == i])) for i in range(ngroups)])

    per_hedge = np.asarray([float(hedge_count(s)) for s in flat_texts])
    per_coh = np.asarray([distinct_ratio(s) for s in flat_texts])
    per_rep = np.asarray([distinct_ngram_ratio(s, 4) for s in flat_texts])
    return {
        "proj": {k: [float(x) for x in group_mean(v)] for k, v in projs.items()},
        "mass": {k: [float(x) for x in group_mean(v)] for k, v in masses.items()},
        "hedges": [float(x) for x in group_mean(per_hedge)],
        "mean_hedge": float(per_hedge.mean()) if per_hedge.size else 0.0,
        "coherence": float(per_coh.mean()) if per_coh.size else 0.0,
        "repetition": float(per_rep.mean()) if per_rep.size else 0.0,
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
            att = out.attentions[L][0]  # [heads, T, T]
            sel = att[:, -1, :].index_select(1, kp.to(att.device))
            scores[L] += sel.sum(-1).float().cpu().numpy()
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
            att = out.attentions[L][0]  # [heads, T, T]
            vals = [att[:, seg + j, j + 1] for j in range(seg - 1)]
            scores[L] += torch.stack(vals, 0).mean(0).float().cpu().numpy()
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
    b = np.asarray(base["proj"][key], dtype=np.float64)
    t = np.asarray(tgt["proj"][key], dtype=np.float64)
    ctrl_mean = np.mean([c["proj"][key] for c in ctrls], axis=0) if ctrls else b
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


def eval_dr_test(base, tgt, ctrls, cross, tau, base_other, xrail, key, okey):
    """DR starvation with gated cross-rail selectivity."""
    b = np.asarray(base["proj"][key])
    t = np.asarray(tgt["proj"][key])
    drop = float(b.mean() - t.mean())
    ctrl_drops = [float(b.mean() - np.mean(c["proj"][key])) for c in ctrls]
    cross_drop = float(b.mean() - np.mean(cross["proj"][key]))
    paired = _paired_block(base, tgt, ctrls, key, sign=+1)
    p_w = paired["p_vs_control_mean"]
    w_stats = paired["stats_vs_control_mean"]
    p_ctrl = control_ensemble_p(drop, ctrl_drops)
    change = behavioral_change_rate(base["texts"], tgt["texts"])

    base_rate = rate_above(b, tau)
    tgt_rate = rate_above(t, tau)
    d_target = effect_size(b, t)
    d_xrail = effect_size(base_other["proj"][okey], xrail["proj"][okey])

    res = {
        "baseline_mean_proj": float(b.mean()),
        "target_mean_proj": float(t.mean()),
        "targeted_drop": drop,
        "matched_control_drops": ctrl_drops,
        "max_matched_control_drop": float(max(ctrl_drops)),
        "cross_cover_drop": cross_drop,
        "wilcoxon_pratt_p": p_w,
        "wilcoxon_pratt_stats": w_stats,
        "paired_arms": paired,
        "control_ensemble_p": p_ctrl,
        "n_controls": len(ctrls),
        "legacy_sign_test_p_reported_only": sign_test_p(
            paired["diffs_vs_control_mean"]),
        "behavioral_change_rate": change,
        "baseline_presence_rate": float(base_rate),
        "target_presence_rate": float(tgt_rate),
        "effect_size_target": d_target,
        "effect_size_cross_rail": d_xrail,
        "selectivity_gate": f"|d_cross_rail| <= {SELECTIVITY_MAX_RATIO} x d_target",
        "coherence_target": tgt["coherence"],
        "repetition_target": tgt["repetition"],
        "sample_texts_target": tgt["sample_texts"],
    }
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
    beats_controls = (drop > max(ctrl_drops)) and (drop > cross_drop) \
        and paired["both_arms_hold"] and (p_ctrl < CONTROL_PERM_ALPHA)
    starves = tgt_rate < DR_PRESENCE_COLLAPSE * base_rate
    selective = (d_target > 0) and (abs(d_xrail) <= SELECTIVITY_MAX_RATIO * d_target)
    res["beats_matched_and_cross_controls"] = bool(beats_controls)
    res["starvation_signature_holds"] = bool(starves)
    res["selectivity_gate_holds"] = bool(selective)
    res["status"] = "PASS" if (beats_controls and starves and selective) else "FAIL"
    return res


def eval_amp_test(base, tgt, ctrls, cross, tau, base_other, xrail, key, okey):
    """AMP attenuation: magnitude shrinks, presence retained, selectivity gated."""
    b = np.asarray(base["proj"][key])
    t = np.asarray(tgt["proj"][key])
    drop = float(b.mean() - t.mean())
    ctrl_drops = [float(b.mean() - np.mean(c["proj"][key])) for c in ctrls]
    cross_drop = float(b.mean() - np.mean(cross["proj"][key]))
    paired = _paired_block(base, tgt, ctrls, key, sign=+1)
    p_w = paired["p_vs_control_mean"]
    w_stats = paired["stats_vs_control_mean"]
    p_ctrl = control_ensemble_p(drop, ctrl_drops)
    change = behavioral_change_rate(base["texts"], tgt["texts"])

    base_rate = rate_above(b, tau)
    tgt_rate = rate_above(t, tau)
    d_target = effect_size(b, t)
    d_xrail = effect_size(base_other["proj"][okey], xrail["proj"][okey])

    res = {
        "baseline_mean_proj": float(b.mean()),
        "target_mean_proj": float(t.mean()),
        "targeted_drop": drop,
        "matched_control_drops": ctrl_drops,
        "max_matched_control_drop": float(max(ctrl_drops)),
        "cross_direction_drop": cross_drop,
        "wilcoxon_pratt_p": p_w,
        "wilcoxon_pratt_stats": w_stats,
        "paired_arms": paired,
        "control_ensemble_p": p_ctrl,
        "n_controls": len(ctrls),
        "legacy_sign_test_p_reported_only": sign_test_p(
            paired["diffs_vs_control_mean"]),
        "behavioral_change_rate": change,
        "baseline_presence_rate": float(base_rate),
        "target_presence_rate": float(tgt_rate),
        "effect_size_target": d_target,
        "effect_size_cross_rail": d_xrail,
        "coherence_target": tgt["coherence"],
        "repetition_target": tgt["repetition"],
        "sample_texts_target": tgt["sample_texts"],
    }
    if base_rate < BASELINE_PRESENCE_MIN:
        res["status"] = "VACUOUS"
        res["reason"] = (f"baseline presence rate {base_rate:.2f} below "
                         f"precondition {BASELINE_PRESENCE_MIN}")
        return res
    if change < BEHAVIORAL_CHANGE_MIN:
        res["status"] = "VACUOUS_NO_BEHAVIORAL_CHANGE"
        res["reason"] = (f"only {change:.2f} of judge prompts changed text under "
                         f"the targeted intervention (< {BEHAVIORAL_CHANGE_MIN})")
        return res
    if tgt["coherence"] < COHERENCE_MIN or tgt["repetition"] < REPETITION_MIN:
        res["status"] = "CONFOUNDED"
        res["reason"] = ("target condition failed the coherence and/or "
                         "repetition guard (fluency / degenerate-loop confound)")
        return res
    beats_controls = (drop > max(ctrl_drops)) and (drop > cross_drop) \
        and paired["both_arms_hold"] and (p_ctrl < CONTROL_PERM_ALPHA)
    retains = tgt_rate >= AMP_PRESENCE_RETAIN * base_rate
    selective = (d_target > 0) and (abs(d_xrail) <= SELECTIVITY_MAX_RATIO * d_target)
    res["beats_matched_and_cross_controls"] = bool(beats_controls)
    res["attenuation_signature_holds"] = bool(retains)
    res["selectivity_gate_holds"] = bool(selective)
    res["status"] = "PASS" if (beats_controls and retains and selective) else "FAIL"
    return res


def eval_rs_test(pre, base_con, tgt, ctrls, ref_lic, key,
                 pre_judge=None, ctrl_meta=None, target_magnitude=None):
    """RS-F5 rev 0.3: the increase-sign anchor, redesigned.

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
    b = np.asarray(base_con["proj"][key])
    t = np.asarray(tgt["proj"][key])
    r = np.asarray(ref_lic["proj"][key])
    inc = float(t.mean() - b.mean())
    ctrl_incs = [float(np.mean(c["proj"][key]) - b.mean()) for c in ctrls]
    paired = _paired_block(base_con, tgt, ctrls, key, sign=-1)
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
    ctrl_mass_drops = [float(hm_b - mean_mass(c, "hedge")) for c in ctrls]
    ctrl_mass_lrs = [_lr(hm_b, mean_mass(c, "hedge")) for c in ctrls]
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


def eval_conn_test(base, tgt, ctrls, key, okey, rand_keys):
    """CONN: upstream DR-F5 cut selectively starves the downstream AMP site."""
    d_target = effect_size(base["proj"][key], tgt["proj"][key])
    d_other = effect_size(base["proj"][okey], tgt["proj"][okey])
    d_rand = [effect_size(base["proj"][rk], tgt["proj"][rk]) for rk in rand_keys]
    d_ctrl_covers = [effect_size(base["proj"][key], c["proj"][key]) for c in ctrls]
    paired = _paired_block(base, tgt, ctrls, key, sign=+1)
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
        "max_matched_cover_effect": float(max(d_ctrl_covers)) if d_ctrl_covers else 0.0,
        "wilcoxon_pratt_p": p_w,
        "wilcoxon_pratt_stats": w_stats,
        "control_ensemble_p": p_ctrl,
        "paired_arms": paired,
        "legacy_sign_test_p_reported_only": sign_test_p(
            paired["diffs_vs_control_mean"]),
        "behavioral_change_rate": change,
        "note": ("clean-pass only; correlated with DR-F5 (shared bank and "
                 "direction) -- counted with that caveat in the aggregate"),
    }
    if change < BEHAVIORAL_CHANGE_MIN:
        res["status"] = "VACUOUS_NO_BEHAVIORAL_CHANGE"
        res["reason"] = (f"only {change:.2f} of judge prompts changed text under "
                         f"the upstream cut (< {BEHAVIORAL_CHANGE_MIN})")
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
    ap = argparse.ArgumentParser(description="COMPONENT ATLAS v0 (rev 0.3)")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--revision", default=None,
                    help="HF revision; defaults to the pinned revision for known models")
    ap.add_argument("--smoke", action="store_true",
                    help="tiny mechanical run; never evidence")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--device", default=None)
    ap.add_argument("--out", default=None, help="output directory")
    ap.add_argument("--max-new-tokens", type=int, default=32)
    ap.add_argument("--controls", type=int, default=24,
                    help=("matched control trials per test. The control-ensemble "
                          "p floor is 1/(C+1) and the criterion is STRICT (< "
                          f"alpha), so C >= {CONTROLS_MIN_STRICT} is required: "
                          "C=19 gives exactly 0.0500, which is NOT < 0.05 and "
                          "makes every core test unpassable. C=24 gives 0.0400."))
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


def derive_layer_params(n_blocks, n_heads):
    """Depth/width-FRACTION resolution of the rev-0.2 absolute constants.

    At n_blocks=16 this returns sweep_lo=4, L_star_min=6, dr_offset=4 and (with
    n_heads=8) topk_heads=4 -- bit-identical to rev 0.2. At 32 blocks x 32
    heads it returns 8 / 12 / 8 / 31, preserving the RELATIVE geometry the
    design was built on (DR sits 25% of depth upstream of AMP, not 12.5%).
    """
    sweep_lo = max(1, int(round(LAYER_SWEEP_MIN_FRAC * n_blocks)))
    l_star_min = max(2, int(round(L_STAR_MIN_FRAC * n_blocks)))
    l_star_max = min(n_blocks - 2,
                     max(l_star_min, int(round(L_STAR_MAX_FRAC * n_blocks))))
    dr_offset = max(1, int(round(DR_OFFSET_FRAC * n_blocks)))
    topk = max(TOPK_HEADS_MIN, int(round(TOPK_HEADS_FRAC * n_blocks * n_heads)))
    return sweep_lo, l_star_min, l_star_max, dr_offset, topk


def derive_cover_k(intermediate):
    """COVER_K as a FRACTION of the MLP intermediate width (rev 0.3, D20).

    8192 -> 32 (bit-identical to rev 0.2's literal "Top-32"); 10240 -> 40. The
    rev-0.3 draft left COVER_K absolute at 32, which would have made the DR
    rail cut 0.31% of the layer at pythia-2.8b against 0.39% at pythia-1b -- a
    20% relative WEAKENING of the one intervention whose rev-0.2 behavioural
    change rate (~0.50) was already below the new 0.60 precondition.
    """
    return max(COVER_K_MIN, int(round(COVER_K_FRAC * int(intermediate))))


def main():
    args = parse_args()
    t0 = time.time()
    device = args.device or ("cuda" if torch.cuda.is_available() else "cpu")
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    # Pin the fp32 matmul path explicitly. torch>=2.0 already defaults these to
    # False, but PREREG section 1's determinism/precision argument ASSUMES it,
    # and an assumed default is not a pinned one (review MINOR).
    try:
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
    except Exception:  # pragma: no cover - CPU-only builds
        pass

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
    report_path = os.path.join(out_dir, REPORT_FILENAME)
    if args.preflight:
        report_path = os.path.join(out_dir, PREFLIGHT_FILENAME)

    n_controls = 2 if args.smoke else args.controls
    max_new = 10 if args.smoke else args.max_new_tokens
    n_conn_dirs = 3 if args.smoke else max(n_controls, CONTROLS_MIN_STRICT)
    rs_samples = 2 if args.smoke else max(1, args.rs_samples)

    # Control-ensemble floor guard (review MAJOR). The criterion is a STRICT
    # inequality against 1/(C+1); at C=19 the floor is EXACTLY 0.0500, so the
    # documented "reduced fallback --controls 19" would have produced a full-
    # cost run in which every core test was unpassable by arithmetic. Abort
    # loudly rather than burn ~2 h on an unpassable configuration.
    if (not args.smoke) and n_controls < CONTROLS_MIN_STRICT:
        print(f"[abort] --controls {n_controls} < {CONTROLS_MIN_STRICT}: the "
              f"control-ensemble p floor 1/(C+1) = {1.0/(n_controls+1):.4f} is "
              f"not strictly below alpha={CONTROL_PERM_ALPHA}; every core test "
              "would be unpassable by arithmetic.")
        write_report({"schema_version": SCHEMA_VERSION,
                      "aggregate": {
                          "status": "ABORT_CONTROL_FLOOR",
                          "n_controls": n_controls,
                          "control_ensemble_p_floor": 1.0 / (n_controls + 1),
                          "required_min_controls": CONTROLS_MIN_STRICT}},
                     report_path)
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

    print(f"[load] {args.model} rev={revision} device={device}")
    model, tok = load_model_and_tokenizer(
        args.model, revision, device, args.local_files_only)
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
            "provenance": {
                "model": args.model, "revision": revision,
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

    config_sha = sha_of({
        "schema": SCHEMA_VERSION, "COVER_K_FRAC": COVER_K_FRAC,
        "LAYER_SWEEP_MIN_FRAC": LAYER_SWEEP_MIN_FRAC,
        "L_STAR_MIN_FRAC": L_STAR_MIN_FRAC, "L_STAR_MAX_FRAC": L_STAR_MAX_FRAC,
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
                         "n_seq": n_seq}})

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
            "n_controls": n_controls,
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
                "fractions": {"sweep": LAYER_SWEEP_MIN_FRAC,
                              "l_star_min": L_STAR_MIN_FRAC,
                              "l_star_max": L_STAR_MAX_FRAC,
                              "dr_offset": DR_OFFSET_FRAC,
                              "topk_heads": TOPK_HEADS_FRAC,
                              "cover_k": COVER_K_FRAC}},
            "control_ensemble_p_floor": float(1.0 / (n_controls + 1)),
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
    best_margin = float(max(mean_margins))
    tied_margin = [sweep_blocks[i] for i, v in enumerate(mean_margins)
                   if abs(v - best_margin) <= 1e-12]
    best_acc = float(max(mean_accs))
    tied_acc = [sweep_blocks[i] for i, v in enumerate(mean_accs)
                if abs(v - best_acc) <= 1e-12]
    # Preregistered tie-break on an exact margin tie: SHALLOWEST tied block at
    # or above L_STAR_MIN (safer than "deepest", which degenerates to the
    # sweep ceiling under saturation).
    eligible = [L for L in tied_margin if L >= l_star_min] or tied_margin
    l_star = int(min(eligible))
    acc_at_l_star = float(mean_accs[sweep_blocks.index(l_star)])

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
                           "(preregistered, rev 0.3 review fix D21)"),
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

    if l_star < l_star_min:
        report["aggregate"] = {
            "status": "ABORT_GUARD_LAYER",
            "reason": (f"L*={l_star} < {l_star_min}: L_dr = L*-{dr_offset} would "
                       "not be strictly upstream with margin; preregistered "
                       "hard abort, no fallback")}
        write_report(report, report_path)
        print("[abort] ABORT_GUARD_LAYER")
        return 0
    l_dr = l_star - dr_offset
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
    conn_dirs = {f"r{i}": pc_random_dir(V_star, rng_conn)
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
    cover_k = derive_cover_k(intermediate)
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
    print(f"[discover] cover_k={cover_k} of {intermediate} intermediate coords "
          f"({100.0 * cover_k / intermediate:.3f}%)")
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
        rs_seed = args.seed * 10000 + 7000
        b_rs = gen_condition(model, tok, pf_con, device, [], max_new,
                             n_samples=rs_samples, sample_seed=rs_seed)
        t_rs = gen_condition(model, tok, pf_con, device,
                             eraser_hooks(u_rs_star), max_new,
                             n_samples=rs_samples, sample_seed=rs_seed)
        pf["RS_F5_behavioral_change_rate"] = behavioral_change_rate(b_rs, t_rs)
        pf["n_prompts"] = k
        pf["threshold"] = BEHAVIORAL_CHANGE_MIN
        pf["go"] = bool(min(pf["DR_F5_behavioral_change_rate"],
                            pf["AMP_F5_behavioral_change_rate"],
                            pf["RS_F5_behavioral_change_rate"])
                        >= BEHAVIORAL_CHANGE_MIN)
        pf["note"] = ("PREFLIGHT ONLY -- never evidence, reads no test "
                      "statistic. A NO-GO means the confirmatory run would "
                      "very likely stamp VACUOUS_NO_BEHAVIORAL_CHANGE on the "
                      "affected arms; fix the intervention strength (cover_k, "
                      "L*) or stop, and log whatever is changed as a deviation "
                      "BEFORE the confirmatory run.")
        report["preflight"] = pf
        report["aggregate"] = {"status": "PREFLIGHT_ONLY", "go": pf["go"]}
        report["provenance"]["runtime_seconds"] = round(time.time() - t0, 1)
        write_report(report, report_path)
        print(f"[preflight] go={pf['go']} DR={pf['DR_F5_behavioral_change_rate']:.2f} "
              f"AMP={pf['AMP_F5_behavioral_change_rate']:.2f} "
              f"RS={pf['RS_F5_behavioral_change_rate']:.2f} -> {report_path}")
        return 0

    # ---------------- Stage: ABLATE (generate hooked, judge CLEAN) --------
    print("[ablate] baselines (judge banks, no hooks)")
    txt_base_f5 = gen_condition(model, tok, banks["f5_judge"], device, [], max_new)
    txt_base_f2 = gen_condition(model, tok, banks["f2_judge"], device, [], max_new)
    txt_base_neu = gen_condition(model, tok, banks["neu_judge"], device, [], max_new)

    base_f5 = measure_condition(model, tok, banks["f5_judge"], txt_base_f5,
                                device, l_star, measure_dirs)
    base_f2 = measure_condition(model, tok, banks["f2_judge"], txt_base_f2,
                                device, l_star, measure_dirs)
    base_neu = measure_condition(model, tok, banks["neu_judge"], txt_base_neu,
                                 device, l_star, measure_dirs)

    # Presence thresholds from BASELINE conditions only.
    tau_f5 = 0.5 * (float(np.mean(base_f5["proj"]["uF5"]))
                    + float(np.mean(base_neu["proj"]["uF5"])))
    tau_f2 = 0.5 * (float(np.mean(base_f2["proj"]["uF2"]))
                    + float(np.mean(base_neu["proj"]["uF2"])))
    report["discover"]["tau_F5"] = tau_f5
    report["discover"]["tau_F2"] = tau_f2

    tests = {}

    # ---- DR-F5 ----
    print("[ablate] DR-F5")
    txt_tgt = gen_condition(model, tok, banks["f5_judge"], device,
                            dr_hooks(cover_f5), max_new)
    tgt_dr5 = measure_condition(model, tok, banks["f5_judge"], txt_tgt,
                                device, l_star, measure_dirs)
    ctrls_dr5 = []
    for tr in range(n_controls):
        rng = np.random.default_rng(args.seed * 10000 + tr)
        cov = decile_matched_cover(mean_abs_f5, cover_f5, rng)
        txt_c = gen_condition(model, tok, banks["f5_judge"], device,
                              dr_hooks(cov), max_new)
        ctrls_dr5.append(measure_condition(
            model, tok, banks["f5_judge"], txt_c, device, l_star, measure_dirs))
    # NOTE (review MINOR, deduplicated): the F5-bank-with-F2-cover condition is
    # simultaneously DR-F5's cross-COVER control and DR-F2's cross-RAIL
    # selectivity condition, and the F2-bank-with-F5-cover condition is the
    # mirror. The rev-0.3 draft generated each of them TWICE with identical
    # configuration (~64 wasted generation units). Each is now generated once,
    # with the full measure_dirs so both consumers can read it.
    txt_f5bank_f2cover = gen_condition(model, tok, banks["f5_judge"], device,
                                       dr_hooks(cover_f2), max_new)
    cond_f5bank_f2cover = measure_condition(
        model, tok, banks["f5_judge"], txt_f5bank_f2cover, device, l_star,
        measure_dirs)
    txt_f2bank_f5cover = gen_condition(model, tok, banks["f2_judge"], device,
                                       dr_hooks(cover_f5), max_new)
    cond_f2bank_f5cover = measure_condition(
        model, tok, banks["f2_judge"], txt_f2bank_f5cover, device, l_star,
        measure_dirs)
    cross_dr5 = cond_f5bank_f2cover     # DR-F5 cross-cover control
    xrail_dr5 = cond_f2bank_f5cover     # DR-F5 cross-rail selectivity
    tests["DR_F5"] = eval_dr_test(base_f5, tgt_dr5, ctrls_dr5, cross_dr5,
                                  tau_f5, base_f2, xrail_dr5, "uF5", "uF2")
    write_report(report, report_path)

    # ---- DR-F2 ----
    print("[ablate] DR-F2")
    txt_tgt2 = gen_condition(model, tok, banks["f2_judge"], device,
                             dr_hooks(cover_f2), max_new)
    tgt_dr2 = measure_condition(model, tok, banks["f2_judge"], txt_tgt2,
                                device, l_star, measure_dirs)
    ctrls_dr2 = []
    for tr in range(n_controls):
        rng = np.random.default_rng(args.seed * 10000 + 100 + tr)
        cov = decile_matched_cover(mean_abs_f2, cover_f2, rng)
        txt_c = gen_condition(model, tok, banks["f2_judge"], device,
                              dr_hooks(cov), max_new)
        ctrls_dr2.append(measure_condition(
            model, tok, banks["f2_judge"], txt_c, device, l_star, measure_dirs))
    cross_dr2 = cond_f2bank_f5cover     # DR-F2 cross-cover control (reused)
    xrail_dr2 = cond_f5bank_f2cover     # DR-F2 cross-rail selectivity (reused)
    tests["DR_F2"] = eval_dr_test(base_f2, tgt_dr2, ctrls_dr2, cross_dr2,
                                  tau_f2, base_f5, xrail_dr2, "uF2", "uF5")

    # ---- AMP-F5 ----
    print("[ablate] AMP-F5")
    txt_amp = gen_condition(model, tok, banks["f5_judge"], device,
                            eraser_hooks(u_f5_star), max_new)
    tgt_amp = measure_condition(model, tok, banks["f5_judge"], txt_amp,
                                device, l_star, measure_dirs)
    ctrls_amp = []
    for tr in range(n_controls):
        rng = np.random.default_rng(args.seed * 10000 + 300 + tr)
        u_rand = pc_random_dir(V_star, rng)
        txt_c = gen_condition(model, tok, banks["f5_judge"], device,
                              eraser_hooks(u_rand), max_new)
        ctrls_amp.append(measure_condition(
            model, tok, banks["f5_judge"], txt_c, device, l_star, measure_dirs))
    txt_amp_cross = gen_condition(model, tok, banks["f5_judge"], device,
                                  eraser_hooks(u_f2_star), max_new)
    cross_amp = measure_condition(model, tok, banks["f5_judge"], txt_amp_cross,
                                  device, l_star, measure_dirs)
    txt_amp_xrail = gen_condition(model, tok, banks["f2_judge"], device,
                                  eraser_hooks(u_f5_star), max_new)
    xrail_amp = measure_condition(model, tok, banks["f2_judge"], txt_amp_xrail,
                                  device, l_star, {"uF2": u_f2_star})
    tests["AMP_F5"] = eval_amp_test(base_f5, tgt_amp, ctrls_amp, cross_amp,
                                    tau_f5, base_f2, xrail_amp, "uF5", "uF2")
    write_report(report, report_path)

    # ---- RS-F5 (increase-sign anchor; rev 0.3 redesign) ----
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
    n_shuf = int(round(RS_CTRL_SHUFFLED_FRAC * n_controls))
    n_shuf = max(1, min(n_controls - 1, n_shuf)) if n_controls > 1 else n_controls
    rs_rows_lic = feats["rs_lic_fit"][:, l_star + 1]
    rs_rows_con = feats["rs_con_fit"][:, l_star + 1]
    ctrls_rs, ctrl_dirs_rs, ctrl_family = [], [], []
    for tr in range(n_controls):
        rng = np.random.default_rng(args.seed * 10000 + 200 + tr)
        if tr < n_shuf:
            u_rand = shuffled_label_dir(rs_rows_con, rs_rows_lic, rng,
                                        ortho_to=u_f5_star)
            fam = "shuffled_label_refit"
        else:
            u_rand = pc_random_dir(V_rs, rng, ortho_to=u_f5_star)
            fam = "rs_fit_pc_subspace"
        ctrl_dirs_rs.append(u_rand)
        ctrl_family.append(fam)
        txt_c = gen_condition(model, tok, con_j, device, eraser_hooks(u_rand),
                              max_new, n_samples=rs_samples,
                              sample_seed=rs_seed)   # common random numbers
        ctrls_rs.append(measure_condition(
            model, tok, con_j, txt_c, device, l_star, rs_dirs, mass_ids))

    # Perturbation-magnitude matching, reported so the reader can see whether
    # the target/control comparison was strength-matched AT ALL (review MAJOR):
    # mean |h . u| over the conflicted judge prompts, clean model, last token.
    H_con = residual_feats(model, tok, con_j, device)[:, l_star + 1]

    def _mag(u):
        return float(np.mean(np.abs(H_con @ np.asarray(u, dtype=np.float64))))

    target_mag = _mag(u_rs_star)
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
        "common_random_numbers": True,
        "note": ("if the magnitude ratio is far below 1 the controls are "
                 "STRONGER perturbations than the target and a FAIL cannot "
                 "distinguish 'no brake' from 'controls too strong'"),
    }
    tests["RS_F5"] = eval_rs_test(rs_pre, base_rs, tgt_rs, ctrls_rs, ref_rs,
                                  "uF5", pre_judge=rs_pre_judge,
                                  ctrl_meta=ctrl_meta,
                                  target_magnitude=target_mag)
    write_report(report, report_path)

    # ---------------- Stage: CONNECT ----------------
    print("[connect] DR-F5 (L_dr) -> AMP-F5 site (L*), clean-pass selectivity")
    tests["CONN_DRF5_to_AMPF5"] = eval_conn_test(
        base_f5, tgt_dr5, ctrls_dr5, "uF5", "uF2", rand_keys)
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
    core_order = ["DR_F5", "DR_F2", "AMP_F5", "RS_F5", "CONN_DRF5_to_AMPF5"]
    evaluable = [n for n in core_order
                 if tests[n].get("status") in ("PASS", "FAIL", "CONFOUNDED")]
    n_pass = sum(1 for n in evaluable if tests[n]["status"] == "PASS")
    n_eval = len(evaluable)
    fraction = (n_pass / n_eval) if n_eval else 0.0

    rs_status = tests["RS_F5"].get("status")
    rs_ok_or_vacuous = rs_status in ("PASS", "VACUOUS", "VACUOUS_NO_BRAKE",
                                     "VACUOUS_NO_BEHAVIORAL_CHANGE")

    kill = None
    if n_eval < 3:
        status = "GREY_ATLAS_V0_INSUFFICIENT_EVALUABLE"
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
        tests["DR_F5"].get("starvation_signature_holds") is True
        and tests["AMP_F5"].get("attenuation_signature_holds") is True)
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
    report["provenance"]["runtime_seconds"] = round(time.time() - t0, 1)
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
