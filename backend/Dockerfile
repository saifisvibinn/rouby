FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev || uv sync --no-dev

COPY . .

RUN chmod +x /app/scripts/start.sh

ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000

CMD ["/app/scripts/start.sh"]

