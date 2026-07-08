# ── Stage 1: Build frontend ─────────────────────────────────────────
FROM node:20-slim AS frontend-build

WORKDIR /app/frontend

# Install dependencies
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

# Build frontend
COPY frontend/ ./
RUN npm run build


# ── Stage 2: Backend ────────────────────────────────────────────────
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies (for PyMuPDF, Pillow, optional Tesseract)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/pyproject.toml ./
COPY backend/app/ ./app/
RUN pip install --no-cache-dir -e .

# Copy built frontend from stage 1
COPY --from=frontend-build /app/frontend/dist ./app/static/

# Create data directory
RUN mkdir -p /app/data/uploads /app/data/output /app/data/jobs

# Environment variables
ENV APP_SERVER_PORT=8000
ENV APP_DATA_DIR=/app/data

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
