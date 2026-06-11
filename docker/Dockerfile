FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --no-cache-dir -e . && playwright install chromium && playwright install-deps chromium

COPY core/ ./core/
COPY scraper/ ./scraper/
COPY bot/ ./bot/

CMD ["python", "-m", "scraper.runner"]
