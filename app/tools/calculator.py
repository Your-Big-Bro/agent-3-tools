"""Инструмент ``calculator``: безопасный расчёт арифметики через AST.

``eval`` не используется: разбираем выражение в дерево и разрешаем только
числовые литералы, скобки и базовые операторы.
"""

from __future__ import annotations

import ast
import operator
from typing import Callable

MAX_EXPRESSION_LENGTH = 200
MAX_POWER = 100

_BINOPS: dict[type[ast.operator], Callable[[float, float], float]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

_UNARYOPS: dict[type[ast.unaryop], Callable[[float], float]] = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def _evaluate(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return _evaluate(node.body)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise ValueError("only numbers are allowed")
        return node.value
    if isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in _BINOPS:
            raise ValueError(f"operator {op_type.__name__} is not allowed")
        left = _evaluate(node.left)
        right = _evaluate(node.right)
        if op_type is ast.Pow and abs(right) > MAX_POWER:
            raise ValueError("exponent is too large")
        return _BINOPS[op_type](left, right)
    if isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in _UNARYOPS:
            raise ValueError(f"operator {op_type.__name__} is not allowed")
        return _UNARYOPS[op_type](_evaluate(node.operand))
    raise ValueError(f"unsupported expression element: {type(node).__name__}")


def _format_number(value: float) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, float):
        return f"{value:.10g}"
    return str(value)


def calculator(expression: str) -> str:
    """Вычислить арифметическое выражение и вернуть результат строкой."""
    text = (expression or "").strip()
    text = text.strip("`").strip().strip("=").strip()
    if text.endswith("?"):
        text = text[:-1].strip()

    if not text:
        return "Error: empty expression"
    if len(text) > MAX_EXPRESSION_LENGTH:
        return "Error: expression is too long"
    if "^" in text:
        text = text.replace("^", "**")

    try:
        tree = ast.parse(text, mode="eval")
        result = _evaluate(tree)
        return _format_number(result)
    except ZeroDivisionError:
        return "Error: division by zero"
    except (SyntaxError, ValueError, TypeError, OverflowError) as exc:
        return f"Error: {exc}"
