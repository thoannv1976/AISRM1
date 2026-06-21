# AISRM1 worker (document/AI background tasks) — shares the api package
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY apps/api/pyproject.toml /app/pyproject.toml
RUN pip install --upgrade pip && pip install ".[documents,ai]" redis

COPY apps/api /app

RUN useradd -m -u 10001 appuser && chown -R appuser:appuser /app
USER appuser

CMD ["python", "-m", "app.worker"]
