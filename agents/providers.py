import json
from abc import ABC, abstractmethod

import httpx

from backend.app.config import Settings


class LLMProvider(ABC):
    name: str

    @abstractmethod
    def generate_json(self, system: str, prompt: str, schema: dict) -> dict:
        """Generate a JSON value conforming to schema."""


class GeminiProvider(LLMProvider):
    name = "gemini"

    def __init__(self, settings: Settings):
        from google import genai
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model = settings.gemini_model

    def generate_json(self, system: str, prompt: str, schema: dict) -> dict:
        response = self.client.models.generate_content(
            model=self.model, contents=prompt,
            config={"system_instruction": system, "response_mime_type": "application/json", "response_schema": schema},
        )
        return response.parsed


class OllamaProvider(LLMProvider):
    name = "ollama"

    def __init__(self, settings: Settings):
        self.base_url, self.model = settings.ollama_base_url, settings.ollama_model

    def generate_json(self, system: str, prompt: str, schema: dict) -> dict:
        response = httpx.post(f"{self.base_url}/api/chat", json={
            "model": self.model, "stream": False, "format": schema,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        }, timeout=60)
        response.raise_for_status()
        return json.loads(response.json()["message"]["content"])


class FallbackProvider(LLMProvider):
    name = "gemini-with-ollama-fallback"

    def __init__(self, primary: LLMProvider, fallback: LLMProvider):
        self.primary, self.fallback = primary, fallback

    def generate_json(self, system: str, prompt: str, schema: dict) -> dict:
        try:
            return self.primary.generate_json(system, prompt, schema)
        except Exception:
            return self.fallback.generate_json(system, prompt, schema)


def build_provider(settings: Settings) -> LLMProvider | None:
    """Gemini is primary when configured; Ollama is the local provider; rules are the safe fallback."""
    if settings.llm_provider == "gemini" and settings.gemini_api_key:
        return FallbackProvider(GeminiProvider(settings), OllamaProvider(settings))
    if settings.llm_provider == "ollama":
        return OllamaProvider(settings)
    return None
