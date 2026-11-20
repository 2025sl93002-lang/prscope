"""Optional local AI assistance (Ollama).

Strictly optional and off by default. If a local Ollama runtime is reachable it
can *explain* existing deterministic findings in prose — it never invents
dependencies, findings, or evidence, and no repository code is sent to any
external (non-localhost) service. If the runtime is unavailable, callers fall
back to the deterministic explanation. Uses only the Python standard library
(``urllib``) — no extra dependency. SPDX-License-Identifier: MIT
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request

_SYSTEM = (
    "You are a code-review assistant. You will be given deterministic analysis "
    "findings produced by a static analyzer. Explain them clearly for a reviewer. "
    "Do NOT invent files, dependencies, test results, or evidence that are not in "
    "the provided findings. If information is missing, say so."
)


def is_available(endpoint: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(f"{endpoint.rstrip('/')}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - localhost only
            return resp.status == 200
    except (urllib.error.URLError, OSError, ValueError):
        return False


def explain(endpoint: str, model: str, context_text: str, timeout: float = 30.0) -> str | None:
    """Return an AI explanation, or None if the runtime is unavailable/errors."""
    payload = json.dumps({
        "model": model,
        "system": _SYSTEM,
        "prompt": context_text,
        "stream": False,
    }).encode("utf-8")
    try:
        req = urllib.request.Request(
            f"{endpoint.rstrip('/')}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - localhost only
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("response", "").strip() or None
    except (urllib.error.URLError, OSError, ValueError, json.JSONDecodeError):
        return None
