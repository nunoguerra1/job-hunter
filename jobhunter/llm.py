import os
import time
from typing import Protocol, TypeVar

from google import genai
from google.genai import errors, types
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)
RETRYABLE = {429, 500, 503, 504}


class LLM(Protocol):
    def generate_json(self, prompt: str, schema: type[T]) -> T: ...


class GeminiClient:
    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.client = genai.Client(api_key=api_key or os.environ["GEMINI_API_KEY"])
        self.model = model or os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")

    def generate_json(self, prompt: str, schema: type[T]) -> T:
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=schema,
            temperature=0.2,
        )
        for attempt in range(4):
            try:
                response = self.client.models.generate_content(
                    model=self.model, contents=prompt, config=config
                )
                return schema.model_validate_json(response.text)
            except errors.APIError as error:
                if error.code in RETRYABLE and attempt < 3:
                    wait = 15 * (attempt + 1)
                    print(f"  (Gemini {error.code}; tentando de novo em {wait}s)")
                    time.sleep(wait)
                    continue
                raise
        raise RuntimeError("inalcançável")