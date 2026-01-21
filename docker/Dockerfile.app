FROM python:3.11-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /code 

COPY pyproject.toml uv.lock ./

ENV VIRTUAL_ENV=/code/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN uv sync --frozen --no-install-project

COPY .env ./
COPY ./src ./src

CMD ["uvicorn", "src:app", "--host", "0.0.0.0", "--port", "5000", "--reload"]