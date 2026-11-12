"""Логирование запусков: консоль + файл ``logs/runs.jsonl``.

Требование задания — «видно, какой инструмент выбрал агент». Поэтому каждая
запись содержит поля ``tool`` и ``tool_args``, а консольная строка начинается
с имени инструмента.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


class RunLogger:
    """Пишет структурированный журнал запусков."""

    def __init__(
        self,
        logs_dir: Path | str | None = None,
        *,
        log_file: Path | str | None = None,
        console: bool = True,
    ) -> None:
        if log_file is not None:
            self.log_file = Path(log_file)
            self.logs_dir = self.log_file.parent
        elif logs_dir is not None:
            self.logs_dir = Path(logs_dir)
            self.log_file = self.logs_dir / "runs.jsonl"
        else:
            raise ValueError("нужен либо logs_dir, либо log_file")

        self.console = console
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    def log_run(
        self,
        *,
        session: str,
        provider: str,
        question: str,
        tool: str | None,
        tool_args: str | None,
        tool_result: str | None,
        answer: str,
        duration_ms: float,
    ) -> dict:
        record = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "session": session,
            "provider": provider,
            "question": question,
            "tool": tool,
            "tool_args": tool_args,
            "tool_result": tool_result,
            "answer": answer,
            "duration_ms": round(duration_ms, 2),
        }
        with self.log_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

        if self.console:
            stamp = record["ts"][11:19]
            print(
                f"[{stamp}] session={session} provider={provider} "
                f"tool={tool or '-'} args={tool_args or '-'} "
                f"{record['duration_ms']} ms -> {self._short(answer)}"
            )
        return record

    def recent(self, limit: int = 5) -> list[dict]:
        """Последние записи журнала (для отчёта и проверки)."""
        if not self.log_file.is_file():
            return []
        lines = self.log_file.read_text(encoding="utf-8").splitlines()
        records = []
        for line in lines[-limit:]:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return records

    @staticmethod
    def _short(text: str, limit: int = 90) -> str:
        flat = " ".join((text or "").split())
        return flat if len(flat) <= limit else flat[: limit - 1] + "…"
