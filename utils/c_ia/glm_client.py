"""
Zhipu GLM-4-Flash API client for Steps 2, 3a-1, and 3a-2.
Uses raw requests (no openai dependency).

Env vars needed:
  - ZHIPU_API_KEY  → get from https://open.bigmodel.cn
"""

import os
import json
import time
import requests

from utils.c_ia.ollama_client import SYSTEM_PROMPT

# ── Zhipu API config ───────────────────────────────────────────
ZHIPU_API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
ZHIPU_MODEL   = "glm-4-flash"


def query_glm_json(
    prompt: str,
    system_prompt: str = None,
    temperature: float = 0.0,
    max_tokens: int = 512,
    max_retries: int = 3,
) -> dict | None:
    """
    Call GLM-4-Flash directly via Zhipu's API using raw requests.
    Returns parsed JSON dict or None on failure.

    Env var: ZHIPU_API_KEY
    """
    api_key = os.environ.get("ZHIPU_API_KEY")
    if not api_key:
        print("  [Zhipu] ❌ ZHIPU_API_KEY not set!")
        print("  [Zhipu]    → Register at https://open.bigmodel.cn")
        print("  [Zhipu]    → Then: export ZHIPU_API_KEY='your-key-here'")
        return None

    if system_prompt is None:
        system_prompt = SYSTEM_PROMPT

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    body = {
        "model": ZHIPU_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
    }

    for attempt in range(1, max_retries + 1):
        try:
            print(f"  [Zhipu] 🌐 {ZHIPU_MODEL} (attempt {attempt}/{max_retries})...")
            start = time.time()

            response = requests.post(ZHIPU_API_URL, headers=headers, json=body, timeout=120)
            response.raise_for_status()
            elapsed = time.time() - start
            data = response.json()
            choices = data.get("choices")
            if not choices:
                print(f"  [Zhipu] ⚠️  Unexpected response format (attempt {attempt}/{max_retries}): {data}")
                if attempt < max_retries:
                    time.sleep(2 ** attempt)
                continue
            raw_text = choices[0]["message"]["content"]
            print(f"  [Zhipu] ⏱️  Response in {elapsed:.1f}s")

            try:
                return json.loads(raw_text)
            except json.JSONDecodeError:
                start_idx = raw_text.find("{")
                end_idx = raw_text.rfind("}") + 1
                if start_idx != -1 and end_idx > 0 and end_idx > start_idx:
                    try:
                        return json.loads(raw_text[start_idx:end_idx])
                    except json.JSONDecodeError:
                        pass
                print(f"  [Zhipu] ⚠️  JSON parse failed (attempt {attempt}/{max_retries})")
                if attempt < max_retries:
                    time.sleep(2 ** attempt)

        except Exception as e:
            print(f"  [Zhipu] ⚠️  Error: {e} (attempt {attempt}/{max_retries})")
            if attempt < max_retries:
                time.sleep(2 ** attempt)

    print(f"  [Zhipu] ❌ All {max_retries} attempts failed.")
    return None
