"""The English boundary -- what is decided before the reasoner sees anything.

`encoder.py` is the one place English is read, and it is read by a closed
grammar with a total rejection policy. These tests pin three things: that each
sentence of the grammar has exactly one reading; that everything else is
refused with a code naming the fault rather than read charitably; and that
`render` is an exact inverse, so the boundary adds no meaning in either
direction. A fourth, structural, check keeps the module as model-free as the
processor it feeds: an encoder that could reach a model would be a place to
smuggle the reasoning back out of CAS.
"""

from __future__ import annotations

import ast
import random
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PACKAGE = REPO / "scripts" / "cas_rpu"
sys.path.insert(0, str(PACKAGE))

import events  # noqa: E402
from encoder import (  # noqa: E402
    ACCEPTED_FORM,
    PRODUCTIONS,
    EncodeError,
    decode_verdict,
    encode,
    normalise,
    render,
)
from events import EventKind  # noqa: E402

#: The five canonical sentences and the one event each means.
CANON = (
    ("A leads to B.", events.fact("A", "B")),
    ("A does not lead to B.", events.negation("A", "B")),
    ("maybe A leads to B.", events.hypothesis("A", "B")),
    ("forget that A leads to B.", events.retract("A", "B")),
    ("does A lead to B?", events.ask("A", "B")),
)


def refusal(text: str) -> EncodeError:
    """The EncodeError `encode` raises for `text`; fails the test if it does not."""
    try:
        encode(text)
    except EncodeError as exc:
        return exc
    raise AssertionError(f"{text!r} was accepted; it should have been refused")


class GrammarTests(unittest.TestCase):
    def test_each_template_maps_to_exactly_one_event_kind(self):
        """Not "at least one": a sentence two productions could read would make
        the fixed order load-bearing, and then the order would be a semantic
        decision hiding in a tuple."""
        for text, expected in CANON:
            with self.subTest(text=text):
                self.assertEqual(encode(text), expected)
                readings = [p.kind for p in PRODUCTIONS if p.pattern.fullmatch(text)]
                self.assertEqual(readings, [expected.kind])
        self.assertEqual({e.kind for _, e in CANON}, set(EventKind))
        self.assertEqual({p.kind for p in PRODUCTIONS}, set(EventKind))

    def test_a_leading_capital_is_accepted_only_on_the_first_word(self):
        """Sentence-initial capitalisation is how people type; a capital
        anywhere else is a different token, and a different token is not read
        as the keyword it resembles."""
        self.assertEqual(encode("Maybe A leads to B."), events.hypothesis("A", "B"))
        self.assertEqual(encode("Forget that A leads to B."), events.retract("A", "B"))
        self.assertEqual(encode("Does A lead to B?"), events.ask("A", "B"))
        for text in (
            "maybe A Leads to B.",
            "A Leads to B.",
            "A Does not lead to B.",
            "A does Not lead to B.",
            "forget That A leads to B.",
            "does A Lead to B?",
            "MAYBE A leads to B.",
            "DOES A lead to B?",
        ):
            with self.subTest(text=text):
                exc = refusal(text)
                self.assertEqual(exc.code, "E-ENC-001")
                # refused as a case fault, not misread as a two-word name
                self.assertIn("lowercase", exc.message)

    def test_whitespace_runs_collapse_and_a_trailing_period_is_optional(self):
        """Whitespace is a separator, never meaning, so no amount of it can
        change which event a sentence is. The '.' is the one piece of
        punctuation that carries nothing, so it is the one that is optional."""
        self.assertEqual(normalise("  A \t leads\n\nto   B  "), "A leads to B")
        for text in (
            "A leads to B",
            "A leads to B.",
            "  A   leads\tto   B  ",
            "A leads to B .",
        ):
            with self.subTest(text=text):
                self.assertEqual(encode(text), events.fact("A", "B"))
        self.assertEqual(encode("maybe A leads to B"), events.hypothesis("A", "B"))
        self.assertEqual(encode("forget that  A leads to B"), events.retract("A", "B"))
        self.assertEqual(encode("does   A lead to B ?"), events.ask("A", "B"))

    def test_there_is_no_production_for_an_associative_link(self):
        """The REPL's `~>` has no English here on purpose, and the refusal says
        so rather than falling back on a bare "no match"."""
        exc = refusal("A ~> B")
        self.assertEqual(exc.code, "E-ENC-001")
        self.assertIn("associative", exc.message)
        self.assertIn("events.associate", exc.message)
        for production in PRODUCTIONS:
            self.assertEqual(production.build("A", "B").relation, events.DEFAULT_RELATION)


