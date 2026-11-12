"""Агент с тремя инструментами: два режима работы.

* ``mock``  - детерминированный роутер, работает без модели и без зависимостей;
* ``ollama`` - настоящий ReAct-агент на LangGraph с чекпоинтером в SQLite.

Оба режима используют одни и те же инструменты, одну и ту же память
и один и тот же журнал запусков, поэтому поведение сопоставимо.
"""

from __future__ import annotations

import json
import re
import time
from typing import Any

from app.config import Settings
from app.logging_setup import RunLogger
from app.memory import SqliteHistory
from app.prompts import labels, system_prompt, tool_descriptions
from app.router_mock import route_question
from app.tools import TOOL_NAMES, describe, run_tool
from app.tracing import enable_tracing

# Сколько последних сообщений держим в состоянии графа.
# Локальная модель на 3B плохо переносит длинную историю, поэтому окно короткое.
MAX_HISTORY_TURNS = 3


# Регулярки для демонстрации памяти в mock-режиме (без модели).
_NAME_PATTERNS = (
    re.compile(r"меня зовут\s+([A-Za-zА-Яа-яЁё-]+)", re.IGNORECASE),
    re.compile(r"my name is\s+([A-Za-zА-Яа-яЁё-]+)", re.IGNORECASE),
)
_REMEMBER_RE = re.compile(r"запомни|remember", re.IGNORECASE)
_ASK_NAME_RE = re.compile(r"как меня зовут|what(?:'s| is) my name", re.IGNORECASE)


class BaseAgent:
    """Общий каркас: память, журнал, единый способ записи результата."""

    provider = "base"

    def __init__(self, settings: Settings, history: SqliteHistory, logger: RunLogger) -> None:
        self.settings = settings
        self.history = history
        self.logger = logger

    @property
    def lang(self) -> str:
        return self.settings.prompt_lang

    def ask(self, question: str, session: str = "default") -> str:  # pragma: no cover - интерфейс
        raise NotImplementedError

    def reset(self, session: str = "default") -> int:
        self.history.clear_facts(session)
        return self.history.reset(session)

    def _finish(
        self,
        *,
        started: float,
        session: str,
        question: str,
        tool: str | None,
        tool_args: str | None,
        tool_result: str | None,
        answer: str,
    ) -> str:
        duration_ms = (time.perf_counter() - started) * 1000
        self.history.add(session, "user", question)
        self.history.add(session, "assistant", answer, tool=tool)
        self.logger.log_run(
            session=session,
            provider=self.provider,
            question=question,
            tool=tool,
            tool_args=tool_args,
            tool_result=tool_result,
            answer=answer,
            duration_ms=duration_ms,
        )
        return answer


