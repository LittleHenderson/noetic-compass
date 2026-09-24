"""pytest set-up for test_hset2.py (CLAUDE_BUILT_CLAUDE_CHECKED): registers the e2e and slow markers."""


def pytest_configure(config):
    config.addinivalue_line("markers", "e2e: the tiny end-to-end build with throwaway salts (about 2 minutes)")
    config.addinivalue_line("markers", "slow: the trained-answer-state re-measurement, 158 frozen-checker targets (about 2 minutes)")
