FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y libcurl4-openssl-dev libssl-dev libxml2-dev libxslt1-dev libjpeg-dev zlib1g-dev libpng-dev libpango-1.0-0 libcairo2 libasound2 --no-install-recommends && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install playwright && playwright install --with-deps chromium
COPY . .
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
