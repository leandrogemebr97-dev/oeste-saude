FROM python:3.12-slim

WORKDIR /app

# Instala dependências do sistema para pdfplumber e playwright
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

EXPOSE 8001

CMD ["sh", "-c", "gunicorn main:app -w 2 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:${PORT:-8001}"]
