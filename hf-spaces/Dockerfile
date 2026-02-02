# HF Spaces Dockerfile - 1proxy Backend
FROM python:3.12

WORKDIR /app

# Copy everything at once to reduce layers
COPY hf-spaces/requirements.txt .
COPY 1proxy-backend/ ./1proxy-backend/

# Install dependencies
RUN pip install --no-cache-dir -r hf-spaces/requirements.txt

# Create data directory
RUN mkdir -p /app/data

EXPOSE 7860

ENV PYTHONPATH=/app
ENV PORT=7860
ENV HOST=0.0.0.0

CMD python -m uvicorn 1proxy-backend.app.main:app --host 0.0.0.0 --port 7860
