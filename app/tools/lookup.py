"""Инструмент ``lookup``: поиск по локальной базе знаний проекта."""

from __future__ import annotations

import json
import re
from pathlib import Path

KB_PATH = Path(__file__).resolve().parents[2] / "data" / "kb.json"
MAX_RESULTS = 3
MIN_SCORE = 1

_WORD_RE = re.compile(r"[a-zA-Zа-яА-ЯёЁ0-9_]+")
_STOPWORDS = {
    "что", "как", "какой", "какие", "каком", "какая", "где", "это", "есть", "для",
    "про", "мне", "расскажи", "подскажи", "можно", "нужно", "или", "and", "the",
    "what", "which", "how", "does", "this", "that", "about", "with", "for", "you",
}

# Грубые окончания для русского: «стеке» -> «стек», «памяти» -> «памят».
_ENDINGS = (
    "иями", "ями", "ами", "ов", "ев", "ах", "ях", "ой", "ей", "ый", "ий",
    "ая", "ое", "ые", "ие", "ам", "ям", "ом", "ем", "у", "ю", "а", "я",
    "ы", "и", "е", "о", "ь",
)


def _stem(word: str) -> str:
    for ending in _ENDINGS:
        if len(word) - len(ending) >= 4 and word.endswith(ending):
            return word[: -len(ending)]
    return word


def _tokens(text: str) -> set[str]:
    words = {w.lower() for w in _WORD_RE.findall(text or "")}
    return {_stem(w) for w in words if len(w) > 2 and w not in _STOPWORDS}



def _load_kb(path: Path) -> list[dict]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if isinstance(data, dict):
        data = data.get("entries", [])
    return [item for item in data if isinstance(item, dict)]


def _entry_text(entry: dict) -> str:
    parts = [str(entry.get("title", "")), str(entry.get("text", ""))]
    parts.extend(str(tag) for tag in entry.get("tags", []) or [])
    return " ".join(parts)


def _score(query_tokens: set[str], entry: dict) -> int:
    tags = {_stem(str(tag).lower()) for tag in entry.get("tags", []) or []}
    title = _tokens(str(entry.get("title", "")))
    body = _tokens(str(entry.get("text", "")))
    score = 0
    score += 3 * len(query_tokens & tags)
    score += 2 * len(query_tokens & title)
    score += len(query_tokens & body)
    return score


def lookup(query: str, kb_path: Path | None = None) -> str:
    """Найти в базе знаний записи, релевантные запросу."""
    entries = _load_kb(kb_path or KB_PATH)
    if not entries:
        return "Error: knowledge base is empty or not found"

    query_tokens = _tokens(query)
    if not query_tokens:
        return "Error: empty query"

    scored = [(entry, _score(query_tokens, entry)) for entry in entries]
    scored = [(entry, score) for entry, score in scored if score >= MIN_SCORE]
    scored.sort(key=lambda pair: pair[1], reverse=True)

    if not scored:
        return "No matching entries in the knowledge base"

    lines = []
    for entry, score in scored[:MAX_RESULTS]:
        title = entry.get("title", "untitled")
        text = entry.get("text", "")
        lines.append(f"- [{entry.get('id', '?')}] {title} (score={score}): {text}")
    return "\n".join(lines)
