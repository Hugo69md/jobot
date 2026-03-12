# pip install openai
import json
import os
import time
from openai import OpenAI

from utils.c_ia.ollama_client import SYSTEM_PROMPT

# ── DeepSeek constants ────────────────────────────────────────────────────────
DEEPSEEK_BASE_URL  = "https://api.deepseek.com"
DEEPSEEK_MODEL     = "deepseek-chat"
DEEPSEEK_API_KEY_ENV = "DEEPSEEK_API_KEY"

# ── Zhipu GLM constants ───────────────────────────────────────────────────────
ZHIPU_BASE_URL     = "https://open.bigmodel.cn/api/paas/v4"
ZHIPU_MODEL        = "glm-4-7-flash"
ZHIPU_API_KEY_ENV  = "ZHIPU_API_KEY"


def query_deepseek_json(
    prompt: str,
    system_prompt: str = None,
    temperature: float = 0.0,
    max_tokens: int = 512,
    max_retries: int = 3,
) -> dict | None:
    """
    Call DeepSeek chat API and return parsed JSON response.

    Used for Step 3A1 (experience selection) where the local Qwen 3.5 4B
    model hallucinates. DeepSeek is OpenAI-compatible.

    Args:
        prompt:        User message / task description.
        system_prompt: Override the default system prompt. If None, uses
                       the same SYSTEM_PROMPT as ollama_client.py.
        temperature:   Sampling temperature (0.0 = deterministic).
        max_tokens:    Maximum tokens in the generated response.
        max_retries:   Number of retry attempts with exponential backoff.

    Returns:
        Parsed dict on success, None on failure.
    """
    api_key = os.environ.get(DEEPSEEK_API_KEY_ENV)
    if not api_key:
        print(f"  [DeepSeek] ❌ Environment variable '{DEEPSEEK_API_KEY_ENV}' is not set. "
              f"Get your key at https://platform.deepseek.com and set it before running.")
        return None

    client = OpenAI(api_key=api_key, base_url=DEEPSEEK_BASE_URL)
    sys_msg = system_prompt if system_prompt is not None else SYSTEM_PROMPT

    for attempt in range(max_retries):
        try:
            print(f"  [DeepSeek] Sending request (attempt {attempt + 1}/{max_retries})...")
            start_time = time.time()

            response = client.chat.completions.create(
                model=DEEPSEEK_MODEL,
                messages=[
                    {"role": "system", "content": sys_msg},
                    {"role": "user",   "content": prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
            )

            elapsed = time.time() - start_time
            content = response.choices[0].message.content
            usage   = response.usage
            print(
                f"  [DeepSeek] ⏱️  {elapsed:.1f}s | "
                f"prompt: {usage.prompt_tokens} tok | "
                f"generated: {usage.completion_tokens} tok"
            )

            return json.loads(content)

        except Exception as e:
            print(f"  [DeepSeek] ⚠️  Error (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)

    print(f"  [DeepSeek] ❌ All {max_retries} attempts failed.")
    return None


def query_glm_flash_json(
    prompt: str,
    system_prompt: str = None,
    temperature: float = 0.0,
    max_tokens: int = 512,
    max_retries: int = 3,
) -> dict | None:
    """
    Call Zhipu GLM-4-7-Flash API and return parsed JSON response.

    Placeholder — NOT wired into any pipeline step yet.
    Will be used once a Zhipu API key is available.

    Args:
        prompt:        User message / task description.
        system_prompt: Override the default system prompt. If None, uses
                       the same SYSTEM_PROMPT as ollama_client.py.
        temperature:   Sampling temperature (0.0 = deterministic).
        max_tokens:    Maximum tokens in the generated response.
        max_retries:   Number of retry attempts with exponential backoff.

    Returns:
        Parsed dict on success, None on failure.
    """
    api_key = os.environ.get(ZHIPU_API_KEY_ENV)
    if not api_key:
        print(f"  [GLM-Flash] ❌ Environment variable '{ZHIPU_API_KEY_ENV}' is not set. "
              f"Get your key at https://open.bigmodel.cn and set it before running.")
        return None

    client = OpenAI(api_key=api_key, base_url=ZHIPU_BASE_URL)
    sys_msg = system_prompt if system_prompt is not None else SYSTEM_PROMPT

    for attempt in range(max_retries):
        try:
            print(f"  [GLM-Flash] Sending request (attempt {attempt + 1}/{max_retries})...")
            start_time = time.time()

            response = client.chat.completions.create(
                model=ZHIPU_MODEL,
                messages=[
                    {"role": "system", "content": sys_msg},
                    {"role": "user",   "content": prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
            )

            elapsed = time.time() - start_time
            content = response.choices[0].message.content
            usage   = response.usage
            print(
                f"  [GLM-Flash] ⏱️  {elapsed:.1f}s | "
                f"prompt: {usage.prompt_tokens} tok | "
                f"generated: {usage.completion_tokens} tok"
            )

            return json.loads(content)

        except Exception as e:
            print(f"  [GLM-Flash] ⚠️  Error (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)

    print(f"  [GLM-Flash] ❌ All {max_retries} attempts failed.")
    return None
