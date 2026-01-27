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

# 🔍 DIAGNOSTIC: Verify adjust_links.json file is present
RUN echo "============================================================" && \
    echo "🔍 VERIFYING ADJUST LINKS FILE IN DOCKER IMAGE" && \
    echo "============================================================" && \
    ls -la /app/ && \
    echo "------------------------------------------------------------" && \
    ls -la /app/data/ && \
    echo "------------------------------------------------------------" && \
    if [ -f "/app/data/adjust_links.json" ]; then \
        echo "✅ adjust_links.json FOUND"; \
        echo "📄 File size: $(stat -f%z /app/data/adjust_links.json 2>/dev/null || stat --format=%s /app/data/adjust_links.json) bytes"; \
        echo "📋 First 3 lines:"; \
        head -n 3 /app/data/adjust_links.json; \
    else \
        echo "❌ WARNING: adjust_links.json NOT FOUND!"; \
        echo "⚠️  Alerts will NOT have adjust deeplinks!"; \
    fi && \
    echo "============================================================"

# Verify critical dependencies on build
RUN python -c "import telegram; import ccxt; import psycopg2; print('✅ All dependencies OK')"

# 🔍 DIAGNOSTIC: Test adjust_links module load during build
RUN python -c "from bot.services import adjust_links; print('✅ Adjust links module loads successfully')" || \
    echo "⚠️  WARNING: adjust_links module load test failed"

# Run the bot
CMD ["python", "-m", "bot.main"]
