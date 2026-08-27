"""The calibration runner — key handling, prefetch integrity, transport policy.

Nothing here touches the network. The concern is the parts that decide whether
a live run is trustworthy: that the gate scores exactly the set that was
fetched, that a key is read the way the product reads it and never written out,
and that the cloud-only policy is enforced by the code rather than by prose.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "ccb_r1"))

import run_calibration as rc  # noqa: E402
from calibration import honesty_procedure  # noqa: E402
from runners import StubCompletion  # noqa: E402


class DotenvTests(unittest.TestCase):
    def _write(self, text: str) -> Path:
        path = Path(tempfile.mkdtemp()) / ".env"
        path.write_text(text, encoding="utf-8")
        return path

    def test_values_are_loaded(self):
        path = self._write("NC_TEST_KEY=abc123\n")
        with mock.patch.dict("os.environ", {}, clear=False):
            rc.load_dotenv(path)
            self.assertEqual(rc.os.environ["NC_TEST_KEY"], "abc123")

    def test_the_existing_environment_wins(self):
        """A stale file must never override an explicit export."""
        path = self._write("NC_TEST_KEY=from_file\n")
        with mock.patch.dict("os.environ", {"NC_TEST_KEY": "from_shell"}, clear=False):
            rc.load_dotenv(path)
            self.assertEqual(rc.os.environ["NC_TEST_KEY"], "from_shell")

    def test_comments_blanks_and_malformed_lines_are_skipped(self):
        path = self._write("# a comment\n\nnot_a_pair\nNC_OK=1\n")
        with mock.patch.dict("os.environ", {}, clear=False):
            self.assertEqual(rc.load_dotenv(path), 1)

    def test_quotes_are_stripped(self):
        path = self._write('NC_Q="quoted"\n')
        with mock.patch.dict("os.environ", {}, clear=False):
            rc.load_dotenv(path)
            self.assertEqual(rc.os.environ["NC_Q"], "quoted")

    def test_a_missing_file_is_not_an_error(self):
        self.assertEqual(rc.load_dotenv(Path("/nonexistent/.env")), 0)


class KeyResolutionTests(unittest.TestCase):
    PROVIDER = rc.Provider(("NC_X_KEY", "X_KEY"), "https://example.invalid", "m")

    def test_the_prefixed_name_wins(self):
        """Matches api/config.py's AliasChoices order."""
        with mock.patch.dict("os.environ", {"NC_X_KEY": "a", "X_KEY": "b"}, clear=False):
            self.assertEqual(rc.resolve_key(self.PROVIDER), "a")

    def test_the_bare_name_is_the_fallback(self):
        with mock.patch.dict("os.environ", {"X_KEY": "b"}, clear=False):
            self.assertEqual(rc.resolve_key(self.PROVIDER), "b")

    def test_an_empty_value_does_not_count_as_set(self):
        with mock.patch.dict("os.environ", {"NC_X_KEY": "   ", "X_KEY": "b"}, clear=False):
            self.assertEqual(rc.resolve_key(self.PROVIDER), "b")

    def test_no_key_fails_fast_and_names_the_variables(self):
        with mock.patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(SystemExit) as ctx:
                rc.resolve_key(self.PROVIDER)
        self.assertIn("NC_X_KEY", str(ctx.exception))


class TransportPolicyTests(unittest.TestCase):
    def test_no_local_transport_is_reachable_from_the_runner(self):
        """Cloud only, enforced in code rather than in prose.

        Sustained CPU inference was a suspected crash trigger. Ollama and local
        HF transports stay in runners.py for a future GPU host; they must not
        be selectable here.
        """
        for provider in rc.PROVIDERS.values():
            self.assertTrue(provider.base_url.startswith("https://"), provider.base_url)
            self.assertNotIn("127.0.0.1", provider.base_url)
            self.assertNotIn("localhost", provider.base_url)

    def test_every_provider_names_a_prefixed_and_a_bare_key(self):
        for name, provider in rc.PROVIDERS.items():
            self.assertEqual(len(provider.key_env), 2, name)
            self.assertTrue(provider.key_env[0].startswith("NC_"), name)


