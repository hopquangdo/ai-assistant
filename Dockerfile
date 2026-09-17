# syntax=docker/dockerfile:1

FROM python:3.12-slim AS runner
WORKDIR /app

RUN groupadd -r chatbot && useradd -r -g chatbot chatbot \
    && apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
COPY package ./package
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src

USER chatbot
ENV APP_PORT=8000
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -fsS "http://127.0.0.1:${APP_PORT}/docs" || exit 1

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
