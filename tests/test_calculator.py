"""Тесты инструмента calculator: арифметика и защита от инъекций."""

import unittest

from app.tools.calculator import calculator


class CalculatorTest(unittest.TestCase):
    def test_adds(self):
        self.assertEqual(calculator("2+2"), "4")

    def test_multiplies(self):
        self.assertEqual(calculator("125 * 12"), "1500")

    def test_parentheses(self):
        self.assertEqual(calculator("(15 + 27) * 3"), "126")

    def test_float_result(self):
        self.assertEqual(calculator("10/4"), "2.5")

    def test_caret_as_power(self):
        self.assertEqual(calculator("2^10"), "1024")

    def test_unary_minus(self):
        self.assertEqual(calculator("-5 * -3"), "15")

    def test_strips_question_mark(self):
        self.assertEqual(calculator("7*6?"), "42")

    def test_division_by_zero_is_reported(self):
        self.assertTrue(calculator("1/0").startswith("Error"))

    def test_code_is_rejected(self):
        self.assertTrue(calculator("__import__('os').system('dir')").startswith("Error"))

    def test_names_are_rejected(self):
        self.assertTrue(calculator("print(1)").startswith("Error"))

    def test_empty_expression(self):
        self.assertTrue(calculator("   ").startswith("Error"))

    def test_too_long_expression(self):
        self.assertTrue(calculator("1+" * 200 + "1").startswith("Error"))


if __name__ == "__main__":
    unittest.main()
