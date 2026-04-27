from typing import Any, Optional

from config import settings
from app.services.ai_scoring.gemini_client import ask as gemini_ask
from app.services.ai_scoring.ollama_client import ask as ollama_ask


async def ask(
    *,
    prompt: str,
    timeout: float = 30.0,
    options: Optional[dict[str, Any]] = None,
    response_format: Optional[str] = None,
) -> dict[str, Any] | None:
    if settings.USE_LOCAL_LLM:
        return await ollama_ask(
            model=settings.OLLAMA_MODEL,
            prompt=prompt,
            timeout=timeout,
            url=settings.OLLAMA_URL,
            options=options,
            response_format=response_format,
        )

    temperature = None
    max_output_tokens = None
    if options:
        temperature = options.get("temperature")
        max_output_tokens = options.get("num_predict")

    return await gemini_ask(
        model=settings.GEMINI_MODEL,
        api_key=settings.GEMINI_API_KEY,
        prompt=prompt,
        timeout=timeout,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        response_mime_type="application/json" if response_format == "json" else None,
    )
