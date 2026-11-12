"""Реестр инструментов агента.

Каждый инструмент — обычная функция плюс описание (в ``app.prompts``).
Такое разделение позволяет использовать одни и те же функции и в mock-режиме
(прямой вызов), и в LLM-режиме (обёртка в LangChain Tool).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from app.prompts import tool_descriptions
from app.tools.calculator import calculator
from app.tools.lookup import lookup
from app.tools.now import now


@dataclass(frozen=True)
class ToolSpec:
    """Описание инструмента: имя и вызываемая функция."""

    name: str
    func: Callable[..., str]

    def __call__(self, argument: str = "") -> str:
        return self.func(argument)


TOOLS: tuple[ToolSpec, ...] = (
    ToolSpec("calculator", calculator),
    ToolSpec("now", now),
    ToolSpec("lookup", lookup),
)

TOOLS_BY_NAME: dict[str, ToolSpec] = {tool.name: tool for tool in TOOLS}

TOOL_NAMES: tuple[str, ...] = tuple(tool.name for tool in TOOLS)


def get_tool(name: str) -> ToolSpec:
    """Вернуть инструмент по имени или возбудить понятную ошибку."""
    try:
        return TOOLS_BY_NAME[name]
    except KeyError as exc:
        raise KeyError(f"unknown tool: {name!r}, available: {', '.join(TOOL_NAMES)}") from exc


def run_tool(name: str, argument: str = "") -> str:
    """Вызвать инструмент по имени с одним строковым аргументом."""
    return get_tool(name)(argument)


def describe(name: str, lang: str = "ru") -> str:
    """Описание инструмента для промпта на выбранном языке."""
    return tool_descriptions(lang).get(name, "")


def describe_all(lang: str = "ru") -> dict[str, str]:
    return {name: describe(name, lang) for name in TOOL_NAMES}