class RejectionTests(unittest.TestCase):
    """Rejection is total, and each refusal says which rule was broken."""

    NEAR_MISSES = (
        # E-ENC-001: outside the grammar altogether
        ("", "E-ENC-001"),
        ("   ", "E-ENC-001"),
        ("hello", "E-ENC-001"),
        ("leads to B", "E-ENC-001"),
        ("A leads to", "E-ENC-001"),
        ("A leads B", "E-ENC-001"),
        ("A ~> B", "E-ENC-001"),
        ("A Leads to B.", "E-ENC-001"),
        ("MAYBE A leads to B.", "E-ENC-001"),
        # E-ENC-002: the shape is right, a name is not a NAME
        ("A leads to B C", "E-ENC-002"),
        ("A leads to B leads", "E-ENC-002"),
        ("New York leads to B", "E-ENC-002"),
        ("2A leads to B", "E-ENC-002"),
        ("A leads to 9", "E-ENC-002"),
        ("A.B leads to C", "E-ENC-002"),
        ("A leads to B!", "E-ENC-002"),
        ("A|B leads to C", "E-ENC-002"),
        ("A~B leads to C", "E-ENC-002"),
        ("-A leads to B", "E-ENC-002"),
        ("maybe big city leads to B", "E-ENC-002"),
        ("does 2A lead to B?", "E-ENC-002"),
        # E-ENC-003: the body is a production, the terminator is wrong
        ("does A lead to B", "E-ENC-003"),
        ("does A lead to B.", "E-ENC-003"),
        ("A leads to B?", "E-ENC-003"),
        ("maybe A leads to B?", "E-ENC-003"),
        # E-ENC-004: a near-synonym
        ("A causes B", "E-ENC-004"),
        ("A -> B", "E-ENC-004"),
        ("not A leads to B", "E-ENC-004"),
        ("does A leads to B?", "E-ENC-004"),
        ("A lead to B", "E-ENC-004"),
        # E-ENC-005: more than one sentence
        ("A leads to B and B leads to C", "E-ENC-005"),
        ("A leads to B, B leads to C", "E-ENC-005"),
        ("A leads to B leads to C", "E-ENC-005"),
        # E-ENC-006: reflexive
        ("A leads to A", "E-ENC-006"),
        ("does A lead to A?", "E-ENC-006"),
    )

    def test_anything_outside_the_grammar_is_rejected_with_a_code_not_guessed(self):
        """Every near-miss has a predicted code. A wrong code here means the
        diagnosis order changed, and the order is part of the contract: the
        most informative fault wins."""
        for text, code in self.NEAR_MISSES:
            with self.subTest(text=text):
                exc = refusal(text)
                self.assertEqual(exc.code, code, exc)
                self.assertEqual(exc.text, text)
                self.assertTrue(str(exc).startswith(code + ": "))

    def test_rejected_synonyms_name_the_accepted_form(self):
        """A refusal that only says "no" leaves the boundary implicit; the
        person learns where it is by trial. Naming the accepted form puts the
        whole grammar in the error message."""
        table = (
            ("A causes B", EventKind.FACT),
            ("A results in B", EventKind.FACT),
            ("A implies B", EventKind.FACT),
            ("remember that A leads to B", EventKind.FACT),
            ("unforget that A leads to B", EventKind.FACT),
            ("A lead to B", EventKind.FACT),
            ("A -> B", EventKind.FACT),
            ("A doesn't lead to B", EventKind.NEGATION),
            ("A does not leads to B", EventKind.NEGATION),
            ("A never leads to B", EventKind.NEGATION),
            ("not A leads to B", EventKind.NEGATION),
            ("A might lead to B", EventKind.HYPOTHESIS),
            ("perhaps A leads to B", EventKind.HYPOTHESIS),
            ("suppose A leads to B", EventKind.HYPOTHESIS),
            ("maybe that A leads to B", EventKind.HYPOTHESIS),
            ("is it true that A leads to B?", EventKind.ASK),
            ("does A leads to B?", EventKind.ASK),
            ("forget A leads to B", EventKind.RETRACT),
            ("forget that A lead to B", EventKind.RETRACT),
            ("retract A leads to B", EventKind.RETRACT),
        )
        for text, kind in table:
            with self.subTest(text=text):
                exc = refusal(text)
                self.assertEqual(exc.code, "E-ENC-004", exc)
                self.assertIn(repr(ACCEPTED_FORM[kind]), exc.message)
        # every accepted form is itself in the grammar, so the advice is sound
        for kind, form in ACCEPTED_FORM.items():
            self.assertEqual(encode(form).kind, kind)

    def test_a_compound_sentence_is_refused(self):
        """One sentence is one event. Splitting a compound would mean deciding
        how its clauses relate, which is the reasoner's job, not the parser's.
        A compound wins over the other codes because splitting it is what the
        person has to do before any other advice applies."""
        for text in (
            "A leads to B and B leads to C",
            "A leads to B, B leads to C",
            "A leads to B; B leads to C",
            "A leads to B then B leads to C",
            "A leads to B because B leads to C",
            "A leads to B but C leads to D",
            "A leads to B leads to C",
            "A causes B and B causes C",   # also a synonym; compound wins
            "2A leads to B and B leads to C",   # also a bad name; compound wins
        ):
            with self.subTest(text=text):
                self.assertEqual(refusal(text).code, "E-ENC-005")

    def test_a_reflexive_statement_is_refused(self):
        """`events.Event` already refuses `A -> A` as E-EV-003. The encoder
        re-raises it as E-ENC-006 so a caller handles one error vocabulary,
        and keeps the original as the cause so nothing is hidden."""
        for template in (
            "{a} leads to {a}.",
            "{a} does not lead to {a}.",
            "maybe {a} leads to {a}.",
            "forget that {a} leads to {a}.",
            "does {a} lead to {a}?",
        ):
            text = template.format(a="A")
            with self.subTest(text=text):
                exc = refusal(text)
                self.assertEqual(exc.code, "E-ENC-006")
                self.assertIsInstance(exc.__cause__, events.EventError)
                self.assertEqual(exc.__cause__.code, "E-EV-003")

    def test_a_question_without_its_mark_is_refused_and_vice_versa(self):
        """The '?' is the only thing that separates asking from asserting in
        this grammar, so it cannot be optional in either direction: dropping
        it would turn a question into a fact the workspace then believes."""
        for text in ("does A lead to B", "does A lead to B.", "Does A lead to B"):
            with self.subTest(text=text):
                exc = refusal(text)
                self.assertEqual(exc.code, "E-ENC-003")
                self.assertIn("'?'", exc.message)
        for text in (
            "A leads to B?",
            "A does not lead to B?",
            "maybe A leads to B?",
            "forget that A leads to B?",
        ):
            with self.subTest(text=text):
                exc = refusal(text)
                self.assertEqual(exc.code, "E-ENC-003")
                self.assertIn("statement", exc.message)


