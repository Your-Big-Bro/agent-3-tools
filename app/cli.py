"""Командный интерфейс агента.

Режимы:
  python -m app                  интерактивный диалог
  python -m app "вопрос"         один запрос и выход
  python -m app --demo           демонстрационный сценарий из семи запросов
"""

from __future__ import annotations

import argparse
import dataclasses
import sys

from app.agent import build_agent
from app.config import get_settings
from app.tracing import tracing_status

DEMO_QUESTIONS: tuple[str, ...] = (
    "Сколько будет 125 * 12?",
    "Какое сегодня число и день недели?",
    "На каком стеке сделан этот проект?",
    "Меня зовут Дима, запомни это.",
    "Как меня зовут?",
    "Посчитай (15 + 27) * 3",
    "Что такое Docker в этом проекте?",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="app",
        description="Агент с тремя инструментами: calculator, now, lookup.",
    )
    parser.add_argument("question", nargs="?", help="вопрос; без него запускается диалог")
    parser.add_argument(
        "--session", default="default", help="идентификатор сессии для истории (по умолчанию: default)"
    )
    parser.add_argument("--lang", choices=("ru", "en"), help="язык промптов на один запуск")
    parser.add_argument("--demo", action="store_true", help="прогнать демонстрационный сценарий")
    parser.add_argument("--reset", action="store_true", help="очистить историю сессии перед запуском")
    parser.add_argument("--log", action="store_true", help="показать последние записи журнала")
    parser.add_argument("--version", action="version", version="agent-3-tools 1.0.0")
    return parser


def _print_banner(settings, session: str) -> None:
    print("agent-3-tools - агент с тремя инструментами")
    print(f"  провайдер : {settings.llm_provider}")
    print(f"  язык      : {settings.prompt_lang}")
    print(f"  сессия    : {session}")
    print(f"  память    : {settings.db_path}")
    print(f"  журнал    : {settings.logs_dir / 'runs.jsonl'}")
    print(f"  трейсинг  : {tracing_status(settings)}")
    print()


def _run_demo(agent, session: str) -> int:
    print("=== Демонстрационный сценарий ===")
    used: list[str] = []
    for index, question in enumerate(DEMO_QUESTIONS, 1):
        print(f"\n[{index}/{len(DEMO_QUESTIONS)}] Вопрос: {question}")
        answer = agent.ask(question, session=session)
        print(answer)

    for record in agent.logger.recent(limit=len(DEMO_QUESTIONS)):
        if record.get("tool"):
            used.append(record["tool"])

    print("\n=== Итог ===")
    print(f"запросов: {len(DEMO_QUESTIONS)}")
    print(f"использованные инструменты: {', '.join(used) if used else 'нет'}")
    print(f"журнал: {agent.logger.log_file}")
    return 0


def _run_repl(agent, session: str) -> int:
    print("Введите вопрос или команду (/help, /history, /reset, /exit).\n")
    while True:
        try:
            question = input("вы> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0

        if not question:
            continue
        if question in ("/exit", "/quit", "exit", "quit"):
            return 0
        if question == "/help":
            print("  /history - сколько реплик в текущей сессии")
            print("  /reset   - очистить историю сессии")
            print("  /exit    - выход\n")
            continue
        if question == "/history":
            print(f"  реплик в сессии {session!r}: {agent.history.count(session)}\n")
            continue
        if question == "/reset":
            removed = agent.reset(session)
            print(f"  очищено реплик: {removed}\n")
            continue

        try:
            print(agent.ask(question, session=session))
        except Exception as exc:  # noqa: BLE001 - в интерактиве показываем ошибку и живём дальше
            print(f"  ошибка: {exc}")
        print()


def main(argv: list[str] | None = None) -> int:
    if not sys.stdout.isatty():
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):
            pass

    parser = build_parser()
    args = parser.parse_args(argv)

    settings = get_settings()
    if args.lang:
        settings = dataclasses.replace(settings, prompt_lang=args.lang)

    if settings.llm_provider == "ollama":
        from app.llm import check_ollama

        reachable, message = check_ollama(settings)
        if not reachable:
            print(f"Предупреждение: {message}", file=sys.stderr)
            print(
                "Проверьте, что Ollama запущена (`ollama serve`) и модель скачана "
                f"(`ollama pull {settings.llm_model}`). Либо верните mock-режим: LLM_PROVIDER=mock",
                file=sys.stderr,
            )

    agent = build_agent(settings)

    if args.reset:
        removed = agent.reset(args.session)
        print(f"История сессии {args.session!r} очищена, удалено реплик: {removed}")

    if args.log:
        records = agent.logger.recent(limit=10)
        if not records:
            print("Журнал пуст.")
        for record in records:
            print(
                f"{record['ts']} tool={record.get('tool') or '-'} "
                f"session={record['session']} q={record['question'][:60]}"
            )
        return 0

    if args.demo:
        _print_banner(settings, args.session)
        return _run_demo(agent, args.session)

    if args.question:
        try:
            print(agent.ask(args.question, session=args.session))
        except Exception as exc:  # noqa: BLE001 - единая точка вывода ошибок
            print(f"Ошибка: {exc}", file=sys.stderr)
            return 1
        return 0

    _print_banner(settings, args.session)
    return _run_repl(agent, args.session)
