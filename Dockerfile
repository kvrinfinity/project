# Stage 1: Build stage
FROM python:3.11-slim as builder

WORKDIR /app

COPY requirements.txt .
RUN apt-get update && apt-get install -y --no-install-recommends build-essential gcc \
    && pip install --upgrade pip \
    && pip install --prefix=/install -r requirements.txt \
    && apt-get purge -y --auto-remove build-essential gcc \
    && rm -rf /root/.cache /var/lib/apt/lists/*

# Stage 2: Minimal runtime image
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY --from=builder /install /usr/local
COPY . .

EXPOSE 5000

CMD ["python", "app.py"]
