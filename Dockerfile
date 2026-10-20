FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.lock.txt .
RUN pip install --no-cache-dir -r requirements.lock.txt
COPY backend/app ./app
COPY backend/modelos_ia ./modelos_ia
ENV KERAS_BACKEND=tensorflow TF_CPP_MIN_LOG_LEVEL=2 TF_NUM_INTRAOP_THREADS=2 TF_NUM_INTEROP_THREADS=1 OMP_NUM_THREADS=2 PYTHONUNBUFFERED=1
RUN useradd --create-home manaco
USER manaco
CMD ["sh", "-c", "python -m app.inicializar_bd && uvicorn app.principal:app --host 0.0.0.0 --port ${PORT:-8000}"]
