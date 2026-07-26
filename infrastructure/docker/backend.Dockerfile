FROM python:3.12-slim AS base

COPY --from=ghcr.io/astral-sh/uv:0.11.32 /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

FROM base AS dependencies

COPY pyproject.toml ./pyproject.toml
COPY apps/backend/pyproject.toml ./apps/backend/pyproject.toml
COPY packages/common/pyproject.toml ./packages/common/pyproject.toml
COPY packages/common/src ./packages/common/src

RUN uv sync --locked --no-dev --package ecoloop-backend --no-install-package ecoloop-backend

FROM base AS runtime

RUN groupadd --gid 10001 app \
    && useradd --uid 10001 --gid 10001 --create-home --shell /usr/sbin/nologin app

COPY --from=dependencies /app/.venv /app/.venv
COPY pyproject.toml ./pyproject.toml
COPY apps/backend ./apps/backend
COPY packages/common ./packages/common

RUN uv sync --locked --no-dev --package ecoloop-backend

ENV PATH="/app/.venv/bin:$PATH"

USER app

EXPOSE 8000

CMD ["uv", "run", "--no-sync", "--package", "ecoloop-backend", "ecoloop-backend"]