class InverseTests(unittest.TestCase):
    def test_round_trip_over_a_generated_corpus(self):
        """`encode(render(e)) == e` for every kind over several hundred random
        names, including names spelled like keywords. The second assertion is
        the stronger one: exactly one production reads each rendered sentence,
        so the language is unambiguous for any NAME, not just the tidy ones."""
        rng = random.Random(20261006)
        first = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
        rest = first + "0123456789_-"
        keyword_shaped = (
            "maybe", "Maybe", "does", "Does", "forget", "Forget", "that",
            "leads", "lead", "to", "not", "and", "causes", "perhaps",
        )

        def name() -> str:
            if rng.random() < 0.15:
                return rng.choice(keyword_shaped)
            length = rng.randint(1, 10)
            return rng.choice(first) + "".join(rng.choice(rest) for _ in range(length - 1))

        builders = (events.fact, events.negation, events.hypothesis, events.retract, events.ask)
        corpus: list[events.Event] = []
        while len(corpus) < 600:
            subject, obj = name(), name()
            if subject == obj:
                continue
            corpus.append(rng.choice(builders)(subject, obj))

        self.assertEqual({e.kind for e in corpus}, set(EventKind))
        for event in corpus:
            sentence = render(event)
            with self.subTest(sentence=sentence):
                self.assertEqual(encode(sentence), event)
                readings = [p for p in PRODUCTIONS if p.pattern.fullmatch(sentence)]
                self.assertEqual(len(readings), 1)
                self.assertEqual(sentence[-1], "?" if event.kind is EventKind.ASK else ".")

    def test_render_refuses_what_encode_could_not_read_back(self):
        """A rendered sentence the encoder would refuse is meaning leaving the
        grammar through the back door. Associative links have no production;
        a name with a space or a leading digit is not a NAME."""
        with self.assertRaises(EncodeError) as ctx:
            render(events.associate("A", "B"))
        self.assertEqual(ctx.exception.code, "E-ENC-008")
        for subject in ("big city", "2A", "A.B"):
            with self.subTest(subject=subject):
                with self.assertRaises(EncodeError) as ctx:
                    render(events.fact(subject, "B"))
                self.assertEqual(ctx.exception.code, "E-ENC-002")
        with self.assertRaises(EncodeError) as ctx:
            render("A leads to B.")  # type: ignore[arg-type]
        self.assertEqual(ctx.exception.code, "E-ENC-008")


