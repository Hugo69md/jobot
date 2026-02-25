import requests
import json
import time
import sys
import threading

OLLAMA_API_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen2.5:14b"


def _waiting_indicator(start_time, stop_event):
    """Print a dot every 10 seconds while waiting for prompt processing."""
    while not stop_event.is_set():
        elapsed = time.time() - start_time
        sys.stdout.write(f"\r  [Ollama] ⏳ Processing prompt... {elapsed:.0f}s elapsed")
        sys.stdout.flush()
        stop_event.wait(10)


def query_ollama(prompt: str, temperature: float = 0.3, max_retries: int = 3) -> str:
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": True,
        "options": {
            "temperature": temperature,
            "num_ctx": 32768,
            "num_predict": 8192,
        },
        "format": "json"
    }

    for attempt in range(max_retries):
        try:
            print(f"  [Ollama] Sending request (attempt {attempt + 1}/{max_retries})...")
            start_time = time.time()
            first_token_time = None
            token_count = 0
            full_response = ""

            # Start a waiting indicator thread
            stop_event = threading.Event()
            waiter = threading.Thread(target=_waiting_indicator, args=(start_time, stop_event))
            waiter.daemon = True
            waiter.start()

            response = requests.post(
                OLLAMA_API_URL,
                json=payload,
                stream=True,
                timeout=3600
            )
            response.raise_for_status()

            for line in response.iter_lines():
                if not line:
                    continue

                chunk = json.loads(line)
                token = chunk.get("response", "")
                full_response += token

                if token and first_token_time is None:
                    # Stop the waiting indicator
                    stop_event.set()
                    first_token_time = time.time()
                    prompt_time = first_token_time - start_time
                    print(f"\n  [Ollama] ⏱️  Prompt processed in {prompt_time:.1f}s — now generating...")

                if token:
                    token_count += 1
                    elapsed = time.time() - start_time
                    if token_count % 50 == 0:
                        gen_elapsed = time.time() - first_token_time if first_token_time else 0
                        speed = token_count / gen_elapsed if gen_elapsed > 0 else 0
                        sys.stdout.write(
                            f"\r  [Ollama] 📝 {token_count} tokens generated "
                            f"({speed:.1f} tok/s) — {elapsed:.0f}s elapsed"
                        )
                        sys.stdout.flush()

                if chunk.get("done", False):
                    stop_event.set()  # Stop waiter just in case
                    elapsed = time.time() - start_time
                    print(f"\n  [Ollama] ✅ Done! {token_count} tokens in {elapsed:.1f}s")
                    prompt_eval_count = chunk.get("prompt_eval_count", 0)
                    eval_count = chunk.get("eval_count", 0)
                    total_duration = chunk.get("total_duration", 0) / 1e9
                    print(f"  [Ollama] 📊 Prompt: {prompt_eval_count} tok | "
                          f"Generated: {eval_count} tok | "
                          f"Total: {total_duration:.1f}s")
                    break

            return full_response

        except requests.exceptions.Timeout:
            print(f"\n  [Ollama] Timeout (attempt {attempt + 1})")
            if attempt == max_retries - 1:
                raise
            time.sleep(10)

        except requests.exceptions.ConnectionError:
            print(f"\n  [Ollama] Connection error — is 'ollama serve' running?")
            if attempt == max_retries - 1:
                raise
            time.sleep(15)

        except Exception as e:
            print(f"\n  [Ollama] Error: {e}")
            if attempt == max_retries - 1:
                raise
            time.sleep(10)

    return ""