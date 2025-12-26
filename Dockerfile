# Production image: Gunicorn serves Flask app, NGINX runs separately in docker-compose

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps (tail for /get-log; certificates for outbound HTTPS)
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first for better layer caching
COPY pyproject.toml README.md LICENSE ./
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir gunicorn \
    && python -m pip install --no-cache-dir .

# Copy application source
COPY . .

# Persistent data directory (SQLite DB + logs)
RUN mkdir -p /data

EXPOSE 8000

# Gunicorn settings can be tuned via env vars
ENV GUNICORN_BIND=0.0.0.0:8000 \
    GUNICORN_WORKERS=2 \
    GUNICORN_THREADS=4 \
    GUNICORN_TIMEOUT=60

CMD ["sh", "-lc", "gunicorn --bind ${GUNICORN_BIND} --workers ${GUNICORN_WORKERS} --threads ${GUNICORN_THREADS} --worker-class gthread --timeout ${GUNICORN_TIMEOUT} cdx_web_scan:app"]