class PrefetchIntegrityTests(unittest.TestCase):
    def test_each_prompt_is_fetched_exactly_once(self):
        stub = StubCompletion(default="UNKNOWN")
        rc.run(honesty_procedure(n=40), stub, workers=4, retries=0, verbose=False)
        self.assertEqual(len(stub.calls), len(set(stub.calls)))

    def test_the_gate_scores_the_set_that_was_fetched(self):
        """Determinism is what makes the cache sound; assert it rather than trust it."""
        stub = StubCompletion(default="UNKNOWN")
        result, _ = rc.run(honesty_procedure(n=40), stub, workers=4, retries=0, verbose=False)
        fetched = set(stub.calls)
        for attempt in range(len(result.attempts)):
            for item in honesty_procedure(n=40).build(attempt).items:
                self.assertIn(item.prompt(), fetched)

    def test_a_cache_miss_voids_the_run_rather_than_scoring_it(self):
        procedure = honesty_procedure(n=20)
        with mock.patch.object(rc, "fetch_all", return_value={}):
            with self.assertRaises(SystemExit) as ctx:
                rc.run(procedure, StubCompletion(), workers=1, retries=0, verbose=False)
        self.assertIn("void", str(ctx.exception))

    def test_abstention_and_unparseable_counts_reach_the_log(self):
        _, log = rc.run(honesty_procedure(n=40), StubCompletion(default="UNKNOWN"),
                        workers=4, retries=0, verbose=False)
        self.assertEqual(log.abstained, log.scored)
        self.assertEqual(log.unparseable, 0)

        _, noisy = rc.run(honesty_procedure(n=40), StubCompletion(default="!!!"),
                          workers=4, retries=0, verbose=False)
        self.assertEqual(noisy.unparseable, noisy.scored)


class FetchFailureTests(unittest.TestCase):
    def test_a_persistent_failure_becomes_empty_text_not_an_abort(self):
        """A dead prompt shows up as unparseable, which the result file reports."""
        def broken(_prompt: str) -> str:
            raise OSError("connection reset")

        replies = rc.fetch_all(broken, ["a", "b"], workers=2, retries=0)
        self.assertEqual(replies, {"a": "", "b": ""})

    def test_a_transient_failure_is_retried(self):
        state = {"calls": 0}

        def flaky(prompt: str) -> str:
            state["calls"] += 1
            if state["calls"] == 1:
                raise OSError("transient")
            return "UNKNOWN"

        with mock.patch.object(rc.time, "sleep", lambda _s: None):
            replies = rc.fetch_all(flaky, ["a"], workers=1, retries=2)
        self.assertEqual(replies["a"], "UNKNOWN")
        self.assertEqual(state["calls"], 2)


class ResultFileTests(unittest.TestCase):
    def test_the_run_is_recorded_with_its_provider_pinned(self):
        """"DeepSeek" is not a specification; provider, model and temperature are."""
        out = Path(tempfile.mkdtemp()) / "result.json"
        stub = StubCompletion(default="UNKNOWN")
        with mock.patch.object(rc, "build_completion", return_value=stub), \
             mock.patch.object(rc, "load_dotenv", return_value=0):
            code = rc.main([
                "--kind", "honesty", "--provider", "deepseek", "--n", "40",
                "--workers", "2", "--retries", "0", "--quiet", "--out", str(out),
            ])
        self.assertEqual(code, 1)  # always-UNKNOWN is AT_CHANCE, so not accepted

        payload = json.loads(out.read_text())
        self.assertEqual(payload["kind"], "honesty")
        self.assertEqual(payload["provider"], "deepseek")
        self.assertEqual(payload["model"], "deepseek-chat")
        self.assertEqual(payload["temperature"], 0.0)
        self.assertEqual(payload["status"], "AT_CHANCE")
        self.assertFalse(payload["accepted"])
        self.assertEqual(len(payload["attempts"]), 3)
        self.assertEqual(payload["procedure_fingerprint"],
                         honesty_procedure(n=40).fingerprint())

    def test_the_result_file_carries_no_credential(self):
        out = Path(tempfile.mkdtemp()) / "result.json"
        stub = StubCompletion(default="UNKNOWN")
        with mock.patch.object(rc, "build_completion", return_value=stub), \
             mock.patch.object(rc, "load_dotenv", return_value=0), \
             mock.patch.dict("os.environ", {"NC_DEEPSEEK_API_KEY": "sk-secret-value"}):
            rc.main(["--kind", "honesty", "--n", "20", "--workers", "2",
                     "--retries", "0", "--quiet", "--out", str(out)])
        text = out.read_text()
        self.assertNotIn("sk-secret-value", text)
        self.assertNotIn("api_key", text)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
