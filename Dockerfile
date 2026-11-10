FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .
COPY data/seed_news.csv /app/data/seed_news.csv

RUN mkdir -p /app/vector_wealth_db

ENV PYTHONUNBUFFERED=1
ENV VECTOR_WEALTH_DB_PATH=/app/vector_wealth_db

EXPOSE 10000

CMD ["gunicorn", "main:app", "-w", "1", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:10000", "--timeout", "120"]
