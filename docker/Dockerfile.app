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
#  - --proxy-headers + --forwarded-allow-ips=127.0.0.1 let the app see the real
#    client IP and scheme from Caddy's X-Forwarded-* headers, but ONLY when the
#    immediate peer is the local proxy / Tor daemon. Trusting "*" would let any
#    direct client spoof X-Forwarded-For (and thus the per-IP rate limiter) if
#    the port were ever exposed; pinning to loopback removes that footgun.
#  - --limit-concurrency sheds load (503) instead of unbounded queueing.
#  - --timeout-keep-alive trims idle keep-alive sockets (slowloris).
#  - --no-server-header: suppress Uvicorn's Server header so the app middleware
#    is the sole source of a generic one (no software/version advertised).
CMD ["uvicorn", "src:app", "--host", "0.0.0.0", "--port", "5000", \
     "--proxy-headers", "--forwarded-allow-ips", "127.0.0.1", \
     "--no-server-header", \
     "--limit-concurrency", "200", "--timeout-keep-alive", "5"]
