import asyncio
import json
import logging
from typing import Any, Optional
from urllib import error, request


logger = logging.getLogger(__name__)

DEFAULT_GEMINI_URL_TEMPLATE = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def _extract_text(response_data: dict[str, Any]) -> str:
    candidates = response_data.get("candidates")
    if not isinstance(candidates, list):
        return ""

    parts: list[str] = []
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        content = candidate.get("content")
        if not isinstance(content, dict):
            continue
        content_parts = content.get("parts")
        if not isinstance(content_parts, list):
            continue
        for part in content_parts:
            if isinstance(part, dict) and isinstance(part.get("text"), str):
                parts.append(part["text"])

    return "\n".join(parts).strip()


def _post_generate(
    *,
    prompt: str,
    model: str,
    api_key: str,
    timeout: float,
    temperature: Optional[float] = None,
    max_output_tokens: Optional[int] = None,
    response_mime_type: Optional[str] = None,
) -> dict[str, Any] | None:
    if not api_key:
        logger.warning("Gemini API key is empty")
        return None

    payload: dict[str, Any] = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}],
            }
        ]
    }

    generation_config: dict[str, Any] = {}
    if temperature is not None:
        generation_config["temperature"] = temperature
    if max_output_tokens is not None:
        generation_config["maxOutputTokens"] = max_output_tokens
    if response_mime_type:
        generation_config["responseMimeType"] = response_mime_type
    if generation_config:
        payload["generationConfig"] = generation_config

    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        DEFAULT_GEMINI_URL_TEMPLATE.format(model=model),
        data=body,
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        },
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        logger.warning("Gemini HTTP error %s: %s", exc.code, details)
        return None
    except error.URLError as exc:
        logger.warning("Gemini connection error: %s", exc)
        return None
    except TimeoutError:
        logger.warning("Gemini request timed out after %s seconds", timeout)
        return None

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Gemini returned invalid JSON: %s", raw[:500])
        return None

    return {
        "response": _extract_text(data),
        "raw": data,
    }


async def ask(
    *,
    prompt: str,
    model: str,
    api_key: str,
    timeout: float = 30.0,
    temperature: Optional[float] = None,
    max_output_tokens: Optional[int] = None,
    response_mime_type: Optional[str] = None,
) -> dict[str, Any] | None:
    return await asyncio.to_thread(
        _post_generate,
        prompt=prompt,
        model=model,
        api_key=api_key,
        timeout=timeout,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        response_mime_type=response_mime_type,
    )
