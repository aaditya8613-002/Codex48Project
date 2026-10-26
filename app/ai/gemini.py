"""Thin wrapper around the Google AI Studio (Gemini) API.

Only passages we retrieved are ever sent. Callers must handle AIUnavailable so
the exact rules still work when the key is missing, rate-limited or offline.
"""
import json
import re

from ..config import settings


class AIUnavailable(RuntimeError):
    """Raised when Gemini cannot be used (no key, quota, network, bad output)."""


_client = None


def _get_client():
    global _client
    if _client is None:
        if not settings.gemini_api_key:
            raise AIUnavailable("GEMINI_API_KEY is not set")
        from google import genai

        _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


def is_configured() -> bool:
    return bool(settings.gemini_api_key)


def embed_texts(texts: list[str], query: bool = False) -> list[list[float]]:
    """Embed texts in batches of 100. query=True uses the retrieval-query task type."""
    if not texts:
        return []
    from google.genai import types

    client = _get_client()
    task = "RETRIEVAL_QUERY" if query else "RETRIEVAL_DOCUMENT"
    out: list[list[float]] = []
    try:
        for i in range(0, len(texts), 100):
            batch = texts[i : i + 100]
            resp = client.models.embed_content(
                model=settings.gemini_embed_model,
                contents=batch,
                config=types.EmbedContentConfig(task_type=task),
            )
            out.extend([list(e.values) for e in resp.embeddings])
    except AIUnavailable:
        raise
    except Exception as exc:  # quota, network, API errors
        raise AIUnavailable(f"embedding failed: {exc}") from exc
    return out


def generate_json(system: str, prompt: str) -> dict:
    """Ask Gemini for a JSON object. Temperature 0 for repeatable findings."""
    from google.genai import types

    client = _get_client()
    try:
        resp = client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system,
                temperature=0,
                response_mime_type="application/json",
            ),
        )
        raw = resp.text or ""
    except AIUnavailable:
        raise
    except Exception as exc:
        raise AIUnavailable(f"generation failed: {exc}") from exc
    return parse_json(raw)


def parse_json(raw: str) -> dict:
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?|```$", "", raw, flags=re.MULTILINE).strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AIUnavailable(f"model returned invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise AIUnavailable("model returned JSON that is not an object")
    return data
