FROM python:3.12-slim
WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY api/pyproject.toml api/uv.lock* ./api/
COPY libs/ ./libs/
RUN cd api && uv sync --frozen --no-dev

COPY api/ ./api/
COPY shared/ ./shared/

EXPOSE 8080
CMD ["uv", "run", "--directory", "api", "uvicorn", "index:app", "--host", "0.0.0.0", "--port", "8080"]
