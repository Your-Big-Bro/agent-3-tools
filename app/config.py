"""Загрузка настроек из окружения и файла ``.env``.

Специально не используется ``python-dotenv``: mock-режим должен запускаться
на голом Python, без ``pip install``. Парсер поддерживает комментарии,
пустые строки, ``export KEY=VALUE`` и значения в кавычках.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ENV_FILE = PROJECT_ROOT / ".env"

VALID_PROVIDERS = ("mock", "ollama")
VALID_LANGS = ("ru", "en")


def parse_dotenv(path: Path) -> dict[str, str]:
    """Разобрать простой ``.env``-файл в словарь."""
    values: dict[str, str] = {}
    if not path.is_file():
        return values

    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if key:
            values[key] = value
    return values


def _as_bool(value: str, default: bool = False) -> bool:
    if not value:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class Settings:
    """Все настройки приложения в одном месте."""

    llm_provider: str = "mock"
    llm_model: str = "qwen2.5:3b-instruct"
    ollama_base_url: str = "http://localhost:11434"
    prompt_lang: str = "ru"
    timezone: str = "Europe/Moscow"

    data_dir: Path = PROJECT_ROOT / "data"
    logs_dir: Path = PROJECT_ROOT / "logs"
    db_path: Path = PROJECT_ROOT / "data" / "agent_state.sqlite"
    kb_path: Path = PROJECT_ROOT / "data" / "kb.json"

    langsmith_tracing: bool = False
    langsmith_api_key: str = ""
    langsmith_project: str = "agent-3-tools"
    langsmith_endpoint: str = ""

    @property
    def tracing_ready(self) -> bool:
        return bool(self.langsmith_tracing and self.langsmith_api_key)


def get_settings(env_file: Path | None = None) -> Settings:
    """Собрать настройки: переменные окружения приоритетнее файла ``.env``."""
    file_values = parse_dotenv(env_file or DEFAULT_ENV_FILE)

    def get(name: str, default: str = "") -> str:
        return os.environ.get(name) or file_values.get(name, default)

    provider = get("LLM_PROVIDER", "mock").strip().lower()
    if provider not in VALID_PROVIDERS:
        provider = "mock"

    lang = get("PROMPT_LANG", "ru").strip().lower()
    if lang not in VALID_LANGS:
        lang = "ru"

    data_dir = PROJECT_ROOT / "data"
    logs_dir = PROJECT_ROOT / "logs"

    return Settings(
        llm_provider=provider,
        llm_model=get("LLM_MODEL", "qwen2.5:7b-instruct").strip(),
        ollama_base_url=get("OLLAMA_BASE_URL", "http://localhost:11434").strip(),
        prompt_lang=lang,
        timezone=get("APP_TIMEZONE", "Europe/Moscow").strip(),
        data_dir=data_dir,
        logs_dir=logs_dir,
        db_path=data_dir / "agent_state.sqlite",
        kb_path=data_dir / "kb.json",
        langsmith_tracing=_as_bool(get("LANGSMITH_TRACING", ""), default=False),
        langsmith_api_key=get("LANGSMITH_API_KEY", "").strip(),
        langsmith_project=get("LANGSMITH_PROJECT", "agent-3-tools").strip(),
        langsmith_endpoint=get("LANGSMITH_ENDPOINT", "").strip(),
    )
