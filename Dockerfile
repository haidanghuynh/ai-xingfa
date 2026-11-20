# syntax=docker/dockerfile:1
# Build giao dien React truoc
FROM node:22-alpine AS web
WORKDIR /build/web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

# Runtime Python
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    XFCAD_HOME=/app

WORKDIR /app

COPY requirements.txt pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir -e .

COPY config ./config
COPY data ./data
COPY static ./static
COPY --from=web /build/web/dist ./web/dist

RUN mkdir -p /app/out
VOLUME ["/app/out"]

EXPOSE 8010
CMD ["python", "-m", "xingfacad", "serve", "--host", "0.0.0.0", "--port", "8010"]
