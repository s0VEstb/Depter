import asyncio
import json
import logging
from typing import Any, Optional
from urllib import error, request


logger = logging.getLogger(__name__)

DEFAULT_OLLAMA_URL = "http://192.168.23.6:11434/api/generate"
DEFAULT_OLLAMA_MODEL = "gemma4:e4b"


def _post_generate(
    *,
    model: str,
    prompt: str,
    timeout: float,
    url: str,
    options: Optional[dict[str, Any]] = None,
) -> dict[str, Any] | None:
    payload: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "stream": False,
    }
    if options:
        payload["options"] = options

    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        logger.warning("Ollama HTTP error %s: %s", exc.code, details)
        return None
    except error.URLError as exc:
        logger.warning("Ollama connection error: %s", exc)
        return None
    except TimeoutError:
        logger.warning("Ollama request timed out after %s seconds", timeout)
        return None

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Ollama returned invalid JSON: %s", raw[:500])
        return None


async def ask(
    *,
    prompt: str,
    model: str = DEFAULT_OLLAMA_MODEL,
    timeout: float = 30.0,
    url: str = DEFAULT_OLLAMA_URL,
    options: Optional[dict[str, Any]] = None,
) -> dict[str, Any] | None:
    return await asyncio.to_thread(
        _post_generate,
        model=model,
        prompt=prompt,
        timeout=timeout,
        url=url,
        options=options,
    )
