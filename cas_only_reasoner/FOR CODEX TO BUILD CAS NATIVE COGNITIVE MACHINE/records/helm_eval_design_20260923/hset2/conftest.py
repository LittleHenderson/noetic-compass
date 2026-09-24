"""pytest set-up for test_hset2.py (CLAUDE_BUILT_CLAUDE_CHECKED): registers the e2e marker."""


def pytest_configure(config):
    config.addinivalue_line("markers", "e2e: the tiny end-to-end build with throwaway salts (about 2 minutes)")
