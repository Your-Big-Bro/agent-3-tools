"""Интеграционные тесты mock-агента: маршрутизация, память, журнал."""

import dataclasses
import tempfile
import unittest
from pathlib import Path

from app.agent import MockAgent, build_agent
from app.config import Settings
from app.logging_setup import RunLogger
from app.memory import SqliteHistory
from tests._tmp import remove_file, tmp_file

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class MockAgentTest(unittest.TestCase):
    def setUp(self):
        self.db_path = tmp_file(".sqlite")
        self.log_path = tmp_file(".jsonl")
        self.addCleanup(remove_file, self.db_path)
        self.addCleanup(remove_file, self.log_path)

        self.settings = dataclasses.replace(
            Settings(),
            llm_provider="mock",
            prompt_lang="ru",
            db_path=self.db_path,
            logs_dir=Path(tempfile.gettempdir()),
            kb_path=PROJECT_ROOT / "data" / "kb.json",
            langsmith_tracing=False,
        )
        self.history = SqliteHistory(self.settings.db_path)
        self.logger = RunLogger(log_file=self.log_path, console=False)
        self.agent = MockAgent(self.settings, self.history, self.logger)

    def test_calculator_is_selected_and_used(self):
        answer = self.agent.ask("Сколько будет 21 * 2?", session="s1")
        self.assertIn("calculator", answer)
        self.assertIn("42", answer)

    def test_time_tool_is_selected(self):
        answer = self.agent.ask("Который сейчас час?", session="s1")
        self.assertIn("now", answer)
        self.assertIn("MSK", answer)

    def test_lookup_tool_is_selected(self):
        answer = self.agent.ask("На каком стеке сделан проект?", session="s1")
        self.assertIn("lookup", answer)
        self.assertIn("LangGraph", answer)

    def test_history_is_recorded(self):
        self.agent.ask("2+2", session="s1")
        self.assertEqual(self.history.count("s1"), 2)

    def test_memory_answers_about_previous_questions(self):
        self.agent.ask("Сколько будет 6*7?", session="s1")
        answer = self.agent.ask("Что я спрашивал раньше?", session="s1")
        self.assertIn("6*7", answer)

    def test_remembers_name_and_recalls_it(self):
        saved = self.agent.ask("Меня зовут Дима, запомни это.", session="s1")
        self.assertIn("Дима", saved)

        recalled = self.agent.ask("Как меня зовут?", session="s1")
        self.assertIn("Дима", recalled)

    def test_name_is_unknown_in_fresh_session(self):
        answer = self.agent.ask("Как меня зовут?", session="other")
        self.assertIn("не называли", answer)

    def test_name_memory_survives_restart(self):
        self.agent.ask("Меня зовут Дима, запомни это.", session="s1")

        from app.agent import build_agent

        fresh = build_agent(self.settings)
        self.assertIn("Дима", fresh.ask("Как меня зовут?", session="s1"))

    def test_unknown_question_uses_no_tool(self):
        answer = self.agent.ask("привет", session="s1")
        self.assertTrue(answer)
        record = self.logger.recent(limit=1)[0]
        self.assertIsNone(record["tool"])

    def test_each_run_is_logged(self):
        self.agent.ask("2+2", session="s1")
        self.agent.ask("3+3", session="s1")
        self.assertEqual(len(self.logger.recent(limit=10)), 2)

    def test_sessions_do_not_mix(self):
        self.agent.ask("2+2", session="a")
        self.agent.ask("3+3", session="b")
        self.assertEqual(self.history.count("a"), 2)
        self.assertEqual(self.history.count("b"), 2)

    def test_english_labels(self):
        english = dataclasses.replace(self.settings, prompt_lang="en")
        agent = MockAgent(english, self.history, self.logger)
        answer = agent.ask("What is 2+2?", session="en")
        self.assertIn("Used", answer)

    def test_factory_returns_mock_agent_by_default(self):
        agent = build_agent(self.settings)
        self.assertIsInstance(agent, MockAgent)


if __name__ == "__main__":
    unittest.main()
