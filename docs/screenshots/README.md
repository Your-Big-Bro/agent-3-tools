# Скриншоты запусков

Подтверждение работы проекта: демо в двух режимах, журнал запусков и трейсы LangSmith.

| Файл | Что показывает |
|---|---|
| `01-demo-console.png` | `python -m app --demo` на Ollama: 7 запросов, у каждого видна строка `tool=...` (calculator, now, lookup) и работа памяти (имя «Дима» воспроизведено на шаге 5) |
| `02-runs-jsonl.png` | записи из `logs/runs.jsonl`: поля `question`, `tool`, `tool_args`, `tool_result`, `answer`, `duration_ms` |
| `03-langsmith-trace.png` | трейсы в LangSmith (проект `agent-3-tools`): чистая история из 7 запусков, раскрыт вызов `lookup` с аргументом `query: Docker` |
| `04-docker-run.png` | `docker run --rm agent-3-tools --demo`: контейнер работает автономно, в mock-режиме, журнал пишется в `/app/logs/runs.jsonl` |

Время съёмки - 12.11.2026, модель `qwen2.5:3b-instruct`, образ `agent-3-tools:latest` (278 МБ).
