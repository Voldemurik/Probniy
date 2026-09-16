from types import SimpleNamespace
import pytest
from app.services import llm as llm_module
from app.services.llm import LLMClient, LLMSettings


@pytest.fixture(autouse=True)
def _clear_model_cache():
    llm_module._MODEL_CACHE.clear()
    yield
    llm_module._MODEL_CACHE.clear()


class _FakeGiga:
    def __init__(self, models, ok_model):
        self._models, self._ok = models, ok_model
        self.calls = []

    def get_models(self):
        return SimpleNamespace(data=[SimpleNamespace(id_=m) for m in self._models])

    def chat(self, payload):
        self.calls.append(payload)
        if payload.get("model", "GigaChat-Max") != self._ok:
            raise RuntimeError('404 https://api.giga.chat/v1/chat/completions: {"status":404,"message":"No such model"}')
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="ок"))])


def _client(fake):
    c = LLMClient(LLMSettings("gigachat", "k" * 100, "https://api.giga.chat/v1", "GigaChat-Max", 30, False))
    c._gigachat = fake
    return c


def test_falls_back_to_available_model():
    fake = _FakeGiga(["Embeddings", "GigaChat-2-Lite", "GigaChat-2"], ok_model="GigaChat-2")
    c = _client(fake)
    assert c.chat_text([{"role": "user", "content": "привет"}]) == "ок"
    assert c.model_in_use == "GigaChat-2"
    assert fake.calls[-1]["model"] == "GigaChat-2"
    # второй вызов сразу идёт с подобранной моделью
    c.chat_text([{"role": "user", "content": "ещё"}])
    assert len(fake.calls) == 3 and fake.calls[-1]["model"] == "GigaChat-2"


def test_keeps_configured_model_when_available():
    fake = _FakeGiga(["GigaChat-Max", "GigaChat"], ok_model="GigaChat-Max")
    c = _client(fake)
    assert c.chat_text([{"role": "user", "content": "x"}]) == "ок"
    assert "model" not in fake.calls[0]
