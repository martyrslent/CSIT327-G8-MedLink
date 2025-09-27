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

# Copy Pipfile.lock if it exists (ignore if missing)
COPY Pipfile.lock* ./

# Install dependencies
RUN if [ -f Pipfile.lock ]; then \
        pipenv install --system --deploy --ignore-pipfile; \
    else \
        pipenv install --system --skip-lock; \
    fi

# Copy project files
COPY . .

# Collect static files at build time
RUN python manage.py collectstatic --noinput

# =========================
# Development (Django runserver)
# =========================
# CMD ["python", "manage.py", "runserver", "0.0.0.0:8001"]

# =========================
# Production (Gunicorn + WhiteNoise)
# =========================
CMD ["gunicorn", "medlink.wsgi:application", "--bind", "0.0.0.0:8001"]