class MockAgent(BaseAgent):
    """Агент без модели: инструмент выбирается по ключевым словам."""

    provider = "mock"

    def ask(self, question: str, session: str = "default") -> str:
        started = time.perf_counter()
        text = (question or "").strip()
        if not text:
            return self._finish(
                started=started,
                session=session,
                question=question,
                tool=None,
                tool_args=None,
                tool_result=None,
                answer=labels(self.lang)["unknown"],
            )

        memory_answer = self._memory_intent(text, session)
        if memory_answer is not None:
            return self._finish(
                started=started,
                session=session,
                question=text,
                tool=None,
                tool_args=None,
                tool_result=None,
                answer=memory_answer,
            )

        route = route_question(text, default_timezone=self.settings.timezone)

        if route.tool is None:
            answer = self._unknown_answer()
            return self._finish(
                started=started,
                session=session,
                question=text,
                tool=None,
                tool_args=None,
                tool_result=None,
                answer=answer,
            )

        if route.tool == "recall":
            answer = self._recall(session)
            return self._finish(
                started=started,
                session=session,
                question=text,
                tool="recall",
                tool_args="session history",
                tool_result=answer,
                answer=answer,
            )

        result = run_tool(route.tool, route.argument)
        answer = self._format_answer(route.tool, route.argument, result)
        return self._finish(
            started=started,
            session=session,
            question=text,
            tool=route.tool,
            tool_args=route.argument,
            tool_result=result,
            answer=answer,
        )

    def _format_answer(self, tool: str, argument: str, result: str) -> str:
        text = labels(self.lang)
        lines = [text["used_tool"].format(tool=tool)]
        if argument:
            lines.append(text["args"].format(args=argument))
        lines.append(text["result"].format(result=result))
        return "\n".join(lines)

    def _unknown_answer(self) -> str:
        text = labels(self.lang)
        return f"{text['unknown']}\n{', '.join(TOOL_NAMES)}"

    def _memory_intent(self, text: str, session: str) -> str | None:
        """Демонстрация памяти без модели: запомнить имя и вспомнить его."""
        strings = labels(self.lang)

        if _ASK_NAME_RE.search(text):
            name = self.history.get_fact(session, "name")
            return strings["name_known"].format(name=name) if name else strings["name_unknown"]

        if _REMEMBER_RE.search(text):
            for pattern in _NAME_PATTERNS:
                match = pattern.search(text)
                if match:
                    name = match.group(1)
                    self.history.set_fact(session, "name", name)
                    return strings["name_saved"].format(name=name)

        return None

    def _recall(self, session: str) -> str:
        text = labels(self.lang)
        questions = self.history.questions(session, limit=5)
        if not questions:
            return text["recall_empty"]
        listed = "\n".join(f"{index}. {question}" for index, question in enumerate(questions, 1))
        return f"{text['recall']}\n{listed}"


