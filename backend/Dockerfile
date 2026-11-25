FROM python:3.11-slim as builder

WORKDIR /app
RUN pip install --no-cache-dir uv
COPY requirements.txt .
RUN uv pip install --system --no-cache -r requirements.txt

FROM python:3.11-slim

WORKDIR /app
RUN useradd -m -u 1000 appuser
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --chown=appuser:appuser app/ ./app

USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8000/health', timeout=5)" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
