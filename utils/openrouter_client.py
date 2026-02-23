"""
UTIL: OpenRouter Client
PURPOSE: Wrapper for OpenRouter API with JSON mode, structured output, retry logic,
         and model switching. All LLM calls route through here.
DEPENDENCIES: requests
"""

import json
import time
import requests
from utils.config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL
from utils.logger import log_info, log_error, log_debug

MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds


def chat_completion(
    prompt: str,
    system_message: str,
    model: str,
    temperature: float = 0.7,
    max_tokens: int = 2000,
    json_mode: bool = True,
) -> dict | str:
    """
    Send a chat completion request to OpenRouter.

    Args:
        prompt: User message / input data
        system_message: System prompt
        model: Model identifier (e.g. "anthropic/claude-sonnet-4.5")
        temperature: Creativity vs consistency
        max_tokens: Response length limit
        json_mode: If True, parse response as JSON

    Returns:
        Parsed JSON dict if json_mode=True, else raw text string.
    """
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://aiflowdaily.com",
        "X-Title": "AI Flow Daily",
    }

    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    if json_mode:
        body["response_format"] = {"type": "json_object"}

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            log_debug(f"OpenRouter call → {model} (attempt {attempt})")
            resp = requests.post(
                OPENROUTER_BASE_URL,
                headers=headers,
                json=body,
                timeout=120,
            )
            resp.raise_for_status()

            data = resp.json()
            content = data["choices"][0]["message"]["content"]

            if json_mode:
                # Strip markdown code fences if present
                cleaned = content.strip()
                if cleaned.startswith("```"):
                    # Remove opening fence (```json or ```)
                    first_newline = cleaned.index("\n")
                    cleaned = cleaned[first_newline + 1 :]
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3]
                return json.loads(cleaned.strip())

            return content

        except requests.exceptions.HTTPError as e:
            log_error(f"OpenRouter HTTP error (attempt {attempt}): {e}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY * attempt)
            else:
                raise
        except json.JSONDecodeError as e:
            log_error(f"JSON parse error from {model}: {e}\nRaw: {content[:500]}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
            else:
                raise
        except Exception as e:
            log_error(f"OpenRouter error (attempt {attempt}): {e}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY * attempt)
            else:
                raise
