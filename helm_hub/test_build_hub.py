"""Tests for the HELM Hub builder. Run: python -m unittest helm_hub/test_build_hub.py -v (about 5 s)."""
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

HUB = Path(__file__).resolve().parent
sys.path.insert(0, str(HUB))
import build_hub as b  # noqa: E402


class BuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        t0 = time.perf_counter()
        cls.proc = subprocess.run([sys.executable, str(HUB / "build_hub.py")], capture_output=True, text=True,
                                  encoding="utf-8", errors="replace", timeout=300)
        cls.elapsed = time.perf_counter() - t0
        cls.report = b.check_site()

    def test_build_exits_clean_under_300_s(self):
        self.assertEqual(self.proc.returncode, 0, self.proc.stdout[-3000:] + self.proc.stderr[-3000:])
        self.assertLess(self.elapsed, 300)

    def test_all_pages_written(self):
        for name, _ in b.NAV:
            self.assertTrue((b.SITE / name).exists(), name)
        self.assertTrue((b.SITE / "demo.html").exists())

    def test_jargon_lint_passes(self):
        self.assertEqual(self.report["lint"], [])

    def test_links_resolve(self):
        self.assertEqual(self.report["links"], [])

    def test_no_secrets_emails_or_keys(self):
        self.assertEqual(self.report["secrets"], [])

    def test_page_contract(self):
        self.assertEqual(self.report["contract"], [])
        self.assertEqual(self.report["emoji"], [])

    def test_no_prohibited_words_in_hub_text(self):
        self.assertEqual(self.report["prohibited"], [])

    def test_every_lint_term_is_in_the_glossary(self):
        g = (b.SITE / "glossary.html").read_text(encoding="utf-8")
        for k in b.TERMS:
            self.assertRegex(g, b.TERM_RES[k], k)

    def test_backslash_path_survives_the_build_byte_for_byte(self):
        g = (b.SITE / "glossary.html").read_text(encoding="utf-8")
        self.assertIn(r"Documents\Codex\2026-10-18\OWNER_APPROVALS_20261018.md", g)

    def test_backslash_digits_survive_every_text_path(self):
        path = r"C:\Users\wakil\Documents\Codex\2026-10-18\x\1\0.md"
        for s in (path, "**" + path + "**", "*" + path + "*", "`" + path + "`", "[" + path + "](u)"):
            self.assertIn(path, b.md(s))
        tbl = b.cardify(b.html_table([["Head"], [path]]))
        self.assertIn(path, tbl)

    def test_ctt_is_in_the_glossary_and_the_lint(self):
        g = (b.SITE / "glossary.html").read_text(encoding="utf-8")
        for t in ("CTT-1", "CTT-2R", "E-MACHINE-S", "Ears / mouth", "9,585,566", "2,482,718"):
            self.assertIn(t, g)
        self.assertIn("CTT", b.TERMS)

    def test_wave_and_pair_wave_defined(self):
        g = (b.SITE / "glossary.html").read_text(encoding="utf-8")
        self.assertIn("Pair wave", g)
        self.assertIn("HELM-R1 wave 6", g)
        self.assertIn("one sealed test round in the HELM-R1 series", g)
        for name in ("build.html", "results.html", "roadmap.html"):
            t = (b.SITE / name).read_text(encoding="utf-8")
            box = t[t.find('<details class="words"'):]
            box = box[:box.find("</details>")]
            self.assertIn('data-term="wave"', box, name)
            self.assertIn('data-term="pair wave"', box, name)
        idx = (b.SITE / "index.html").read_text(encoding="utf-8")
        self.assertIn('<dfn data-term="pair wave"', idx)

    def test_build_page_static_fallback_without_js(self):
        t = (b.SITE / "build.html").read_text(encoding="utf-8")
        # both scenes are in the HTML and not hidden; only scripts hide the inactive one
        self.assertIn('<section class="scene" id="scene-today">', t)
        self.assertIn('<section class="scene" id="scene-intended">', t)
        self.assertIn("html.js .scene[hidden]{display:none}", t)
        self.assertIn('id="scene-toggle" role="group" aria-label="Choose a scene" hidden>', t)
        # the moving dot is invisible without JS, and reduced motion is respected
        self.assertIn(".token{fill:var(--accent);opacity:0}", t)
        self.assertIn("@media (prefers-reduced-motion: reduce)", t)
        self.assertIn("matchMedia('(prefers-reduced-motion: reduce)')", t)
        # every step caption is static text, and the Eye's write arrow is crossed out
        self.assertGreaterEqual(t.count('<li data-parts='), 20)
        self.assertIn('class="xmark"', t)
        self.assertIn("shares nothing with the brain", t)
        self.assertIn("What this animation does not claim.", t)

    def test_new_pages_are_linked(self):
        for name in ("index.html", "results.html"):
            t = (b.SITE / name).read_text(encoding="utf-8")
            self.assertIn('href="build.html"', t)
            self.assertIn('href="files.html"', t)
        self.assertIn('href="files.html#start"', (b.SITE / "index.html").read_text(encoding="utf-8"))
        self.assertIn('href="build.html"', (b.SITE / "architecture.html").read_text(encoding="utf-8"))

    def test_every_listed_path_exists_or_is_marked_missing(self):
        import html as _h
        import os
        import re
        t = (b.SITE / "files.html").read_text(encoding="utf-8")
        rows = re.findall(r'<tr data-path="([^"]*)" data-exists="(\d)"><td[^>]*>(.*?)</td><td[^>]*>.*?</td><td[^>]*>(.*?)</td>', t, re.S)
        self.assertGreater(len(rows), 50)
        for path, ex, first, info in rows:
            on_disk = os.path.exists(_h.unescape(path))
            self.assertEqual(ex == "1", on_disk, path)
            if not on_disk:
                self.assertIn("MISSING", first + info, path)
        self.assertIn("do not open", t)

    def test_chat_page_exists_and_is_linked(self):
        self.assertIn(("chat.html", "Talking to HELM"), b.NAV)
        t = (b.SITE / "chat.html").read_text(encoding="utf-8")
        for anchor in ('id="scores"', 'id="exchanges"', 'id="cannot"'):
            self.assertIn(anchor, t)
        self.assertIn("NOT LICENSED", t)
        self.assertIn('href="chat.html"', (b.SITE / "index.html").read_text(encoding="utf-8"))
        self.assertFalse(any("chat.html" in e for e in self.report["lint"]), self.report["lint"])

    def test_chat_page_has_the_four_runs_with_exact_words(self):
        t = (b.SITE / "chat.html").read_text(encoding="utf-8")
        for job in ("c51", "c52", "c53", "c54"):
            self.assertIn(f"<strong>{job}</strong>", t)
        for w in ("FAILURE", "INCONCLUSIVE", "CHAT_WAVE_NO_GAIN", "INSTRUMENT_ERROR", "96 right / 0 wrong", "91 right / 0 wrong",
                  "99 right / 0 wrong", "95 of 97", "91 of 94", "100 of 101", "43 right / 0 wrong", "44 right / 0 wrong", "0.01 USD", "0.02 USD"):
            self.assertIn(w, t, w)
        self.assertEqual(t.count("CHAT_WAVE_NO_GAIN</span>"), 2)

    def test_chat_page_has_at_least_ten_real_transcripts_from_c53_only(self):
        import json
        d = json.loads(b.CHAT_SAMPLES.read_text(encoding="utf-8"))
        n = sum(len(v) for v in d["samples"].values())
        self.assertGreaterEqual(n, 10)
        self.assertEqual(d["job"], "c53")
        t = (b.SITE / "chat.html").read_text(encoding="utf-8")
        self.assertGreaterEqual(t.count('<div class="chat">'), 10)
        self.assertGreaterEqual(t.count("job c53, spent exam"), 10)
        blocks = t.split('<div class="chat">')[1:]
        self.assertTrue(all("job c53, spent exam" in blk.split("</div>")[0] for blk in blocks))
        self.assertFalse(any("c54" in blk.split("</div>")[0] for blk in blocks))
        for tr in (x for v in d["samples"].values() for x in v):
            self.assertIn(tr["id"], t)
            for turn in tr["turns"]:
                self.assertIn(b.esc(turn["helm"]), t)
        self.assertIn('inside: WITNESS_ADMITTED', t)
        self.assertIn('class="msg you noise"', t)

    def test_roadmap_carries_the_intended_talk_section_with_the_owners_words(self):
        r = (b.SITE / "roadmap.html").read_text(encoding="utf-8")
        self.assertIn('id="talk"', r)
        self.assertIn("Intended: talking like a person", r)
        self.assertIn("comment like a normal person would", r)
        self.assertIn("CONVERSE ABOUT", r)
        self.assertIn("TRANSFORMER TRAINED ON THE 40 ELEMENTS", r)
        self.assertGreaterEqual(r.count("INTENDED / NOT A PRESENT CAPABILITY / NOTHING LICENSED"), 9)
        self.assertIn("LLM_WRITTEN_ONLY", r)

    def test_negatives_are_on_the_scorecard(self):
        r = (b.SITE / "results.html").read_text(encoding="utf-8")
        for w in ("S_UNSAFE_ON_REAL", "EARS_HARMED", "GREW_WRONG_KIND", "WIDE_LEARNING_DID_NOT_EARN_KEEP"):
            self.assertIn(w, r)