class LLMAgent(BaseAgent):
    """ReAct-агент на LangGraph поверх локальной модели Ollama."""

    provider = "ollama"

    def __init__(self, settings: Settings, history: SqliteHistory, logger: RunLogger) -> None:
        super().__init__(settings, history, logger)
        self.tracing_enabled = enable_tracing(settings)
        self._graph: Any | None = None
        self._checkpointer: Any | None = None
        self._connection: Any | None = None

    # --- сборка графа -----------------------------------------------------
    def _build_tools(self) -> list[Any]:
        from langchain_core.tools import StructuredTool

        from app.tools.calculator import calculator
        from app.tools.lookup import lookup
        from app.tools.now import now

        descriptions = tool_descriptions(self.lang)

        def _calculator(expression: str) -> str:
            return calculator(expression)

        def _now(timezone: str = "") -> str:
            return now(timezone)

        def _lookup(query: str) -> str:
            return lookup(query)

        return [
            StructuredTool.from_function(
                func=_calculator, name="calculator", description=descriptions["calculator"]
            ),
            StructuredTool.from_function(func=_now, name="now", description=descriptions["now"]),
            StructuredTool.from_function(func=_lookup, name="lookup", description=descriptions["lookup"]),
        ]

    def _ensure_graph(self):
        if self._graph is not None:
            return self._graph

        import sqlite3

        from langgraph.checkpoint.sqlite import SqliteSaver
        from langgraph.prebuilt import create_react_agent

        from app.llm import build_chat_model

        model = build_chat_model(self.settings)
        connection = sqlite3.connect(self.settings.db_path, check_same_thread=False)
        self._connection = connection
        self._checkpointer = SqliteSaver(connection)
        self._graph = create_react_agent(
            model=model,
            tools=self._build_tools(),
            prompt=system_prompt(self.lang),
            checkpointer=self._checkpointer,
        )
        return self._graph

    # --- запрос -----------------------------------------------------------
    def ask(self, question: str, session: str = "default") -> str:
        from langchain_core.messages import HumanMessage

        started = time.perf_counter()
        graph = self._ensure_graph()
        config = {"configurable": {"thread_id": session}}

        # Сколько сообщений уже накоплено в этой ветке памяти - чтобы разбирать
        # только те, что появились в текущем запросе, а не всю историю.
        prior_messages = 0
        try:
            snapshot = graph.get_state(config)
            prior_messages = len(snapshot.values.get("messages", []))
        except Exception:  # noqa: BLE001 - для нового thread_id состояния ещё нет
            prior_messages = 0

        state = graph.invoke({"messages": [HumanMessage(content=question)]}, config=config)

        messages = state.get("messages", [])[prior_messages:]
        tool_names: list[str] = []
        tool_args: dict[str, Any] | None = None
        tool_result: str | None = None

        for message in messages:
            calls = getattr(message, "tool_calls", None)
            if calls:
                for call in calls:
                    tool_names.append(str(call.get("name")))
                    if tool_args is None:
                        tool_args = call.get("args") or {}
            if message.__class__.__name__ == "ToolMessage":
                tool_result = str(message.content)

        answer = self._last_text(messages) or "(empty response)"
        tool_field = ", ".join(tool_names) if tool_names else None

        # Небольшая модель теряет концентрацию на длинной истории, поэтому
        # держим в состоянии только последние сообщения (окно контекста).
        self._trim_state(graph, config, state.get("messages", []), keep_turns=MAX_HISTORY_TURNS)

        return self._finish(
            started=started,
            session=session,
            question=question,
            tool=tool_field,
            tool_args=json.dumps(tool_args, ensure_ascii=False) if tool_args else None,
            tool_result=tool_result,
            answer=answer,
        )

    @staticmethod
    def _last_text(messages: list[Any]) -> str:
        for message in reversed(messages):
            if message.__class__.__name__ != "AIMessage":
                continue
            content = message.content
            if isinstance(content, str):
                return content.strip()
            if isinstance(content, list):
                chunks = []
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        chunks.append(str(block.get("text", "")))
                    elif isinstance(block, str):
                        chunks.append(block)
                return "".join(chunks).strip()
        return ""

    @staticmethod
    def _trim_state(graph: Any, config: dict, messages: list[Any], keep_turns: int) -> None:
        """Оставить только последние ``keep_turns`` реплик пользователя.

        Режем строго по границе HumanMessage: иначе пара «вызов инструмента →
        результат» рвётся, и модель начинает печатать вызовы текстом.
        """
        try:
            from langchain_core.messages import HumanMessage, RemoveMessage

            starts = [index for index, message in enumerate(messages) if isinstance(message, HumanMessage)]
            if len(starts) <= keep_turns:
                return

            cut = starts[-keep_turns]
            stale = [message for message in messages[:cut] if getattr(message, "id", None)]
            if stale:
                graph.update_state(config, {"messages": [RemoveMessage(id=m.id) for m in stale]})
        except Exception:  # noqa: BLE001 - усечение не должно ронять запрос
            pass

    def reset(self, session: str = "default") -> int:
        """Очистить и историю реплик, и состояние графа (чекпоинты LangGraph)."""
        import sqlite3

        removed = super().reset(session)

        connection = self._connection
        temporary = False
        if connection is None:
            connection = sqlite3.connect(self.settings.db_path, check_same_thread=False)
            temporary = True

        try:
            tables = [
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                ).fetchall()
            ]
            for table in tables:
                columns = [row[1] for row in connection.execute(f"PRAGMA table_info({table})")]
                if "thread_id" in columns:
                    connection.execute(f"DELETE FROM {table} WHERE thread_id = ?", (session,))
            connection.commit()
        except sqlite3.Error:
            pass
        finally:
            if temporary:
                connection.close()

        return removed


def build_agent(settings: Settings) -> BaseAgent:
    """Фабрика: выбрать реализацию агента по настройкам."""
    history = SqliteHistory(settings.db_path)
    logger = RunLogger(settings.logs_dir)

    if settings.llm_provider == "ollama":
        return LLMAgent(settings, history, logger)

    return MockAgent(settings, history, logger)


def describe_tools(lang: str) -> dict[str, str]:
    """Описания инструментов на выбранном языке (для README и отладки)."""
    return {name: describe(name, lang) for name in TOOL_NAMES}
