FROM python:3.12-slim
WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY api/pyproject.toml api/uv.lock* ./api/
COPY libs/ ./libs/

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_PROJECT_ENVIRONMENT=/app/.venv

RUN cd api && uv sync --frozen --no-dev

COPY api/ ./api/
COPY shared/ ./shared/

EXPOSE 8080
CMD ["/app/.venv/bin/uvicorn", "index:app", "--host", "0.0.0.0", "--port", "8080", "--app-dir", "/app/api"]
