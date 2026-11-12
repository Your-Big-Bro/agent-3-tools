"""Детерминированный роутер для mock-режима.

Заменяет LLM там, где модель недоступна: по ключевым словам и наличию
арифметического выражения выбирает один из трёх инструментов.
Логика нарочно простая и предсказуемая - её видно на защите.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Ключевые слова-триггеры (подстроки, регистр не важен, «ё» приводится к «е»).
KEYWORDS: dict[str, tuple[str, ...]] = {
    "now": (
        "врем", "час", "дата", "сегодня", "число", "день недели", "сейчас", "пояс",
        "time", "date", "today", "clock", "now", "weekday", "timezone",
    ),
    "lookup": (
        "проект", "стек", "файл", "команд", "запуск", "docker", "докер", "памят",
        "лог", "настрой", "конфиг", "переменн", "порт", "тест", "структур", "зависим",
        "project", "stack", "file", "command", "run", "memory", "log", "config",
        "env", "port", "test", "structure", "dependency",
    ),
    "recall": (
        "что я спрашивал", "что спрашивал", "напомни", "предыдущ", "истори",
        "what did i ask", "previous question", "earlier", "recall",
    ),
    "calculator": (
        "посчитай", "вычисли", "сколько будет", "рассчитай",
        "calculate", "compute", "solve", "sum",
    ),
}

# Приоритет при равенстве очков.
PRIORITY = ("calculator", "now", "lookup", "recall")

_TIMEZONE_HINTS: dict[str, str] = {
    "москв": "Europe/Moscow",
    "новосибир": "Asia/Novosibirsk",
    "екатеринбург": "Asia/Yekaterinburg",
    "казан": "Europe/Kazan",
    "лондон": "Europe/London",
    "нью-йорк": "America/New_York",
    "utc": "UTC",
}

_MATH_WORD_REPLACEMENTS = (
    ("умножить на", "*"),
    ("умножь на", "*"),
    ("помножить на", "*"),
    ("разделить на", "/"),
    ("раздели на", "/"),
    ("поделить на", "/"),
    ("плюс", "+"),
    ("минус", "-"),
    ("делить на", "/"),
    ("divided by", "/"),
    ("multiplied by", "*"),
    ("plus", "+"),
    ("minus", "-"),
    ("times", "*"),
)

_EXPRESSION_RE = re.compile(r"[0-9+\-*/%^(). ]{3,}")


@dataclass
class Route:
    """Результат маршрутизации."""

    tool: str | None
    argument: str = ""
    scores: dict[str, int] = field(default_factory=dict)

    @property
    def matched(self) -> bool:
        return self.tool is not None


def _normalize(text: str) -> str:
    return (text or "").lower().replace("ё", "е")


def _normalize_math(text: str) -> str:
    result = _normalize(text)
    for source, target in _MATH_WORD_REPLACEMENTS:
        result = result.replace(source, target)
    return result


def find_expression(text: str) -> str:
    """Вытащить из вопроса самое длинное арифметическое выражение."""
    candidate = ""
    for match in _EXPRESSION_RE.finditer(_normalize_math(text)):
        piece = match.group().strip()
        if not piece:
            continue
        has_digit = any(char.isdigit() for char in piece)
        has_operator = any(operator in piece for operator in "+-*/%^")
        if has_digit and has_operator and len(piece) > len(candidate):
            candidate = piece
    return candidate


def detect_timezone(text: str) -> str:
    normalized = _normalize(text)
    for hint, timezone in _TIMEZONE_HINTS.items():
        if hint in normalized:
            return timezone
    return ""


def _score(text: str) -> dict[str, int]:
    scores: dict[str, int] = {}
    for tool, words in KEYWORDS.items():
        hits = sum(1 for word in words if word in text)
        if hits:
            scores[tool] = min(hits, 3)
    return scores


def route_question(question: str, *, default_timezone: str = "Europe/Moscow") -> Route:
    """Выбрать инструмент под запрос (mock-режим)."""
    text = _normalize(question)
    scores = _score(text)

    expression = find_expression(question)
    if expression:
        scores["calculator"] = scores.get("calculator", 0) + 4

    if not scores:
        return Route(tool=None, scores={})

    best_score = max(scores.values())
    for tool in PRIORITY:
        if scores.get(tool, 0) == best_score:
            chosen = tool
            break
    else:  # pragma: no cover - защита от изменения PRIORITY
        chosen = next(iter(scores))

    if chosen == "calculator":
        argument = expression
    elif chosen == "now":
        argument = detect_timezone(question) or default_timezone
    else:
        argument = (question or "").strip()

    return Route(tool=chosen, argument=argument, scores=scores)
