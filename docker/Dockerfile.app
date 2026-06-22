FROM python:3.11-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /code

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/code/.venv \
    PATH="/code/.venv/bin:$PATH"

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-install-project

COPY ./src ./src

# Drop privileges: the app never needs root.
RUN useradd --create-home --uid 10001 appuser
USER appuser

# Production launch command. Notes:
#  - No --reload: that is a dev-only feature (single worker + file watcher).
#    Hot reload for local work lives in docker-compose.dev.yaml instead.
#  - Stay at a single worker for now: ConnectionManager keeps live
#    WebSockets in an in-process dict, so multiple workers would route
#    messages to the wrong process. Scaling out needs a Redis pub/sub
#    backplane first.
#  - --proxy-headers + --forwarded-allow-ips=* let the app see the real
#    client IP and scheme from Caddy's X-Forwarded-* headers. This is safe
#    ONLY because the published port is bound to 127.0.0.1 (see the compose
#    files), so nothing but the local reverse proxy / Tor can reach it.
#  - --limit-concurrency sheds load (503) instead of unbounded queueing.
#  - --timeout-keep-alive trims idle keep-alive sockets (slowloris).
CMD ["uvicorn", "src:app", "--host", "0.0.0.0", "--port", "5000", \
     "--proxy-headers", "--forwarded-allow-ips", "*", \
     "--limit-concurrency", "200", "--timeout-keep-alive", "5"]
