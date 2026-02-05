FROM python:3.11-slim

# 1. Dependencias del sistema
# libpq-dev/gcc -> Postgres | libgl1/libglib2.0-0 -> OpenCV (Imprescindible para IA)
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 2. Instalación de librerías (Caché eficiente)
# Nota: Aquí vuestro requirements debe incluir: ultralytics, sqlmodel, psycopg2-binary, redis
COPY docker/worker_requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 3. Copia selectiva del código (Estrategia Híbrida)
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY models/ ./models/

# Definimos el PYTHONPATH para que encuentre el módulo 'src' desde la raíz
ENV PYTHONPATH=/app

# El comando por defecto es el worker, pero lo sobreescribiremos en el compose 
# para incluir la inicialización de la DB
CMD ["python", "src/workers/main.py"]