"""Тесты реестра инструментов и двух «локальных» инструментов: now и lookup."""

import unittest

from app.prompts import tool_descriptions
from app.tools import TOOL_NAMES, describe, get_tool, run_tool
from app.tools.now import now


class RegistryTest(unittest.TestCase):
    def test_three_tools_exactly(self):
        self.assertEqual(TOOL_NAMES, ("calculator", "now", "lookup"))

    def test_descriptions_exist_in_both_languages(self):
        for lang in ("ru", "en"):
            descriptions = tool_descriptions(lang)
            for name in TOOL_NAMES:
                with self.subTest(lang=lang, tool=name):
                    self.assertTrue(len(descriptions[name]) > 40)

    def test_descriptions_are_localized(self):
        self.assertNotEqual(describe("calculator", "ru"), describe("calculator", "en"))

    def test_unknown_tool_raises(self):
        with self.assertRaises(KeyError):
            get_tool("no-such-tool")

    def test_run_tool_dispatches(self):
        self.assertEqual(run_tool("calculator", "6*7"), "42")


class NowToolTest(unittest.TestCase):
    def test_default_timezone_is_moscow(self):
        self.assertIn("Europe/Moscow", now())

    def test_timezone_argument_is_respected(self):
        self.assertIn("UTC", now("UTC"))

    def test_weekday_is_present(self):
        self.assertIn("/", now())


class LookupToolTest(unittest.TestCase):
    def test_finds_stack_entry(self):
        result = run_tool("lookup", "на каком стеке сделан проект")
        self.assertIn("stack", result)

    def test_finds_docker_entry(self):
        result = run_tool("lookup", "как собрать docker образ")
        self.assertIn("docker", result)

    def test_returns_no_match_for_noise(self):
        self.assertIn("No matching", run_tool("lookup", "абракадабра ксчщ"))

    def test_empty_query_is_error(self):
        self.assertIn("Error", run_tool("lookup", "   "))


if __name__ == "__main__":
    unittest.main()
