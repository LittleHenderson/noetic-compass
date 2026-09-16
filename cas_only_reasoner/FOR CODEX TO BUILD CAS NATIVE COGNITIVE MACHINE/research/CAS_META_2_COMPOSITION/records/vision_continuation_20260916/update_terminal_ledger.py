"""Append evidence without altering the complete CNCM requirement scope."""
from hashlib import sha256
import json
from pathlib import Path

HOME = Path("C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE")
INNER = Path(__file__).resolve().parents[4]
addition = b'''
## 2026-09-16 completed encoding gate and checked procedure prerequisite

The source-bound AWS ordered-encoder diagnostic completed: all 96 changed-answer
pairs separated, while all 32 graph-line-reorder controls retained equal numeric
coordinates. The legacy encoder nearly collapsed all 96 changed-answer pairs;
only 32 were exactly coordinate-equal. An independent standard-library recount
verified saved vectors, thresholds, source/result/artifact hashes and coverage.
The worker used zero optimizer updates and zero learner forward calls. No
trained-accuracy improvement or explanation of every past error is established.
The GPU and job resources were independently verified removed; result objects
remain readable in the private bucket. Canonical budget revision 74 reserves
$431, leaving $4,569 under the $5,000 cap, with no refund. These are reservations,
not invoiced charges. Exact records: research/CAS_META_2_COMPOSITION/records/
ordered_encoder_001/STATUS.md and its independent/provider receipts.

The missing-skill integration prerequisite now has an isolated six-instruction
rational candidate executor, finite development selection, separate CAS-Math
substitution checks, fixed engineering qualification, and strict reconstruction.
The combined check passed 180 tests plus 387 subtests. Saved candidate bytes and
checks reproduced in a separate Python process; 768 independent Fraction cases
matched. These public fixed fixtures are not a secret empirical learning exam.
There is still no native procedure installation, suspended-parent resume,
conserved shared acquisition budget, native journal recovery or rollback.
The new modules do not change the 0.1 authority manifest or runtime state.
Exact evidence: records/procedural_substrate_001/STATUS.md in the vision-next
homebase; implementation plan: research/CAS_META_2_COMPOSITION/records/
vision_continuation_20260916/NATIVE_PROCEDURE_INTEGRATION_PLAN.md.

The full V01-V18, 31-system and integrated 20-step destination remains open.
Next work is the real versioned kernel acquisition/install/return/reuse/rollback
path, not another standalone promotion store. Neural program synthesis, native
flow and CAS-Ohm qualification, multimodal competence and all remaining original
requirements retain their existing unmet gates. Complementary/perspective
experiments remain build-only and must not inherit a silent encoder rewrite.
'''
records = []
for root in (HOME, INNER):
    path = root / 'docs/CNCM_COMPLETE_REQUIREMENT_LEDGER.md'
    before = path.read_bytes()
    assert sha256(before).hexdigest() == 'b585da523a12520b495c87dfbd0283e05a1d2b683a22dedae00b337aceb705e7'
    path.write_bytes(before + addition)
    after = path.read_bytes()
    assert after.startswith(before)
    records.append({'path': str(path), 'before_sha256': sha256(before).hexdigest(),
                    'after_sha256': sha256(after).hexdigest(),
                    'original_bytes_preserved': True, 'full_goal_complete': False})
out = Path(__file__).with_name('terminal_ledger_updates.json')
with out.open('x', encoding='utf-8', newline='\n') as handle:
    json.dump(records, handle, indent=2)
    handle.write('\n')
print(json.dumps(records))
