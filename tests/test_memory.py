"""Тесты памяти диалога."""

import unittest
from pathlib import Path

from app.memory import SqliteHistory
from tests._tmp import remove_file, tmp_file


class MemoryTest(unittest.TestCase):
    def setUp(self):
        self.db_path = tmp_file(".sqlite")
        self.addCleanup(remove_file, self.db_path)
        self.history = SqliteHistory(self.db_path)

    def test_roundtrip(self):
        self.history.add("s1", "user", "вопрос")
        self.history.add("s1", "assistant", "ответ", tool="calculator")
        records = self.history.history("s1")

        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["role"], "user")
        self.assertEqual(records[1]["tool"], "calculator")

    def test_sessions_are_isolated(self):
        self.history.add("s1", "user", "первый")
        self.history.add("s2", "user", "второй")

        self.assertEqual([r["content"] for r in self.history.history("s1")], ["первый"])
        self.assertEqual([r["content"] for r in self.history.history("s2")], ["второй"])

    def test_questions_returns_only_user_messages(self):
        self.history.add("s1", "user", "вопрос")
        self.history.add("s1", "assistant", "ответ")
        self.assertEqual(self.history.questions("s1"), ["вопрос"])

    def test_persists_between_instances(self):
        self.history.add("s1", "user", "сохранись")
        reopened = SqliteHistory(self.db_path)
        self.assertEqual(self.history.count("s1"), 1)
        self.assertEqual(reopened.count("s1"), 1)

    def test_reset(self):
        self.history.add("s1", "user", "вопрос")
        removed = self.history.reset("s1")
        self.assertEqual(removed, 1)
        self.assertEqual(self.history.count("s1"), 0)

    def test_sessions_listing(self):
        self.history.add("alpha", "user", "a")
        self.history.add("beta", "user", "b")
        self.assertEqual(sorted(self.history.sessions()), ["alpha", "beta"])

    def test_facts_roundtrip(self):
        self.history.set_fact("s1", "name", "Дима")
        self.assertEqual(self.history.get_fact("s1", "name"), "Дима")

    def test_fact_is_overwritten(self):
        self.history.set_fact("s1", "name", "Дима")
        self.history.set_fact("s1", "name", "Петя")
        self.assertEqual(self.history.get_fact("s1", "name"), "Петя")

    def test_facts_are_isolated_between_sessions(self):
        self.history.set_fact("s1", "name", "Дима")
        self.assertIsNone(self.history.get_fact("s2", "name"))

    def test_clear_facts(self):
        self.history.set_fact("s1", "name", "Дима")
        self.history.clear_facts("s1")
        self.assertIsNone(self.history.get_fact("s1", "name"))


if __name__ == "__main__":
    unittest.main()
