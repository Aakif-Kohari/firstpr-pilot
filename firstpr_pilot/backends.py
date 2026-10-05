"""AI backends: Gemini API (Gemma 4 and Gemini models) and local Ollama."""

from __future__ import annotations

import base64
import os

import requests
from google import genai
from google.genai import types

DEFAULT_GEMMA_MODEL = "gemma-4-26b-a4b-it"
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
DEFAULT_OLLAMA_MODEL = "gemma4:e4b"
DEFAULT_OLLAMA_URL = "http://localhost:11434"


class BackendError(Exception):
    """A user-presentable error from an AI backend."""


class Backend:
    """Interface every backend implements."""

    def generate(
        self,
        prompt: str,
        system_instruction: str,
        image_bytes: bytes | None = None,
        image_mime: str | None = None,
    ) -> str:
        raise NotImplementedError


def _describe_gemini_error(exc: Exception) -> str:
    msg = str(exc)
    low = msg.lower()
    if "429" in msg or "quota" in low or "resource_exhausted" in low:
        return "Gemini API quota or rate limit reached. Wait a minute and try again."
    if "api key" in low or "api_key_invalid" in low or "permission_denied" in low:
        return "The Gemini API key was rejected. Check GEMINI_API_KEY."
    if "not found" in low or "404" in msg:
        return "The model was not found. Check the model name in your settings."
    return f"Gemini API error: {msg}"


def _is_system_instruction_unsupported(exc: Exception) -> bool:
    low = str(exc).lower()
    return ("system instruction" in low or "developer instruction" in low) and (
        "not enabled" in low or "not supported" in low or "unsupported" in low
    )


class GeminiBackend(Backend):
    """Calls models through the Gemini API (works for gemma-4-* and gemini-* model IDs)."""

    def __init__(self, model: str, api_key: str | None = None, client=None):
        self.model = model
        if client is None:
            key = api_key or os.getenv("GEMINI_API_KEY")
            if not key:
                raise BackendError(
                    "GEMINI_API_KEY is not set. Create a free key in Google AI Studio."
                )
            client = genai.Client(api_key=key)
        self.client = client

    def _call(self, contents: list, system_instruction: str | None) -> str:
        config = (
            types.GenerateContentConfig(system_instruction=system_instruction)
            if system_instruction
            else None
        )
        response = self.client.models.generate_content(
            model=self.model, contents=contents, config=config
        )
        return response.text or ""

    def generate(
        self,
        prompt: str,
        system_instruction: str,
        image_bytes: bytes | None = None,
        image_mime: str | None = None,
    ) -> str:
        contents: list = []
        if image_bytes and image_mime:
            contents.append(types.Part.from_bytes(data=image_bytes, mime_type=image_mime))
        contents.append(prompt)
        try:
            try:
                text = self._call(contents, system_instruction)
            except Exception as exc:  # retry once with the instruction inlined
                if not _is_system_instruction_unsupported(exc):
                    raise
                contents[-1] = f"{system_instruction}\n\n{prompt}"
                text = self._call(contents, None)
        except Exception as exc:
            raise BackendError(_describe_gemini_error(exc)) from exc
        if not text.strip():
            raise BackendError("The model returned an empty response (it may have been filtered).")
        return text


class OllamaBackend(Backend):
    """Calls a local Ollama server, so an open-weight Gemma 4 can run fully offline."""

    def __init__(self, model: str | None = None, url: str | None = None, timeout: int = 300):
        self.model = model or os.getenv("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)
        self.url = (url or os.getenv("OLLAMA_URL", DEFAULT_OLLAMA_URL)).rstrip("/")
        self.timeout = timeout

    def generate(
        self,
        prompt: str,
        system_instruction: str,
        image_bytes: bytes | None = None,
        image_mime: str | None = None,
    ) -> str:
        user_message: dict = {"role": "user", "content": prompt}
        if image_bytes:
            user_message["images"] = [base64.b64encode(image_bytes).decode("ascii")]
        payload = {
            "model": self.model,
            "stream": False,
            "messages": [{"role": "system", "content": system_instruction}, user_message],
        }
        try:
            response = requests.post(f"{self.url}/api/chat", json=payload, timeout=self.timeout)
            response.raise_for_status()
        except requests.exceptions.ConnectionError as exc:
            raise BackendError(
                f"Could not connect to Ollama at {self.url}. Is it running (`ollama serve`)?"
            ) from exc
        except requests.exceptions.HTTPError as exc:
            raise BackendError(
                f"Ollama error: {exc}. Have you pulled the model (`ollama pull {self.model}`)?"
            ) from exc
        except requests.exceptions.RequestException as exc:
            raise BackendError(f"Ollama request failed: {exc}") from exc
        text = (response.json().get("message") or {}).get("content", "")
        if not text.strip():
            raise BackendError("Ollama returned an empty response.")
        return text
