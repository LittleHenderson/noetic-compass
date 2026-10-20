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
