FROM python:3.12-slim
WORKDIR /app
COPY requirements.lock.txt .
RUN pip install --no-cache-dir -r requirements.lock.txt
COPY app ./app
RUN useradd --create-home manaco
USER manaco
CMD ["sh", "-c", "python -m app.inicializar_bd && uvicorn app.principal:app --host 0.0.0.0 --port ${PORT:-8000}"]
