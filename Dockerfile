# ──────────────────────────── Stage 1: Build Frontend ────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
# The vite config outputs to '../backend/static'
RUN npm run build

# ──────────────────────────── Stage 2: Serve Backend + Static ────────────────────────────
FROM python:3.11-slim

WORKDIR /app/backend

# Copy backend requirements and install
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ .

# Copy built frontend static files from the builder stage
COPY --from=builder /app/backend/static /app/backend/static

# Expose the application port
EXPOSE 8000

# Start the FastAPI server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
