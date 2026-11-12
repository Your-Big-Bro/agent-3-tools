"""Промпты и описания инструментов на двух языках (ru/en).

Описания инструментов - не украшение: именно по ним модель принимает решение,
какой tool вызвать. Поэтому в каждом описании есть явные триггеры
(«арифметика», «дата и время», «проект») и запрет отвечать самому.
"""

from __future__ import annotations

SYSTEM_PROMPT_EN = """You are a routing agent with exactly three tools:

- calculator - arithmetic expressions;
- now - current date, time, weekday, timezone;
- lookup - facts about this project (stack, files, commands, configuration, Docker, tests).

HARD RULES:
1. Any arithmetic, even trivial, MUST go to calculator. Never compute in your head.
2. Any question about date, time, weekday or timezone MUST go to now.
3. Any question about THIS project (stack, files, Docker, settings, logs, memory, tests, commands)
   MUST go to lookup. You have no knowledge about this project from training, so never answer
   project questions from memory.
4. If the question refers to something said earlier, use the dialogue history.
5. Answer briefly (1-2 sentences) in the user's language.

Examples:
- "What is 19*7?" -> call the calculator tool with the expression 19*7
- "What time is it in Moscow?" -> call the now tool with the timezone Europe/Moscow
- "Which libraries does the project use?" -> call the lookup tool with the query project libraries
- "What is Docker in this project?" -> call the lookup tool with the query Docker
- "Hi!" -> answer directly, no tool
"""

SYSTEM_PROMPT_RU = """Ты - агент-маршрутизатор с ровно тремя инструментами:

- calculator - арифметические выражения;
- now - текущая дата, время, день недели, часовой пояс;
- lookup - факты об этом проекте (стек, файлы, команды, настройки, Docker, тесты).

ЖЁСТКИЕ ПРАВИЛА:
1. Любая арифметика, даже самая простая, - только calculator. Никогда не считай в уме.
2. Любой вопрос про дату, время, день недели или часовой пояс - только now.
3. Любой вопрос про ЭТОТ проект (стек, файлы, Docker, настройки, логи, память, тесты, команды) -
   только lookup. Ты не знаешь этот проект из обучения, поэтому не отвечай о нём по памяти.
4. Если вопрос ссылается на сказанное ранее - используй историю диалога.
5. Отвечай коротко (1-2 предложения) на языке пользователя.

Примеры:
- «Сколько будет 19*7?» → вызови инструмент calculator, передав выражение 19*7
- «Который час в Москве?» → вызови инструмент now, передав пояс Europe/Moscow
- «Какие библиотеки в проекте?» → вызови инструмент lookup с запросом библиотеки проекта
- «Что такое Docker в этом проекте?» → вызови инструмент lookup с запросом Docker
- «Привет!» → ответь без инструмента
"""

SYSTEM_PROMPTS: dict[str, str] = {
    "en": SYSTEM_PROMPT_EN,
    "ru": SYSTEM_PROMPT_RU,
}


TOOL_DESCRIPTIONS_EN: dict[str, str] = {
    "calculator": (
        "Evaluate an arithmetic expression and return the exact number. "
        "Use it for ANY math: addition, subtraction, multiplication, division, "
        "powers, percentages, parentheses. Input must be the expression only, "
        "for example: 125 * 12 or (15 + 27) * 3. "
        "Never compute numbers yourself."
    ),
    "now": (
        "Return the current date, time, weekday and timezone. "
        "Use it for any question about today's date, the current time, the day of week "
        "or a timezone (for example Europe/Moscow). Input is an optional timezone name."
    ),
    "lookup": (
        "Search the project knowledge base and return matching facts. "
        "Use it for questions about this project: which libraries it uses, which files exist, "
        "how to run it, which ports, environment variables, how tools and memory work. "
        "Input is a natural-language query."
    ),
}

TOOL_DESCRIPTIONS_RU: dict[str, str] = {
    "calculator": (
        "Вычисляет арифметическое выражение и возвращает точное число. "
        "Использовать для ЛЮБЫХ вычислений: сложение, вычитание, умножение, деление, "
        "степени, проценты, скобки. На вход подаётся только выражение, "
        "например: 125 * 12 или (15 + 27) * 3. "
        "Никогда не считай в уме самостоятельно."
    ),
    "now": (
        "Возвращает текущую дату, время, день недели и часовой пояс. "
        "Использовать для вопросов про сегодняшнюю дату, текущее время, день недели "
        "или часовой пояс (например, Europe/Moscow). На вход можно передать название пояса."
    ),
    "lookup": (
        "Ищет факты в базе знаний проекта и возвращает совпадения. "
        "Использовать для вопросов об этом проекте: какие библиотеки используются, какие есть файлы, "
        "как запускать, какие порты и переменные окружения, как устроены инструменты и память. "
        "На вход подаётся запрос на естественном языке."
    ),
}

TOOL_DESCRIPTIONS: dict[str, dict[str, str]] = {
    "en": TOOL_DESCRIPTIONS_EN,
    "ru": TOOL_DESCRIPTIONS_RU,
}

# Короткие подписи для консольного вывода агента.
ANSWERS: dict[str, dict[str, str]] = {
    "en": {
        "used_tool": "Used: {tool}",
        "args": "Arguments: {args}",
        "result": "Tool result: {result}",
        "no_tool": "No tool was needed for this question.",
        "unknown": "I could not match this question to any of the three tools.",
        "recall_empty": "There is no earlier dialogue in this session yet.",
        "recall": "Earlier in this session you asked:",
        "name_saved": "Got it, your name is {name}. I will remember it in this session.",
        "name_known": "Your name is {name} (remembered from earlier in this session).",
        "name_unknown": "You have not told me your name yet in this session.",
    },
    "ru": {
        "used_tool": "Использован инструмент: {tool}",
        "args": "Аргументы: {args}",
        "result": "Результат инструмента: {result}",
        "no_tool": "Инструмент для этого запроса не понадобился.",
        "unknown": "Не удалось сопоставить запрос ни с одним из трёх инструментов.",
        "recall_empty": "В этой сессии ещё нет предыдущих вопросов.",
        "recall": "Ранее в этой сессии вы спрашивали:",
        "name_saved": "Запомнил: ваше имя {name}. Сохраню его в этой сессии.",
        "name_known": "Ваше имя {name} (взято из памяти этой сессии).",
        "name_unknown": "В этой сессии вы ещё не называли своё имя.",
    },
}


def system_prompt(lang: str) -> str:
    return SYSTEM_PROMPTS.get(lang, SYSTEM_PROMPTS["ru"])


def tool_descriptions(lang: str) -> dict[str, str]:
    return TOOL_DESCRIPTIONS.get(lang, TOOL_DESCRIPTIONS["ru"])


def labels(lang: str) -> dict[str, str]:
    return ANSWERS.get(lang, ANSWERS["ru"])