class CheckerCanTripTests(unittest.TestCase):
    """The checks must be able to fail; otherwise a pass means nothing."""

    def _page(self, body: str) -> Path:
        d = Path(tempfile.mkdtemp())
        html = ('<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
                '<title>Two Words</title></head><body><main>' + body + '</main></body></html>')
        (d / "x.html").write_text(html, encoding="utf-8")
        return d / "x.html"

    def test_lint_flags_unexplained_term(self):
        errs = b.lint_page(self._page("<p>The recipe brain names the limiting reagent.</p>"))
        self.assertTrue(any("recipe brain" in e for e in errs))

    def test_lint_accepts_explained_term(self):
        errs = b.lint_page(self._page("<p>" + b.T("recipe brain", also=("recipe",)) + " works.</p>"))
        self.assertFalse(any("'recipe brain'" in e for e in errs))

    def test_secret_scan_flags_planted_values(self):
        p = self._page("<p>write to someone@example.com with AKIA" + "ABCDEFGHIJKLMNOP</p>")
        rep = b.check_site(p.parent)
        kinds = " ".join(rep["secrets"])
        self.assertIn("e-mail", kinds)
        self.assertIn("AWS access key id", kinds)

    def test_contract_flags_c1_control_character(self):
        p = self._page("<p>Codex\x826-10-18</p>")
        self.assertTrue(any("C1 control character" in c for c in b.check_site(p.parent)["contract"]))

    def test_link_check_flags_broken_link(self):
        p = self._page('<p><a href="nowhere.html">x</a></p>')
        self.assertTrue(b.check_site(p.parent)["links"])


if __name__ == "__main__":
    unittest.main()
