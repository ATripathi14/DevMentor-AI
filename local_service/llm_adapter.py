import requests

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "llama3.2:3b"

SYSTEM_PROMPT = (
    "You are a concise debugging assistant. Plain English, no markdown. "
    "Maximum 3 sentences: the likely cause, then one concrete fix."
)


def explain_with_llm(category: str, error_type: str, message: str,
                     timeout: float = 20.0) -> str | None:
    """Ask the local Ollama model to explain a sanitized error.
    Returns the explanation, or None if Ollama is unavailable or too slow."""
    user_prompt = (
        f"Python error category: {category}. "
        f"Exception: {error_type}. Sanitized message: {message}. "
        "Explain the cause and one concrete fix."
    )
    try:
        r = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL,
                "stream": False,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                "options": {"num_predict": 160},
            },
            timeout=timeout,
        )
        r.raise_for_status()
        return r.json()["message"]["content"].strip()
    except (requests.exceptions.RequestException, KeyError, ValueError):
        return None