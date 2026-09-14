FROM python:3.12-slim

WORKDIR /app

# Install system dependencies including curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/app
RUN useradd -r -M -d /app -s /usr/sbin/nologin appuser && chown -R appuser:appuser /app

USER appuser

EXPOSE 5555
CMD ["sh", "/app/scripts/docker-start.sh"]
