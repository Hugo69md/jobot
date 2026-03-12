"""
Cloud-based IA client for Step 3A1 (experience selection).
Uses Ollama Cloud to run GLM-4.7 (cloud) via the official ollama Python client.

Env vars needed:
  - OLLAMA_API_KEY  → get from https://ollama.com (account settings)

Also contains a placeholder for direct Zhipu GLM-4.7-Flash API (for later).
"""

import os
import json
import re
import time
from ollama import Client

# ── Ollama Cloud config ────────────────────────────────────────
OLLAMA_CLOUD_HOST  = "https://ollama.com"
OLLAMA_CLOUD_MODEL = "glm-4.7:cloud"        # GLM-4.7 hosted on Ollama Cloud

# ── System prompt (same as local Ollama) ───────────────────────
SYSTEM_PROMPT = (
    "Tu es un expert en recrutement, spécialisé dans l'optimisation de CV "
    "et la rédaction de lettres de motivation pour les stages en entreprise.\n\n"
    "Règles absolues à respecter sur TOUTES les réponses :\n"
    "- Tu ne mens JAMAIS\n"
    "- Tu n'inventes JAMAIS de compétences, chiffres ou expériences absents des données fournies.\n"
    "- Toujours respecter ces instructions"
)


def query_cloud_json(
    prompt: str,
    system_prompt: str = None,
    temperature: float = 0.0,
    num_predict: int = 800,
    max_retries: int = 3,
) -> dict | None:
    """
    Call GLM-4.7 via Ollama Cloud for Step 3A1 experience selection.
    Uses the official ollama Python client with stream=False.

    Returns parsed JSON dict or None on failure.
    """
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
        {"role": "user", "content": prompt},
    ]

    options = {
        "temperature": temperature,
        "num_predict": num_predict,
    }

    for attempt in range(1, max_retries + 1):
        try:
            print(f"  [Cloud] 🌐 GLM-4.7 via Ollama Cloud (attempt {attempt}/{max_retries})...")
            start = time.time()

            response = client.chat(
                model=OLLAMA_CLOUD_MODEL,
                messages=messages,
                stream=False,
                options=options,
            )
            elapsed = time.time() - start

            prompt_tok = response.prompt_eval_count or 0
            gen_tok    = response.eval_count or 0
            print(f"  [Cloud] ⏱️  {elapsed:.1f}s | prompt: {prompt_tok} tok | generated: {gen_tok} tok")

            raw_text = response.message.content or ""

            if not raw_text.strip():
                print(f"  [Cloud] ⚠️  Empty response (attempt {attempt}/{max_retries})")
                if attempt < max_retries:
                    time.sleep(2 ** attempt)
                continue

            # Strip <think>...</think> reasoning blocks (used by some GLM variants)
            raw_text = re.sub(r"<think>.*?</think>", "", raw_text, flags=re.DOTALL).strip()

            # Parse JSON from response
            try:
                return json.loads(raw_text)
            except json.JSONDecodeError:
                # Try to extract JSON object from surrounding text
                start_idx = raw_text.find("{")
                end_idx   = raw_text.rfind("}") + 1
                if start_idx != -1 and end_idx > start_idx:
                    try:
                        return json.loads(raw_text[start_idx:end_idx])
                    except json.JSONDecodeError:
                        pass
                print(f"  [Cloud] ⚠️  JSON parse failed (attempt {attempt}/{max_retries})")
                print(f"  [Cloud]    Raw response: {raw_text[:300]}")
                if attempt < max_retries:
                    time.sleep(2 ** attempt)

        except Exception as e:
            print(f"  [Cloud] ⚠️  Error: {e} (attempt {attempt}/{max_retries})")
            if attempt < max_retries:
                time.sleep(2 ** attempt)

    print(f"  [Cloud] ❌ All {max_retries} attempts failed.")
    return None
