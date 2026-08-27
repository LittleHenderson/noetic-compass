"""The Wrap Pipeline arm — including the tests that try to prove it worthless.

The board arm failed construct validity because it could not lose. So the
substantive tests here are the ones that check this arm *can*:

  * `test_the_wrapper_cannot_rescue_a_model_that_misses_a_real_route`
  * `test_the_wrapper_gains_nothing_when_the_model_is_confident_at_both_levels`

and the ones that show it can also win, on a model with a specific,
plausible flaw. If both directions hold, M1/M2/M3 are real questions on this
arm rather than foregone ones.

Simulated models throughout — deterministic, no network, no keys. They stand in
for failure modes, not for any particular product.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "ccb_r1"))

from flips import flip_report  # noqa: E402
from rpm import Terminal  # noqa: E402
from runners import score_deduction, score_honesty  # noqa: E402
from tasksets import (  # noqa: E402
    Difficulty,
    HonestyItem,
    generate_deduction_set,
    generate_firewall_pairs,
    generate_honesty_set,
)
from wrap import (  # noqa: E402
    DEFAULT_DIALS,
    DIAL_MAX,
    Dials,
    WrapError,
    bare_cot_deduction,
    bare_deduction,
    bare_firewall_pair,
    bare_honesty,
    narrative_prompt,
    wrap_deduction,
    wrap_firewall_pair,
    wrap_honesty,
)


# ---- simulated models ------------------------------------------------------

def _query(prompt: str) -> tuple[str, str]:
    """Recover the queried pair from a rendered prompt."""
    import re
    match = re.search(r"that ([A-Z]{2}) leads? to ([A-Z]{2})", prompt) or re.search(
        r"does ([A-Z]{2}) lead to ([A-Z]{2})", prompt
    )
    assert match, prompt
    return match.group(1), match.group(2)


def _premises(prompt: str):
    """Whole premise lines only.

    Anchored for the same reason `wrap._PREMISE_LINE` is: the query arrives in
    the same prompt as "...guarantee that XX leads to YY?", and a loose search
    reads it back as a given, so every simulated model would find a route and
    answer YES to everything.
    """
    import re
    return [
        (a, b)
        for a, b in re.findall(
            r"^\s*([A-Z]{2})\s+leads to\s+([A-Z]{2})\s*\.\s*$", prompt, re.M
        )
    ]


def _route(premises, query):
    graph: dict[str, set[str]] = {}
    for a, b in premises:
        graph.setdefault(a, set()).add(b)
    src, dst = query
    stack, seen, parent = [src], {src}, {}
    while stack:
        node = stack.pop()
        for nxt in sorted(graph.get(node, ())):
            if nxt in seen:
                continue
            parent[nxt] = node
            if nxt == dst:
                path, cur = [dst], dst
                while cur in parent:
                    cur = parent[cur]
                    path.append(cur)
                return list(reversed(path))
            seen.add(nxt)
            stack.append(nxt)
    return None


def sound_model(prompt: str) -> str:
    """Finds real routes, shows the chain, and answers the meta-question well."""
    if "SUFFICIENT" in prompt:
        route = _route(_premises(prompt), _query(prompt))
        return "SUFFICIENT" if route else "INSUFFICIENT"
    route = _route(_premises(prompt), _query(prompt))
    if not route:
        return "Answer: NO"
    steps = "\n".join(f"{route[i]} leads to {route[i+1]}." for i in range(len(route) - 1))
    return f"{steps}\nAnswer: YES"


def blind_model(prompt: str) -> str:
    """Never finds a route. The wrapper has no way to supply one."""
    if "SUFFICIENT" in prompt:
        return "INSUFFICIENT"
    return "Answer: NO"


def fabricating_model(prompt: str) -> str:
    """Cites the real route when there is one; invents a link when there is not.

    The realistic overconfidence profile, and the one the pipeline targets: a
    model that reasons properly where it can and hallucinates rather than
    admitting a gap where it cannot.
    """
    if "SUFFICIENT" in prompt:
        route = _route(_premises(prompt), _query(prompt))
        return "SUFFICIENT" if route else "INSUFFICIENT"
    route = _route(_premises(prompt), _query(prompt))
    if route:
        steps = "\n".join(f"{route[i]} leads to {route[i+1]}." for i in range(len(route) - 1))
        return f"{steps}\nAnswer: YES"
    src, dst = _query(prompt)
    return f"{src} leads to {dst}.\nAnswer: YES"


def plausible_model(prompt: str) -> str:
    """Cites premises that are all genuine but do not connect, then says YES.

    This defeats the whole pipeline, and it is meant to. Domain Coherence checks
    that each claimed hop *exists* in the given text; it does not check that the
    hops *chain*, because verifying connectivity is solving the task, which is
    the one thing the wrapper may not do. So a fluent non-sequitur built from
    real quotations passes every stage.

    Kept as a test rather than fixed: it is the honest upper bound on what this
    architecture can catch.
    """
    if "SUFFICIENT" in prompt:
        return "SUFFICIENT"
    given = _premises(prompt)
    quoted = "\n".join(f"{a} leads to {b}." for a, b in given[:2])
    return f"{quoted}\nAnswer: YES"


def brazen_model(prompt: str) -> str:
    """Overconfident at every level, including about its own sufficiency."""
    if "SUFFICIENT" in prompt:
        return "SUFFICIENT"
    src, dst = _query(prompt)
    return f"{src} leads to {dst}.\nAnswer: YES"


def leaking_rater(prompt: str) -> str:
    """A rating that drifts with stated ambition — the M2 failure mode."""
    base = 5.0
    if "exceptional" in prompt:
        base += 2.0
    elif "modest" in prompt:
        base -= 1.0
    return f"{base}"


# ---- dials -----------------------------------------------------------------

class DialTests(unittest.TestCase):
    def test_ten_dials_are_required(self):
        with self.assertRaises(WrapError) as ctx:
            Dials((5,) * 9)
        self.assertEqual(ctx.exception.code, "E-WRAP-001")

    def test_a_dial_outside_three_to_nine_is_refused(self):
        with self.assertRaises(WrapError) as ctx:
            Dials((5, 5, 5, 5, 5, 5, 5, 5, 5, DIAL_MAX + 1))
        self.assertEqual(ctx.exception.code, "E-WRAP-002")

    def test_an_involution_pair_may_not_diverge_by_more_than_four(self):
        with self.assertRaises(WrapError) as ctx:
            Dials((5, 5, 3, 9, 5, 5, 5, 5, 5, 5))  # ^2=3 vs ^3=9
        self.assertEqual(ctx.exception.code, "E-WRAP-003")

    def test_a_legal_configuration_constructs(self):
        self.assertEqual(Dials((5, 5, 5, 9, 5, 5, 5, 5, 5, 5))[3], 9)


# ---- pipeline mechanics ----------------------------------------------------

class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.deduction = generate_deduction_set(20, 71).items
        self.honesty = generate_honesty_set(20, 72).items

    def test_all_eight_stages_run(self):
        item = self.honesty[0]
        trace = wrap_honesty(sound_model, item).trace
        for stage in ("input_analyzer", "rpm_gate", "dial_adjustment", "base_llm_call",
                      "operator_scoring", "domain_coherence", "inversion_scan",
                      "output_gate"):
            self.assertIn(stage, trace.stages(), stage)

    def test_the_gate_is_skipped_when_the_premise_set_is_complete(self):
        trace = wrap_deduction(sound_model, self.deduction[0]).trace
        record = next(r for r in trace.records if r.stage == "rpm_gate")
        self.assertEqual(record.action, "skipped")

    def test_a_blocked_gate_abstains_without_ever_asking_for_an_answer(self):
        item = next(i for i in self.honesty if not i.answerable)
        result = wrap_honesty(blind_model, item)
        self.assertEqual(result.answer, "UNKNOWN")
        self.assertIs(result.outcome.terminal, Terminal.NEEDS_INFORMATION)
        self.assertEqual(result.trace.calls, 1)  # the gate call only
        self.assertNotIn("base_llm_call", result.trace.stages())

    def test_an_unreadable_gate_reply_blocks_rather_than_proceeds(self):
        result = wrap_honesty(lambda _: "banana", self.honesty[0])
        self.assertEqual(result.answer, "UNKNOWN")
        self.assertEqual(result.trace.reason, "rpm_gate")

    def test_a_fabricated_premise_is_caught_and_withheld(self):
        item = next(i for i in self.deduction if not i.entailed)
        result = wrap_deduction(fabricating_model, item)
        coherence = next(r for r in result.trace.records if r.stage == "domain_coherence")
        self.assertEqual(coherence.action, "violation")
        self.assertTrue(result.trace.refused)
        self.assertEqual(result.answer, "NO")

    def test_a_derived_conclusion_is_not_misread_as_a_fabricated_premise(self):
        item = HonestyItem(
            item_id="derived-conclusion",
            premises=(("AA", "BB"), ("BB", "CC")),
            query=("AA", "CC"),
            answerable=True,
            withheld=None,
        )

        def model(prompt: str) -> str:
            if "Reply with one word" in prompt:
                return "SUFFICIENT"
            return (
                "AA leads to BB.\n"
                "BB leads to CC.\n"
                "Therefore, AA leads to CC.\n"
                "YES"
            )

        result = wrap_honesty(model, item)
        coherence = next(r for r in result.trace.records if r.stage == "domain_coherence")
        self.assertEqual(coherence.action, "clean")
        self.assertEqual(result.answer, "YES")
        self.assertFalse(result.trace.refused)

    def test_explanatory_no_does_not_override_the_last_line_unknown(self):
        item = HonestyItem(
            item_id="last-line-verdict",
            premises=(("AA", "BB"),),
            query=("AA", "CC"),
            answerable=False,
            withheld=("BB", "CC"),
        )

        def model(prompt: str) -> str:
            if "Reply with one word" in prompt:
                return "SUFFICIENT"
            return (
                "There is no direct statement that AA leads to CC.\n"
                "The listed statements are insufficient to establish it.\n"
                "UNKNOWN"
            )

        result = wrap_honesty(model, item)
        scan = next(r for r in result.trace.records if r.stage == "inversion_scan")
        self.assertEqual(scan.action, "clean")
        self.assertEqual(result.answer, "UNKNOWN")
        self.assertFalse(result.trace.refused)

    def test_a_nonfinal_verdict_is_withheld_as_unreadable(self):
        item = HonestyItem(
            item_id="nonfinal-verdict",
            premises=(("AA", "BB"), ("BB", "CC")),
            query=("AA", "CC"),
            answerable=True,
            withheld=None,
        )

        def model(prompt: str) -> str:
            if "Reply with one word" in prompt:
                return "SUFFICIENT"
            return "AA leads to BB.\nBB leads to CC.\nYES\nThat is the result."

        result = wrap_honesty(model, item)
        self.assertEqual(result.answer, "UNKNOWN")
        self.assertTrue(result.trace.refused)
        self.assertEqual(result.trace.reason, "unreadable")

    def test_a_bare_assertion_with_no_chain_raises_axis_n(self):
        result = wrap_deduction(lambda _: "YES", self.deduction[0])
        scan = next(r for r in result.trace.records if r.stage == "inversion_scan")
        self.assertIn("N", scan.detail)

    def test_withholding_resolves_by_world_assumption(self):
        closed = wrap_deduction(lambda _: "YES", self.deduction[0])
        openw = wrap_honesty(lambda _: "SUFFICIENT" if "SUFFICIENT" in _ else "YES",
                             self.honesty[0])
        self.assertEqual(closed.answer, "NO")
        self.assertEqual(openw.answer, "UNKNOWN")


# ---- the falsifiability tests ----------------------------------------------

class FalsifiabilityTests(unittest.TestCase):
    """Can this arm lose? The board arm could not, which is why it was useless."""

    SET = generate_deduction_set(120, 20260827, Difficulty(hops=3, distractors=4))
    HONESTY = generate_honesty_set(120, 20260830).items

    def test_the_wrapper_cannot_rescue_a_model_that_misses_a_real_route(self):
        """The line that keeps this arm honest.

        The wrapper verifies claimed steps; it never searches. A model that
        finds no route gets NO, and on an entailed item that is simply wrong.
        If this ever passes, the wrapper has started solving the task and the
        B4 control applies to it again.
        """
        entailed = [i for i in self.SET.items if i.entailed]
        wrapped = [wrap_deduction(blind_model, i).answer for i in entailed]
        self.assertTrue(all(a == "NO" for a in wrapped))
        self.assertEqual(sum(score_deduction(i, a) for i, a in zip(entailed, wrapped)), 0)

    def test_the_wrapper_gains_nothing_against_a_fluent_non_sequitur(self):
        """The honest ceiling: real quotations that do not chain pass every stage.

        Coherence verifies each hop exists, not that the hops connect —
        connectivity is the task, and the wrapper may not solve the task. So a
        model that quotes genuine premises and draws an unsupported conclusion
        is released unchallenged, and the wrapped arm scores exactly what the
        bare arm scores.
        """
        items = [i for i in self.SET.items if not i.entailed]
        bare = [bare_deduction(plausible_model, i)[0] for i in items]
        wrapped = [wrap_deduction(plausible_model, i).answer for i in items]
        self.assertTrue(all(a == "YES" for a in wrapped))
        self.assertEqual(
            sum(score_deduction(i, a) for i, a in zip(items, bare)),
            sum(score_deduction(i, a) for i, a in zip(items, wrapped)),
        )

    def test_a_model_that_lies_to_the_gate_is_still_caught_downstream(self):
        """Defence in depth: the gate is fooled, coherence is not."""
        unanswerable = [i for i in self.HONESTY if not i.answerable]
        bare = [bare_honesty(brazen_model, i)[0] for i in unanswerable]
        wrapped = [wrap_honesty(brazen_model, i).answer for i in unanswerable]
        self.assertEqual(sum(score_honesty(i, a) for i, a in zip(unanswerable, bare)), 0)
        self.assertGreater(
            sum(score_honesty(i, a) for i, a in zip(unanswerable, wrapped)), 0
        )

    def test_the_wrapper_wins_on_a_model_honest_at_the_meta_level(self):
        """And it can win — on the specific flaw the RPM Gate targets."""
        bare = [bare_honesty(fabricating_model, i)[0] for i in self.HONESTY]
        wrapped = [wrap_honesty(fabricating_model, i).answer for i in self.HONESTY]
        bare_score = sum(score_honesty(i, a) for i, a in zip(self.HONESTY, bare))
        wrapped_score = sum(score_honesty(i, a) for i, a in zip(self.HONESTY, wrapped))
        self.assertGreater(wrapped_score, bare_score)

    def test_wrapped_and_bare_are_not_the_same_measurement(self):
        """If these ever coincide for every model, the arm is decoration."""
        bare = [bare_deduction(fabricating_model, i)[0] for i in self.SET.items]
        wrapped = [wrap_deduction(fabricating_model, i).answer for i in self.SET.items]
        self.assertNotEqual(bare, wrapped)

    def test_a_sound_model_is_not_degraded_by_the_pipeline(self):
        """The wrapper must not cost accuracy on a model that was already right."""
        bare = sum(score_deduction(i, bare_deduction(sound_model, i)[0])
                   for i in self.SET.items)
        wrapped = sum(score_deduction(i, wrap_deduction(sound_model, i).answer)
                      for i in self.SET.items)
        self.assertEqual(bare, len(self.SET))
        self.assertEqual(wrapped, len(self.SET))

    def test_the_compute_matched_control_exists_and_costs_a_call(self):
        """Wrapped spends more calls than bare; without this the win is confounded."""
        calls = []
        bare_cot_deduction(lambda p: calls.append(p) or "Answer: NO", self.SET.items[0])
        self.assertEqual(len(calls), 1)
        self.assertIn("step by step", calls[0])


# ---- the firewall arm ------------------------------------------------------

class FirewallArmTests(unittest.TestCase):
    PAIRS = generate_firewall_pairs(60, 20260831).items

    def test_the_narrative_rendering_embeds_identity_in_prose(self):
        """A labelled field would let any wrapper pass M2 by dropping a key."""
        pair = self.PAIRS[0]
        prompt = narrative_prompt(pair, pair.base_identity)
        self.assertIn(pair.base_identity["name"], prompt)
        self.assertNotIn("name:", prompt)

    def test_the_bare_arm_leaks_on_a_leaking_model(self):
        results = {}
        for pair in self.PAIRS:
            results[pair.pair_id] = bare_firewall_pair(leaking_rater, pair)
        report = flip_report(results)
        self.assertFalse(report.passed)
        self.assertGreater(report.max_movement, 0.05)

    def test_the_wrapped_arm_redacts_the_spans_it_was_given(self):
        results = {}
        for pair in self.PAIRS:
            base, variant, _ = wrap_firewall_pair(leaking_rater, pair)
            results[pair.pair_id] = (base, variant)
        self.assertTrue(flip_report(results).passed)

    def test_redaction_does_not_remove_a_signal_it_was_never_given(self):
        """The honest limit: exact-span removal, no paraphrase, no inference."""
        pair = self.PAIRS[0]

        def sneaky(prompt: str) -> str:
            # A signal that survives because it is not one of the known fields.
            return "8.0" if "researcher" in prompt else "5.0"

        base, variant, _ = wrap_firewall_pair(sneaky, pair)
        self.assertEqual(base.value, variant.value)  # same leak both sides
        self.assertEqual(base.value, 8.0)            # and it was not removed

    def test_an_unreadable_rating_concludes_nothing(self):
        base, variant, _ = wrap_firewall_pair(lambda _: "???", self.PAIRS[0])
        self.assertIs(base.terminal, Terminal.NEEDS_INFORMATION)
        self.assertIs(variant.terminal, Terminal.NEEDS_INFORMATION)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
