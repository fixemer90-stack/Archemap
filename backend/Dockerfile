FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System dependencies for asyncpg builds, pyswisseph, healthchecks, and WeasyPrint PDF rendering.
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    g++ \
    python3-dev \
    libcairo2 \
    libffi-dev \
    libgdk-pixbuf-2.0-0 \
    libglib2.0-0 \
    libharfbuzz-subset0 \
    libharfbuzz0b \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    shared-mime-info \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
RUN python -m pip install --upgrade "pip>=26.1.2" \
    && pip install -e "."

COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app
COPY workers ./workers

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
