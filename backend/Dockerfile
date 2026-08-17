# TipJar Backend — FastAPI + Tesseract OCR (Hetzner, 4GB optimiert)
FROM python:3.11-slim

WORKDIR /app

# System-Deps: Tesseract-Binary (deu+eng) für die LLM-freie OCR + Pillow-Libs
RUN apt-get update && apt-get install -y --no-install-recommends \
        tesseract-ocr tesseract-ocr-deu tesseract-ocr-eng \
        libjpeg62-turbo zlib1g \
    && rm -rf /var/lib/apt/lists/*

# Python-Deps zuerst (Layer-Cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Speicherschonend: 1 Worker (Tesseract wird lazy im Request geladen, kein Preload).
# Malloc-Trimming reduziert RSS-Spitzen nach OCR-Operationen -> kein OOM.
ENV MALLOC_ARENA_MAX=2 \
    PYTHONUNBUFFERED=1 \
    OMP_THREAD_LIMIT=1

EXPOSE 8001

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "1"]
