# syntax=docker/dockerfile:1

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Зависимости отдельным слоем: пересобираются только при изменении requirements.
# INSTALL_LLM=0 — собрать лёгкий образ только для mock-режима (без LangGraph и Ollama).
ARG INSTALL_LLM=1
COPY requirements.txt ./
RUN if [ "$INSTALL_LLM" = "1" ]; then pip install --no-cache-dir -r requirements.txt; fi

# Код и данные
COPY app ./app
COPY data ./data

# Пользователь без прав root
RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/logs /app/data \
    && chown -R appuser:appuser /app

USER appuser

# Значения по умолчанию: mock-режим, русские промпты, московское время.
# Реальные значения приходят из --env-file .env или docker compose.
ENV LLM_PROVIDER=mock \
    PROMPT_LANG=ru \
    APP_TIMEZONE=Europe/Moscow

# Примеры:
#   docker run --rm agent-3-tools "Сколько будет 125 * 12?"
#   docker run --rm -it agent-3-tools
ENTRYPOINT ["python", "-m", "app"]
