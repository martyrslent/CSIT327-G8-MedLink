# =========================
# Base image
# =========================
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install pipenv
RUN pip install --no-cache-dir pipenv

# Copy Pipfile (always required)
COPY Pipfile ./

# Copy Pipfile.lock if it exists
# (ignore missing file so build won’t fail)
COPY Pipfile.lock* ./

# Install dependencies
# - If lockfile exists → deterministic install
# - If not → install directly from Pipfile (skip lock)
RUN if [ -f Pipfile.lock ]; then \
        pipenv install --system --deploy --ignore-pipfile; \
    else \
        pipenv install --system --skip-lock; \
    fi

# Copy project files
COPY . .

# =========================
# Development (Django runserver)
# =========================
# CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# =========================
# Production (Gunicorn)
# =========================
CMD ["gunicorn", "medlink.wsgi:application", "--bind", "0.0.0.0:8000"]
