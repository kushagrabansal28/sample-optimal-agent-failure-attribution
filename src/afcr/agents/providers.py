"""Model-provider abstraction: the statistical algorithm never imports a model SDK.

* ``ScriptedProvider``      deterministic, no model needed (used by tests and the synthetic mode)
* ``RecordingProvider``     wraps any provider and records (prompt, seed) -> completion, so a recorded prefix can be replayed exactly
* ``OpenAICompatProvider``  OpenAI-compatible HTTP endpoint (hosted, vLLM, Ollama ``/v1``).  Needs the optional ``openai`` extra and
                            an API key / base URL taken from the environment at call time.  NOT exercised by the test-suite
                            (no key, no network) — treat as untested until you run it against your own endpoint.
"""
from __future__ import annotations

import os
from collections.abc import Callable
from typing import Protocol


class ModelProvider(Protocol):
    name: str

    def complete(self, prompt: str, *, seed: int | None = None, temperature: float = 0.0, max_tokens: int = 128) -> str: ...


class ScriptedProvider:
    """``fn(prompt, seed, temperature) -> str``; fully deterministic given its arguments."""

    def __init__(self, fn: Callable[[str, int | None, float], str], name: str = "scripted"):
        self.fn, self.name = fn, name

    def complete(self, prompt, *, seed=None, temperature=0.0, max_tokens=128):
        return self.fn(prompt, seed, temperature)


class RecordingProvider:
    def __init__(self, inner: ModelProvider):
        self.inner, self.name = inner, f"recording({inner.name})"
        self.log: dict[tuple[str, int | None, float], str] = {}

    def complete(self, prompt, *, seed=None, temperature=0.0, max_tokens=128):
        key = (prompt, seed, temperature)
        if key not in self.log:
            self.log[key] = self.inner.complete(prompt, seed=seed, temperature=temperature, max_tokens=max_tokens)
        return self.log[key]


class OpenAICompatProvider:
    def __init__(self, model: str, *, base_url_env: str = "OPENAI_BASE_URL", api_key_env: str = "OPENAI_API_KEY"):
        self.model, self.name = model, f"openai-compat:{model}"
        self.base_url_env, self.api_key_env = base_url_env, api_key_env

    def complete(self, prompt, *, seed=None, temperature=0.0, max_tokens=128):
        try:
            from openai import OpenAI
        except ImportError as e:                                    # pragma: no cover
            raise RuntimeError("install the optional extra: pip install -e '.[llm]'") from e
        key = os.environ.get(self.api_key_env)
        if not key:
            raise RuntimeError(f"environment variable {self.api_key_env} is not set (see .env.example)")
        client = OpenAI(api_key=key, base_url=os.environ.get(self.base_url_env) or None)    # pragma: no cover
        r = client.chat.completions.create(model=self.model, messages=[{"role": "user", "content": prompt}], temperature=temperature,
                                           max_tokens=max_tokens, seed=seed)       # pragma: no cover
        return r.choices[0].message.content or ""                                  # pragma: no cover
