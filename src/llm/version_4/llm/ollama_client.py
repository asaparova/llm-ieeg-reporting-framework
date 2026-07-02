from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

import requests


def call_ollama(
    prompt: str,
    model_name: str,
    ollama_url: str,
    json_mode: bool,
    timeout: Optional[Tuple[int, int]] = (30, 1800),
) -> str:
    payload: Dict[str, Any] = {
        "model": model_name,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.0,
            "top_p": 1.0,
            "num_predict": 2200,
        },
    }

    if json_mode:
        payload["format"] = "json"

    resp = requests.post(ollama_url, json=payload, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    return data["response"]