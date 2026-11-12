"""Создание чат-модели для LLM-режима (Ollama).

Импорт ``langchain_ollama`` ленивый: в mock-режиме пакет не нужен вообще,
поэтому проект запускается на чистом Python без установки зависимостей.
"""

from __future__ import annotations

from app.config import Settings


class LLMNotAvailableError(RuntimeError):
    """Понятная ошибка, если LLM-режим выбран, но окружение не готово."""


def build_chat_model(settings: Settings):
    """Вернуть ChatOllama с температурой 0 (детерминированный выбор инструмента)."""
    if settings.llm_provider != "ollama":
        raise LLMNotAvailableError(
            f"LLM-режим недоступен для провайдера {settings.llm_provider!r}"
        )

    try:
        from langchain_ollama import ChatOllama
    except ImportError as exc:  # pragma: no cover - зависит от окружения
        raise LLMNotAvailableError(
            "Для LLM_PROVIDER=ollama нужны зависимости: "
            "`pip install -r requirements.txt` (пакет langchain-ollama). "
            "Либо вернитесь в mock-режим: LLM_PROVIDER=mock."
        ) from exc

    return ChatOllama(
        model=settings.llm_model,
        base_url=settings.ollama_base_url,
        temperature=0,
    )


def check_ollama(settings: Settings) -> tuple[bool, str]:
    """Проверить доступность Ollama без внешних библиотек."""
    from urllib.error import URLError
    from urllib.request import urlopen

    url = settings.ollama_base_url.rstrip("/") + "/api/tags"
    try:
        with urlopen(url, timeout=3) as response:  # noqa: S310 - локальный адрес
            return response.status == 200, f"Ollama отвечает: {url}"
    except (URLError, OSError) as exc:
        return False, f"Ollama недоступна по адресу {url}: {exc}"
