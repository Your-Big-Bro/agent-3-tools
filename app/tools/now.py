"""Инструмент ``now``: текущая дата, время, день недели и часовой пояс."""

from __future__ import annotations

import os
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

DEFAULT_TIMEZONE = "Europe/Moscow"

_WEEKDAYS_RU = (
    "понедельник",
    "вторник",
    "среда",
    "четверг",
    "пятница",
    "суббота",
    "воскресенье",
)


def _resolve_timezone(timezone: str) -> ZoneInfo:
    name = (timezone or "").strip() or os.environ.get("APP_TIMEZONE", "") or DEFAULT_TIMEZONE
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo(DEFAULT_TIMEZONE)


def now(timezone: str = "") -> str:
    """Вернуть текущий момент в указанном поясе одной строкой."""
    tz = _resolve_timezone(timezone)
    moment = datetime.now(tz)
    weekday_en = moment.strftime("%A")
    weekday_ru = _WEEKDAYS_RU[moment.weekday()]
    offset = moment.strftime("%z")
    offset = f"{offset[:3]}:{offset[3:]}" if offset else ""
    return (
        f"{moment:%Y-%m-%d %H:%M:%S} {moment.tzname()} (UTC{offset}), "
        f"{weekday_en} / {weekday_ru}, timezone: {tz.key}"
    )
