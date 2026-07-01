# ── Stage 1: build the React/Vite frontend ────────────────────────────────────
FROM node:20-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build      # -> /app/frontend/dist

# ── Stage 2: Python runtime ───────────────────────────────────────────────────
FROM python:3.12-slim
WORKDIR /app

# scikit-learn / numpy / scipy ship manylinux wheels, so no build toolchain needed.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# App code (frontend/ source is ignored via .dockerignore; only dist is copied below).
COPY . .
COPY --from=frontend /app/frontend/dist ./frontend/dist

# The pipeline caches the historical dataset here; keep it on a writable path.
ENV WC_CACHE_DIR=/tmp
ENV PORT=8000
EXPOSE 8000

# Shell form so ${PORT} (injected by Render/Railway/Fly) is expanded.
CMD uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}
