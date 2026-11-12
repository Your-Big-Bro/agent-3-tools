"""Вспомогательные функции для тестов.

Используются отдельные *файлы* во временном каталоге системы: их можно
создавать и удалять даже в ограниченных окружениях, где удаление каталогов
запрещено (именно на этом падали тесты, использующие TemporaryDirectory).
"""

import os
import tempfile
from pathlib import Path


def tmp_file(suffix: str) -> Path:
    """Создать пустой временный файл и вернуть путь к нему."""
    handle, name = tempfile.mkstemp(prefix="agent3-", suffix=suffix)
    os.close(handle)
    return Path(name)


def remove_file(path: Path) -> None:
    """Удалить файл и возможные служебные файлы SQLite рядом с ним."""
    candidates = [Path(path)]
    candidates += [Path(f"{path}{extra}") for extra in ("-journal", "-wal", "-shm")]
    for candidate in candidates:
        try:
            candidate.unlink(missing_ok=True)
        except OSError:
            pass
