"""
Cloud-based IA client for Step 3A1 (experience selection).
Uses Ollama Cloud to run GLM-4.7 (cloud) — same API format as local Ollama.

Env vars needed:
  - OLLAMA_API_KEY  → get from https://ollama.com (account settings)

Also contains a placeholder for direct Zhipu GLM-4.7-Flash API (for later).
"""

import os
import json
import time
import requests

# ── Ollama Cloud config ────────────────────────────────────────
OLLAMA_CLOUD_URL   = "https://ollama.com/api/chat"
OLLAMA_CLOUD_MODEL = "glm-4.7:cloud"        # GLM-4.7 running on Ollama's servers

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
    num_predict: int = 512,
    max_retries: int = 3,
) -> dict | None:
    """
    Call GLM-4.7 via Ollama Cloud for Step 3A1 experience selection.
    Same API format as local Ollama, but runs on Ollama's cloud servers.
    
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

    payload = {
        "model": OLLAMA_CLOUD_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        "stream": True,
        "format": "json",
        "options": {
            "temperature": temperature,
            "num_predict": num_predict,
        },
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    for attempt in range(1, max_retries + 1):
        try:
            print(f"  [Cloud] 🌐 GLM-4.7 via Ollama Cloud (attempt {attempt}/{max_retries})...")
            start = time.time()

            response = requests.post(
                OLLAMA_CLOUD_URL,
                json=payload,
                headers=headers,
                timeout=120,
            )
            elapsed = time.time() - start

            if response.status_code != 200:
                print(f"  [Cloud] ⚠️  HTTP {response.status_code}: {response.text[:200]}")
                if attempt < max_retries:
                    time.sleep(2 ** attempt)
                continue

            data = response.json()
            raw_text = data.get("message", {}).get("content", "")
            print(f"  [Cloud] ⏱️  Response in {elapsed:.1f}s")

            # Parse JSON from response
            try:
                return json.loads(raw_text)
            except json.JSONDecodeError:
                # Try to extract JSON from surrounding text
                start_idx = raw_text.find("{")
                end_idx = raw_text.rfind("}") + 1
                if start_idx != -1 and end_idx > start_idx:
                    try:
                        return json.loads(raw_text[start_idx:end_idx])
                    except json.JSONDecodeError:
                        pass
                print(f"  [Cloud] ⚠️  JSON parse failed (attempt {attempt}/{max_retries})")
                if attempt < max_retries:
                    time.sleep(2 ** attempt)

        except requests.exceptions.Timeout:
            print(f"  [Cloud] ⚠️  Timeout (attempt {attempt}/{max_retries})")
            if attempt < max_retries:
                time.sleep(2 ** attempt)

        except requests.exceptions.ConnectionError:
            print(f"  [Cloud] ⚠️  Connection error (attempt {attempt}/{max_retries})")
            if attempt < max_retries:
                time.sleep(5)

        except Exception as e:
            print(f"  [Cloud] ⚠️  Error: {e} (attempt {attempt}/{max_retries})")
            if attempt < max_retries:
                time.sleep(2 ** attempt)

    print(f"  [Cloud] ❌ All {max_retries} attempts failed.")
    return None
