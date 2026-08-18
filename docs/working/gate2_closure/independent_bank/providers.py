"""Shared provider config for the independent-bank pipeline.

Lets blindness_probe.py and gen_bank.py talk to any OpenAI-compatible provider
(DeepSeek, Qwen/DashScope, GLM/Zhipu, Gemini, OpenAI) by a short --provider name.

Keys are loaded from a KEY=VALUE file that lives OUTSIDE the repo (default:
~/.cas_llm_keys.env). This module NEVER prints key values. Callers must never
echo os.environ values either.
"""
import os

# provider -> (OpenAI-compatible base_url, env var name for the key, default model id)
PROVIDERS = {
    "deepseek": {
        "base_url": "https://api.deepseek.com",
        "key_env": "DEEPSEEK_API_KEY",
        "default_model": "deepseek-chat",   # override with --model if V4-Pro uses a different id
    },
    "qwen": {
        "base_url": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
        "key_env": "DASHSCOPE_API_KEY",
        "default_model": "qwen-max",
    },
    "glm": {
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "key_env": "ZHIPU_API_KEY",
        "default_model": "glm-4",
    },
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "key_env": "GEMINI_API_KEY",
        "default_model": "gemini-2.5-flash",
    },
    "openai": {
        "base_url": None,
        "key_env": "OPENAI_API_KEY",
        "default_model": "gpt-4o",
    },
}

DEFAULT_KEYS_FILE = os.path.join(os.path.expanduser("~"), ".cas_llm_keys.env")


def load_keys_file(path: str = None) -> list:
    """Parse a KEY=VALUE file into os.environ (does not overwrite already-set vars).
    Returns the list of key names loaded (names only, never values)."""
    path = path or DEFAULT_KEYS_FILE
    loaded = []
    if not os.path.exists(path):
        return loaded
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip().strip('"').strip("'")
            if k and v and not os.environ.get(k):
                os.environ[k] = v
                loaded.append(k)
    return loaded


def resolve(provider: str, model: str = None, keys_file: str = None):
    """Return (base_url, api_key, model_id) for a provider. Loads the keys file first.
    Raises a clear error (no key value in the message) if the key is missing."""
    load_keys_file(keys_file)
    if provider not in PROVIDERS:
        raise SystemExit(f"unknown provider '{provider}'. known: {', '.join(PROVIDERS)}")
    cfg = PROVIDERS[provider]
    key = os.environ.get(cfg["key_env"])
    if not key:
        raise SystemExit(
            f"missing key for provider '{provider}': set {cfg['key_env']} in "
            f"{keys_file or DEFAULT_KEYS_FILE} (KEY=VALUE, one per line)")
    return cfg["base_url"], key, (model or cfg["default_model"])
