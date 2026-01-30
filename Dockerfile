FROM python:3.11-slim

# Dependencias del sistema:
# - libpq-dev y gcc: Para PostgreSQL (psycopg2)
# - libgl1-mesa-glx y libglib2.0-0: OBLIGATORIAS para que funcione YOLO/OpenCV
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

# Copiamos TODO el codigo fuente necesario (src, scripts y models)
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY models/ ./models/

# Comando por defecto (si no se especifica otro, arranca la API)
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]