# Fast development build using full Python image (has build tools pre-installed)

FROM python:3.13 as development

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV DEBIAN_FRONTEND=noninteractive

# Set work directory
WORKDIR /app

# Install only postgresql-client (build tools already in python:3.13)
RUN apt-get update && apt-get install -y postgresql-client && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry

# Configure poetry
RUN poetry config virtualenvs.create false

# Copy dependency files first (for better Docker layer caching)
COPY pyproject.toml poetry.lock* ./

# Install dependencies (this layer will be cached)
RUN poetry install --no-root

# Copy application code
COPY . .

# Install application in development mode
RUN poetry install

# Expose port
EXPOSE 8000

# Default command for development
CMD ["poetry", "run", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]