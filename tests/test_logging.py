"""Тесты журнала запусков: формат JSONL и обязательные поля."""

import json
import unittest
from pathlib import Path

from app.logging_setup import RunLogger
from tests._tmp import remove_file, tmp_file


class LoggingTest(unittest.TestCase):
    def setUp(self):
        self.log_path = tmp_file(".jsonl")
        self.addCleanup(remove_file, self.log_path)
        self.logger = RunLogger(log_file=self.log_path, console=False)

    def _log(self, tool="calculator", question="2+2"):
        return self.logger.log_run(
            session="test",
            provider="mock",
            question=question,
            tool=tool,
            tool_args="2+2",
            tool_result="4",
            answer="4",
            duration_ms=1.5,
        )

    def test_file_is_created(self):
        self._log()
        self.assertTrue(self.logger.log_file.is_file())

    def test_line_is_valid_json(self):
        self._log()
        lines = self.logger.log_file.read_text(encoding="utf-8").splitlines()
        record = json.loads(lines[0])
        self.assertEqual(record["tool"], "calculator")

    def test_required_fields_present(self):
        record = self._log()
        for field in ("ts", "session", "provider", "question", "tool", "tool_args", "answer", "duration_ms"):
            self.assertIn(field, record)

    def test_appends_without_overwriting(self):
        self._log(question="первый")
        self._log(question="второй")
        lines = self.logger.log_file.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 2)

    def test_recent_returns_last_records(self):
        self._log(question="один")
        self._log(question="два")
        recent = self.logger.recent(limit=1)
        self.assertEqual(recent[0]["question"], "два")

    def test_cyrillic_is_preserved(self):
        self._log(question="сколько будет два плюс два")
        content = self.logger.log_file.read_text(encoding="utf-8")
        self.assertIn("сколько будет", content)


if __name__ == "__main__":
    unittest.main()
