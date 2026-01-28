FROM python:3.11-slim

# Dependencias mínimas para PostgreSQL y limpieza de caché para reducir tamaño
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY docker/requirements.txt ./requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

# Copiamos el código fuente
COPY . .

# Exponemos el puerto de FastAPI
EXPOSE 8000

# Ejecutamos con --reload para que los cambios se apliquen en vivo durante el desarrollo
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]