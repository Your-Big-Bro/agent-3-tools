"""Включение трейсинга LangSmith через переменные окружения.

Переменные выставляются до импорта LangChain, иначе SDK не подхватит настройки.
Поддерживаются оба набора имён: новые ``LANGSMITH_*`` и старые ``LANGCHAIN_*``.
"""

from __future__ import annotations

import os

from app.config import Settings


def enable_tracing(settings: Settings) -> bool:
    """Включить трейсинг, если задан ключ. Возвращает признак включения."""
    if not settings.langsmith_tracing or not settings.langsmith_api_key:
        return False

    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
    os.environ["LANGCHAIN_API_KEY"] = settings.langsmith_api_key
    os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project
    os.environ["LANGCHAIN_PROJECT"] = settings.langsmith_project

    if settings.langsmith_endpoint:
        os.environ["LANGSMITH_ENDPOINT"] = settings.langsmith_endpoint
        os.environ["LANGCHAIN_ENDPOINT"] = settings.langsmith_endpoint

    return True


def tracing_status(settings: Settings) -> str:
    """Человекочитаемый статус для вывода при старте."""
    if not settings.langsmith_tracing:
        return "выключен (LANGSMITH_TRACING=false)"
    if not settings.langsmith_api_key:
        return "включён, но нет LANGSMITH_API_KEY - трейсы не уйдут"
    return f"включён, проект: {settings.langsmith_project}"
