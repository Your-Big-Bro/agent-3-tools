"""Тесты mock-роутера: правильно ли выбран инструмент под запрос."""

import unittest

from app.router_mock import detect_timezone, find_expression, route_question


class ExpressionTest(unittest.TestCase):
    def test_finds_simple_expression(self):
        self.assertEqual(find_expression("Сколько будет 12*7?"), "12*7")

    def test_finds_expression_with_spaces(self):
        self.assertEqual(find_expression("посчитай (15 + 27) * 3"), "(15 + 27) * 3")

    def test_ignores_dates(self):
        self.assertEqual(find_expression("какое сегодня число 12.11.2026"), "")

    def test_understands_russian_words(self):
        self.assertEqual(find_expression("сколько будет 5 умножить на 7"), "5 * 7")


class TimezoneTest(unittest.TestCase):
    def test_detects_moscow(self):
        self.assertEqual(detect_timezone("который час в Москве"), "Europe/Moscow")

    def test_unknown_timezone(self):
        self.assertEqual(detect_timezone("который час"), "")


class RoutingTest(unittest.TestCase):
    def test_arithmetic_goes_to_calculator(self):
        route = route_question("Сколько будет 125 * 12?")
        self.assertEqual(route.tool, "calculator")
        self.assertEqual(route.argument, "125 * 12")

    def test_math_word_goes_to_calculator(self):
        route = route_question("посчитай (2+2)*2")
        self.assertEqual(route.tool, "calculator")

    def test_time_question_goes_to_now(self):
        route = route_question("Который сейчас час?")
        self.assertEqual(route.tool, "now")

    def test_timezone_question_passes_timezone(self):
        route = route_question("который час в Москве")
        self.assertEqual(route.tool, "now")
        self.assertEqual(route.argument, "Europe/Moscow")

    def test_project_question_goes_to_lookup(self):
        route = route_question("Расскажи про стек проекта")
        self.assertEqual(route.tool, "lookup")

    def test_docker_question_goes_to_lookup(self):
        route = route_question("как запустить проект в docker?")
        self.assertEqual(route.tool, "lookup")

    def test_recall_question(self):
        route = route_question("Что я спрашивал раньше?")
        self.assertEqual(route.tool, "recall")

    def test_english_time_question(self):
        route = route_question("What time is it now?")
        self.assertEqual(route.tool, "now")

    def test_greeting_has_no_tool(self):
        self.assertIsNone(route_question("привет").tool)

    def test_empty_question_has_no_tool(self):
        self.assertIsNone(route_question("   ").tool)


if __name__ == "__main__":
    unittest.main()