class VerdictTests(unittest.TestCase):
    def test_decode_verdict_templates(self):
        """Fixed templates, so a reader can see the sentence adds nothing the
        processor did not conclude. Support is rendered in the order given,
        because that order is the derivation."""
        self.assertEqual(
            decode_verdict("YES", "A", "Z", support=("A|leads_to|B", "B|leads_to|Z")),
            "Yes: A leads to Z, because A leads to B, B leads to Z.",
        )
        self.assertEqual(
            decode_verdict("YES", "A", "Z", support=("B|leads_to|Z", "A|leads_to|B")),
            "Yes: A leads to Z, because B leads to Z, A leads to B.",
        )
        self.assertEqual(decode_verdict("YES", "A", "Z"), "Yes: A leads to Z.")
        self.assertEqual(
            decode_verdict("NO", "A", "Z"),
            "No: A leads to Z does not follow from what I was given.",
        )
        self.assertEqual(
            decode_verdict("UNKNOWN", "A", "Z", lacunae=("U|leads_to|V",)),
            "Unknown: I would need to know whether U leads to V.",
        )
        self.assertEqual(
            decode_verdict("UNKNOWN", "A", "Z", lacunae=("U|leads_to|V", "X|leads_to|Y")),
            "Unknown: I would need to know whether U leads to V and whether X leads to Y.",
        )
        self.assertEqual(
            decode_verdict("UNKNOWN", "A", "Z"),
            "Unknown: I would need to know more.",
        )
        self.assertEqual(
            decode_verdict("INADMISSIBLE", "A", "Z", contested=("U|leads_to|V",)),
            "Inadmissible: U leads to V and U does not lead to V are both held.",
        )
        self.assertEqual(
            decode_verdict(
                "INADMISSIBLE", "A", "Z", contested=("U|leads_to|V", "X|leads_to|Y")
            ),
            "Inadmissible: U leads to V and U does not lead to V are both held; "
            "X leads to Y and X does not lead to Y are both held.",
        )

    def test_a_verdict_outside_the_four_is_refused(self):
        """No template, no sentence. A lowercase 'yes' is not read as YES for
        the same reason 'causes' is not read as 'leads to'."""
        for answer in ("MAYBE", "yes", "", "NEEDS_INFORMATION", None):
            with self.subTest(answer=answer):
                with self.assertRaises(EncodeError) as ctx:
                    decode_verdict(answer, "A", "Z")  # type: ignore[arg-type]
                self.assertEqual(ctx.exception.code, "E-ENC-007")
        with self.assertRaises(EncodeError) as ctx:
            decode_verdict("INADMISSIBLE", "A", "Z")
        self.assertEqual(ctx.exception.code, "E-ENC-007")
        for key in ("A|B", "A|co_occurs|B", "|leads_to|B", "A leads to B"):
            with self.subTest(key=key):
                with self.assertRaises(EncodeError) as ctx:
                    decode_verdict("YES", "A", "Z", support=(key,))
                self.assertEqual(ctx.exception.code, "E-ENC-007")


class NoModelInTheLoopTests(unittest.TestCase):
    """The encoder is a peripheral, and a peripheral with a model behind it is
    the harness this project set out not to build."""

    ALLOWED = {"__future__", "re", "dataclasses", "enum", "typing", "events"}
    #: Mirrors `test_cas_rpu_sever.py`; a plain-text check that survives any
    #: import style.
    FORBIDDEN = (
        "openai", "anthropic", "ollama", "transformers", "torch", "requests",
        "httpx", "urllib", "socket", "http.client", "runners", "wrap",
        "subprocess", "json", "os", "importlib",
    )
    #: The sever suite's allowlist for `from ... import` lines in this
    #: package. `events` is not on it, so the encoder reaches its sibling with
    #: a plain `import` and the sever suite stays green without being edited.
    SEVER_FROM_ALLOWED = {"__future__", "dataclasses", "enum", "typing"}

    def test_the_encoder_imports_no_model_and_no_transport(self):
        source = (PACKAGE / "encoder.py").read_text()
        tree = ast.parse(source)
        plain: set[str] = set()
        from_lines: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                plain.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                from_lines.add((node.module or "").split(".")[0])
        imported = plain | from_lines
        self.assertLessEqual(imported, self.ALLOWED, imported - self.ALLOWED)
        self.assertIn("events", plain, "the shared Event type must come from events.py")
        self.assertIn("re", plain)
        self.assertLessEqual(from_lines, self.SEVER_FROM_ALLOWED)
        for banned in self.FORBIDDEN:
            self.assertNotIn(f"import {banned}", source)
        self.assertNotIn("__import__", source)
        self.assertNotIn("importlib", source)
        self.assertNotIn("open(", source)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
