"""
Cloud-based IA client for Step 3A1 (experience selection).
Uses Ollama Cloud to run GLM-4.7 (cloud) via the ollama Python client.

Env vars needed:
  - OLLAMA_API_KEY  → get from https://ollama.com (account settings)

pip install ollama
"""

import os
import json
import time

from utils.c_ia.ollama_client import SYSTEM_PROMPT

# ── Ollama Cloud config ────────────────────────────────────────
OLLAMA_CLOUD_HOST  = "https://ollama.com"
OLLAMA_CLOUD_MODEL = "qwen3.5:cloud "


def query_cloud_json(
    prompt: str,
    system_prompt: str = None,
    temperature: float = 0.0,
    num_predict: int = 800,
    max_retries: int = 3,
) -> dict | None:
    """
    Call GLM-4.7 via Ollama Cloud for Step 3A1 experience selection.
    Uses the official ollama Python client (NOT raw requests).

    Returns parsed JSON dict or None on failure.
    """
    try:
        from ollama import Client
    except ImportError:
        print("  [Cloud] ❌ ollama package not installed → pip install ollama")
        return None

    api_key = os.environ.get("OLLAMA_API_KEY")
    if not api_key:
        print("  [Cloud] ❌ OLLAMA_API_KEY not set!")
        print("  [Cloud]    → Get one at https://ollama.com (account settings)")
        print("  [Cloud]    → Then: export OLLAMA_API_KEY='your-key-here'")
        return None

    if system_prompt is None:
        system_prompt = SYSTEM_PROMPT

    client = Client(
        host=OLLAMA_CLOUD_HOST,
        headers={"Authorization": f"Bearer {api_key}"},
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": prompt},
    ]

    for attempt in range(1, max_retries + 1):
        try:
            print(f"  [Cloud] 🌐 GLM-4.7 via Ollama Cloud (attempt {attempt}/{max_retries})...")
            start = time.time()

            # ── Non-streaming call: collect full response at once ──
            response = client.chat(
                model=OLLAMA_CLOUD_MODEL,
                messages=messages,
                stream=False,
                think=False,
                options={
                    "temperature": temperature,
                    "num_predict": num_predict,
                },
            )
            elapsed = time.time() - start

            raw_text = response["message"]["content"]
            prompt_tokens = response.get("prompt_eval_count", 0)
            gen_tokens    = response.get("eval_count", 0)

            print(
                f"  [Cloud] ⏱️  {elapsed:.1f}s | "
                f"prompt: {prompt_tokens} tok | "
                f"generated: {gen_tokens} tok"
            )

            if not raw_text or not raw_text.strip():
                print(f"  [Cloud] ⚠️  Empty response (attempt {attempt}/{max_retries})")
                if attempt < max_retries:
                    time.sleep(2 ** attempt)
                continue

            # ── Strip <think>...</think> blocks if present ──
            cleaned = raw_text
            while "<think>" in cleaned and "</think>" in cleaned:
                think_start = cleaned.index("<think>")
                think_end   = cleaned.index("</think>") + len("</think>")
                cleaned = cleaned[:think_start] + cleaned[think_end:]
            cleaned = cleaned.strip()

            # ── Try direct JSON parse ──
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                pass

            # ── Extract JSON object from surrounding text ──
            start_idx = cleaned.find("{")
            end_idx   = cleaned.rfind("}") + 1
            if start_idx != -1 and end_idx > start_idx:
                try:
                    return json.loads(cleaned[start_idx:end_idx])
                except json.JSONDecodeError:
                    pass

            print(f"  [Cloud] ⚠️  JSON parse failed (attempt {attempt}/{max_retries})")
            print(f"  [Cloud]    Raw: {raw_text[:300]}")
            if attempt < max_retries:
                time.sleep(2 ** attempt)

        except Exception as e:
            print(f"  [Cloud] ⚠️  Error: {e} (attempt {attempt}/{max_retries})")
            if attempt < max_retries:
                time.sleep(2 ** attempt)

    print(f"  [Cloud] ❌ All {max_retries} attempts failed.")
    return None