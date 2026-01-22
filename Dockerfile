# Use SPECIFIC tag to avoid cache issues
FROM python:3.11.7-slim-bookworm

WORKDIR /app

# Prevent Python from writing pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Copy requirements FIRST (for Docker layer caching)
COPY requirements.txt .

# Install dependencies with NO cache and binary wheels only
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --only-binary :all: -r requirements.txt || \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Verify critical dependencies on build
RUN python -c "import telegram; import ccxt; import psycopg2; print('✅ All dependencies OK')"

# Run the bot
CMD ["python", "-m", "bot.main"]
