"""Единый адаптер LLM для ИИще.

Поддерживает:
- gigachat — официальный Python SDK GigaChat;
- openrouter — OpenAI-compatible HTTP API;
- ollama — OpenAI-compatible HTTP API.

Бизнес-логика проекта не должна напрямую импортировать конкретного провайдера.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

import httpx


@dataclass(frozen=True)
class LLMSettings:
    provider: str
    api_key: str
    base_url: str
    model: str
    timeout: float
    verify_ssl: bool


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def get_settings() -> LLMSettings:
    provider = os.getenv("LLM_PROVIDER", "ollama").strip().lower()

    defaults = {
        "gigachat": "https://api.giga.chat/v1",
        "openrouter": "https://openrouter.ai/api/v1",
        "ollama": "http://localhost:11434/v1",
    }
    models = {
        "gigachat": "GigaChat-Max",
        "openrouter": "qwen/qwen3.5-flash",
        "ollama": "qwen3.5:4b",
    }

    # 06.09: на Vercel/облачном хостинге нет корневых сертификатов Минцифры, поэтому там
    # проверка SSL по умолчанию выключена (LLM_VERIFY_SSL=1 включает обратно);
    # случайные кавычки/пробелы вокруг ключа из `vercel env add` отбрасываем.
    on_cloud = bool(os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"))
    return LLMSettings(
        provider=provider,
        api_key=os.getenv("LLM_API_KEY", "").strip().strip("\"'"),
        base_url=os.getenv("LLM_BASE_URL", defaults.get(provider, "")).rstrip("/"),
        model=os.getenv("LLM_MODEL", models.get(provider, "")).strip(),
        timeout=float(os.getenv("LLM_TIMEOUT_S", "60")),
        verify_ssl=_env_bool("LLM_VERIFY_SSL", not on_cloud),
    )


class LLMError(RuntimeError):
    """Ошибка подключения/вызова LLM."""


# Порядок предпочтения, если заданной в LLM_MODEL модели нет на тарифе (06.09)
_MODEL_PREFERENCE = (
    "GigaChat-2-Max", "GigaChat-Max", "GigaChat-2-Pro", "GigaChat-Pro",
    "GigaChat-2", "GigaChat", "GigaChat-2-Lite", "GigaChat-Lite",
)


_MODEL_CACHE: Dict[tuple, str] = {}   # (provider, model из настроек) → подобранная модель; живёт, пока жив процесс


class LLMClient:
    def __init__(self, settings: Optional[LLMSettings] = None) -> None:
        self.settings = settings or get_settings()
        self._gigachat = None
        # модель, подобранная по списку доступных (кэш на процесс, чтобы не спрашивать список каждый раз)
        self._cache_key = (self.settings.provider, self.settings.model, self.settings.api_key[-6:])
        self._resolved_model: Optional[str] = _MODEL_CACHE.get(self._cache_key)

    @property
    def model_in_use(self) -> str:
        return self._resolved_model or self.settings.model

    def available_models(self) -> list[str]:
        """Список моделей, доступных ключу (только GigaChat)."""
        client = self._get_gigachat()
        try:
            models = client.get_models()
        except Exception as exc:
            raise LLMError(f"Не удалось получить список моделей GigaChat: {exc}") from exc
        return [getattr(m, "id_", None) or getattr(m, "id", "") for m in models.data]

    def resolve_model(self) -> Optional[str]:
        """Выбирает рабочую модель: заданную, если она есть на тарифе, иначе лучшую из доступных."""
        chat_models = [m for m in self.available_models() if m and "embed" not in m.lower()]
        for candidate in (self.settings.model, *_MODEL_PREFERENCE):
            if candidate in chat_models:
                self._resolved_model = candidate
                break
        else:
            self._resolved_model = chat_models[0] if chat_models else None
        if self._resolved_model:
            _MODEL_CACHE[self._cache_key] = self._resolved_model
        return self._resolved_model

    @property
    def provider(self) -> str:
        return self.settings.provider

    def is_configured(self) -> bool:
        if self.settings.provider == "ollama":
            return bool(self.settings.base_url and self.settings.model)
        return bool(self.settings.api_key and self.settings.base_url and self.settings.model)

    def _get_gigachat(self):
        if self._gigachat is not None:
            return self._gigachat
        try:
            from gigachat import GigaChat
        except ImportError as exc:
            raise LLMError("Не установлен пакет gigachat") from exc

        if not self.settings.api_key:
            raise LLMError("LLM_API_KEY не настроен для GigaChat")

        try:
            self._gigachat = GigaChat(
                credentials=self.settings.api_key,
                model=self.settings.model,
                base_url=self.settings.base_url,
                timeout=self.settings.timeout,
                verify_ssl_certs=self.settings.verify_ssl,
            )
        except Exception as exc:
            raise LLMError(f"Ошибка инициализации GigaChat: {exc}") from exc
        return self._gigachat

    def _openai_chat(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        if not self.is_configured():
            raise LLMError(f"LLM не настроен для provider={self.provider}")

        url = f"{self.settings.base_url}/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self.settings.api_key:
            headers["Authorization"] = f"Bearer {self.settings.api_key}"

        payload: Dict[str, Any] = {
            "model": self.settings.model,
            "messages": messages,
            **kwargs,
        }

        try:
            with httpx.Client(timeout=self.settings.timeout, verify=self.settings.verify_ssl) as client:
                response = client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
        except Exception as exc:
            raise LLMError(f"Ошибка LLM HTTP: {exc}") from exc

        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError(f"Неожиданный ответ LLM: {data!r}") from exc
        if isinstance(content, list):
            content = "".join(
                part.get("text", "") if isinstance(part, dict) else str(part)
                for part in content
            )
        return str(content)

    def chat_text(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        """Обычный текстовый chat completion."""
        if self.provider == "gigachat":
            client = self._get_gigachat()
            payload: Dict[str, Any] = {"messages": messages, **kwargs}
            if self._resolved_model:
                payload["model"] = self._resolved_model
            try:
                response = client.chat(payload)
                return str(response.choices[0].message.content)
            except Exception as exc:
                # 06.09: на тарифе может не быть модели из LLM_MODEL — подбираем доступную и повторяем один раз
                if "No such model" in str(exc) and not self._resolved_model:
                    try:
                        chosen = self.resolve_model()
                    except LLMError as inner:
                        raise LLMError(f"Ошибка GigaChat: {exc}; {inner}") from exc
                    if chosen and chosen != self.settings.model:
                        print(f"ℹ️ Модель {self.settings.model!r} недоступна, используем {chosen!r}")
                        payload["model"] = chosen
                        try:
                            response = client.chat(payload)
                            return str(response.choices[0].message.content)
                        except Exception as exc2:
                            raise LLMError(f"Ошибка GigaChat ({chosen}): {exc2}") from exc2
                raise LLMError(f"Ошибка GigaChat: {exc}") from exc

        if self.provider in {"ollama", "openrouter"}:
            return self._openai_chat(messages, **kwargs)

        raise LLMError(f"Неизвестный LLM_PROVIDER: {self.provider}")

    def chat_json(self, messages: list[dict[str, str]]) -> str:
        """Запрашивает JSON. Для совместимости не требует JSON-schema от провайдера."""
        if self.provider == "gigachat":
            # 06.09: SDK GigaChat не принимает response_format — формат JSON задаётся промптом,
            # а ответ разбирается устойчиво (см. ai._extract_json)
            return self.chat_text(messages)

        return self.chat_text(
            messages,
            response_format={"type": "json_object"},
            temperature=0,
        )

    def embeddings(self, texts: list[str], model: str = "Embeddings") -> list[list[float]]:
        """Векторные представления строк (только GigaChat). Используется для
        объединения вариантов написания одного сервиса — см. services/naming.py."""
        if self.provider != "gigachat":
            raise LLMError(f"Эмбеддинги поддерживаются только для gigachat, сейчас provider={self.provider}")
        if not texts:
            return []
        client = self._get_gigachat()
        try:
            response = client.embeddings(texts=list(texts), model=model)
        except Exception as exc:
            raise LLMError(f"Ошибка эмбеддингов GigaChat: {exc}") from exc
        return [list(item.embedding) for item in response.data]

    def redact(self, text: str) -> str:
        """Убирает ключ из текста ошибки, если он туда попал."""
        key = self.settings.api_key
        return text.replace(key, "***") if key and key in text else text

    def health(self) -> Dict[str, Any]:
        """Возвращает безопасную диагностическую информацию без раскрытия ключа."""
        result = {
            "provider": self.provider,
            "model": self.settings.model,
            "configured": self.is_configured(),
            "base_url": self.settings.base_url,
            "verify_ssl": self.settings.verify_ssl,
            "api_key_len": len(self.settings.api_key),
            "model_in_use": self.model_in_use,
        }
        if not result["configured"]:
            return result

        if self.provider == "ollama":
            # Для Ollama OpenAI-compatible endpoint не требует ключа.
            return result
        return result


def get_llm_client() -> LLMClient:
    return LLMClient()
