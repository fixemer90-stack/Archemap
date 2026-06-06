FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for pyswisseph + WeasyPrint PDF rendering
RUN apt-get update && apt-get install -y \
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

# Install Python dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[dev]"

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
