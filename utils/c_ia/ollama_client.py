import requests
import json
import time

OLLAMA_API_URL = "http://localhost:11434/api/generate"

# Change this to match your hardware:
# - "qwen2.5:72b" for self-hosted runner / local machine with 48GB+ RAM
# - "qwen2.5:32b" for 24GB+ RAM
# - "qwen2.5:14b" for GitHub-hosted runners (~14GB RAM)
MODEL_NAME = "qwen2.5:32b"


def query_ollama(prompt: str, temperature: float = 0.3, max_retries: int = 3) -> str:
    """
    Send a prompt to Ollama and return the full response text.
    Uses the generate API with streaming disabled for simplicity.
    Low temperature for consistent, structured JSON output.
    """
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_ctx": 65536,       # Large context window for big JSON inputs
            "num_predict": 16384,   # Allow long outputs (cover letters are verbose)
        },
        "format": "json"           # Force JSON output mode
    }

    for attempt in range(max_retries):
        try:
            print(f"  [Ollama] Sending request (attempt {attempt + 1}/{max_retries})...")
            response = requests.post(
                OLLAMA_API_URL,
                json=payload,
                timeout=1800  # 30 min timeout per request (large model can be slow)
            )
            response.raise_for_status()

            result = response.json()
            return result.get("response", "")

        except requests.exceptions.Timeout:
            print(f"  [Ollama] Request timed out (attempt {attempt + 1})")
            if attempt == max_retries - 1:
                raise
            time.sleep(10)

        except requests.exceptions.ConnectionError:
            print(f"  [Ollama] Connection error — is 'ollama serve' running?")
            if attempt == max_retries - 1:
                raise
            time.sleep(15)

        except Exception as e:
            print(f"  [Ollama] Error: {e}")
            if attempt == max_retries - 1:
                raise
            time.sleep(10)

    return ""


def query_ollama_text(prompt: str, temperature: float = 0.5) -> str:
    """
    Same as query_ollama but WITHOUT JSON format constraint.
    Used for cover letter generation where we want free-form French text.
    """
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_ctx": 32768,
            "num_predict": 4096,
        }
    }

    try:
        response = requests.post(
            OLLAMA_API_URL,
            json=payload,
            timeout=1800
        )
        response.raise_for_status()
        result = response.json()
        return result.get("response", "")
    except Exception as e:
        print(f"  [Ollama] Text generation error: {e}")
        return ""