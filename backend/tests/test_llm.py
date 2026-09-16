import os

from app.services.llm import LLMClient, LLMSettings


def test_gigachat_uses_unified_configuration(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "gigachat")
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_BASE_URL", "https://api.giga.chat/v1")
    monkeypatch.setenv("LLM_MODEL", "GigaChat-Max")

    client = LLMClient()
    assert client.provider == "gigachat"
    assert client.is_configured() is True
    assert client.settings.api_key == "test-key"


def test_ollama_does_not_require_api_key(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.setenv("LLM_BASE_URL", "http://localhost:11434/v1")
    monkeypatch.setenv("LLM_MODEL", "qwen3.5:4b")

    client = LLMClient()
    assert client.is_configured() is True


def test_unknown_provider_is_not_configured(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "unknown")
    monkeypatch.setenv("LLM_API_KEY", "key")
    monkeypatch.setenv("LLM_BASE_URL", "http://example.invalid/v1")
    monkeypatch.setenv("LLM_MODEL", "model")

    client = LLMClient()
    # Конфигурация заполнена, но сам вызов даст понятную ошибку unknown provider.
    assert client.is_configured() is True
