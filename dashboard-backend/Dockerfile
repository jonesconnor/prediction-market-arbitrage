# syntax=docker/dockerfile:1

FROM python:3.13-slim AS base
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
WORKDIR /app


FROM base AS builder
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment for isolated dependency installation
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install project dependencies
COPY pyproject.toml uv.lock ./
COPY README.md ./
COPY dashboard_backend ./dashboard_backend
COPY main.py ./
RUN pip install --upgrade pip \
    && pip install --no-cache-dir .


FROM base AS runtime
ENV PATH="/opt/venv/bin:$PATH"
COPY --from=builder /opt/venv /opt/venv

# Copy application source (helpful for hotfixes & stack traces)
COPY dashboard_backend ./dashboard_backend
COPY main.py ./

EXPOSE 8000
CMD ["uvicorn", "dashboard_backend.app:app", "--host", "0.0.0.0", "--port", "8000"]
