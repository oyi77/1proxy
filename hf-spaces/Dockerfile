# HF Spaces Dockerfile - 1proxy Backend
# Completely rewritten for HF Spaces deployment
FROM python:3.12-slim

WORKDIR /app

# Install dependencies first (better caching)
COPY hf-spaces/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Copy application code
COPY 1proxy-backend/ /app/1proxy-backend/

# Create data directory
RUN mkdir -p /app/data && chmod 777 /app/data

EXPOSE 7860

ENV PYTHONPATH=/app
ENV PORT=7860
ENV HOST=0.0.0.0

CMD ["python", "-m", "uvicorn", "1proxy-backend.app.main:app", "--host", "0.0.0.0", "--port", "7860"]
