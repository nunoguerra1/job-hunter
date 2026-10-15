import os
import time
from typing import Protocol, TypeVar

from google import genai
from google.genai import errors, types
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

RETRYABLE = {429, 500, 503, 504}
MAX_RETRIES = 2


class QuotaExhaustedError(RuntimeError):
    """Cota diária gratuita esgotada em todos os modelos configurados."""


class LLM(Protocol):
    def generate_json(self, prompt: str, schema: type[T]) -> T: ...


def _is_daily_quota(error: errors.APIError) -> bool:
    return error.code == 429 and "PerDay" in str(error)


class GeminiClient:
    def __init__(self, api_key: str | None = None, models: list[str] | None = None):
        self.client = genai.Client(api_key=api_key or os.environ["GEMINI_API_KEY"])
        if models is None:
            raw = os.environ.get("GEMINI_MODELS") or os.environ.get("GEMINI_MODEL")
            models = [m.strip() for m in (raw or "gemini-3.5-flash").split(",") if m.strip()]
        self.models = models
        self.exhausted: set[str] = set()

    def generate_json(self, prompt: str, schema: type[T]) -> T:
        for model in self.models:
            if model in self.exhausted:
                continue
            try:
                return self._call(model, prompt, schema)
            except errors.APIError as error:
                if _is_daily_quota(error):
                    print(f"  (cota diária esgotada em {model})")
                    self.exhausted.add(model)
                    continue
                raise
        raise QuotaExhaustedError("cota diária esgotada em todos os modelos")

    def _call(self, model: str, prompt: str, schema: type[T]) -> T:
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=schema,
            temperature=0.2,
        )
        for attempt in range(MAX_RETRIES + 1):
            try:
                response = self.client.models.generate_content(
                    model=model, contents=prompt, config=config
                )
                return schema.model_validate_json(response.text)
            except errors.APIError as error:
                if _is_daily_quota(error):
                    raise
                if error.code in RETRYABLE and attempt < MAX_RETRIES:
                    wait = 20 * (attempt + 1)
                    print(f"  (Gemini {error.code}; tentando de novo em {wait}s)")
                    time.sleep(wait)
                    continue
                raise
        raise RuntimeError("inalcançável")