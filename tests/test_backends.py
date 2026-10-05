from types import SimpleNamespace

import pytest
import requests

from firstpr_pilot import backends
from firstpr_pilot.backends import BackendError, GeminiBackend, OllamaBackend


class FakeModels:
    def __init__(self, behaviours):
        self.behaviours, self.calls = list(behaviours), []

    def generate_content(self, model, contents, config):
        self.calls.append({"model": model, "contents": contents, "config": config})
        item = self.behaviours.pop(0)
        if isinstance(item, Exception):
            raise item
        return SimpleNamespace(text=item)


def fake_client(*behaviours):
    return SimpleNamespace(models=FakeModels(behaviours))


def test_missing_api_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(BackendError, match="GEMINI_API_KEY"):
        GeminiBackend("gemma-4-26b-a4b-it")


def test_gemini_generate_with_image_and_system():
    client = fake_client("hello")
    out = GeminiBackend("gemma-4-26b-a4b-it", client=client).generate("hi", "be nice", b"img", "image/png")
    call = client.models.calls[0]
    assert out == "hello" and call["model"] == "gemma-4-26b-a4b-it"
    assert len(call["contents"]) == 2 and call["contents"][-1] == "hi"
    assert call["config"].system_instruction == "be nice"


def test_gemini_retries_with_inlined_instruction():
    client = fake_client(Exception("400 Developer instruction is not enabled for this model"), "ok")
    out = GeminiBackend("m", client=client).generate("question", "SYSTEM", None, None)
    assert out == "ok" and len(client.models.calls) == 2
    assert client.models.calls[1]["config"] is None
    assert client.models.calls[1]["contents"][-1] == "SYSTEM\n\nquestion"


@pytest.mark.parametrize(
    "error,expected",
    [
        ("429 RESOURCE_EXHAUSTED", "quota"),
        ("API key not valid", "API key"),
        ("404 model not found", "model was not found"),
        ("weird", "Gemini API error"),
    ],
)
def test_gemini_error_mapping(error, expected):
    with pytest.raises(BackendError, match=expected):
        GeminiBackend("m", client=fake_client(Exception(error))).generate("p", "s")


def test_gemini_empty_response():
    with pytest.raises(BackendError, match="empty"):
        GeminiBackend("m", client=fake_client("   ")).generate("p", "s")


class FakeResponse:
    def __init__(self, data, ok=True):
        self.data, self.ok = data, ok

    def raise_for_status(self):
        if not self.ok:
            raise requests.exceptions.HTTPError("404 Client Error")

    def json(self):
        return self.data


def test_ollama_generate_sends_chat_payload(monkeypatch):
    seen = {}

    def fake_post(url, json, timeout):
        seen.update(url=url, json=json)
        return FakeResponse({"message": {"content": "local answer"}})

    monkeypatch.setattr(backends.requests, "post", fake_post)
    out = OllamaBackend("gemma4:e4b", url="http://x:1/").generate("p", "sys", b"abc", "image/png")
    assert out == "local answer" and seen["url"] == "http://x:1/api/chat"
    assert seen["json"]["messages"][0] == {"role": "system", "content": "sys"}
    assert seen["json"]["messages"][1]["images"] and seen["json"]["stream"] is False


def test_ollama_connection_error(monkeypatch):
    def fake_post(*a, **k):
        raise requests.exceptions.ConnectionError("refused")

    monkeypatch.setattr(backends.requests, "post", fake_post)
    with pytest.raises(BackendError, match="ollama serve"):
        OllamaBackend("m").generate("p", "s")


def test_ollama_http_error_hints_pull(monkeypatch):
    monkeypatch.setattr(backends.requests, "post", lambda *a, **k: FakeResponse({}, ok=False))
    with pytest.raises(BackendError, match="ollama pull"):
        OllamaBackend("m").generate("p", "s")
