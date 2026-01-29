import os
import uuid
import redis
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from datetime import datetime
from .schemas import IngestResponse, RedisTask # Importamos los modelos


app = FastAPI(title="Watcher AI - API Ingest")

# Conexión a Redis usando la URL de las variables de entorno de Docker
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
redis_client = redis.from_url(REDIS_URL, decode_responses=True)


@app.post("/v1/ingest/frame", response_model=IngestResponse) # <--- 1. Validamos la respuesta
async def ingest_frame(
    camera_id: str = Form(..., min_length=3), # <--- 2. Validación extra en la entrada
    image: UploadFile = File(...)
):
    if not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="No es una imagen válida")

    event_id = str(uuid.uuid4())
    file_path = f"/app/data/uploads/{event_id}.jpg"
    current_time = datetime.now()

    # 1. Guardar la imagen físicamente
    with open(file_path, "wb") as buffer:
        buffer.write(await image.read())

    # 2. Crear el objeto de la tarea usando Pydantic
    # Si falta un campo o el tipo es incorrecto, fallará aquí mismo
    task = RedisTask(
        event_id=event_id,
        camera_id=camera_id,
        file_path=file_path,
        timestamp=current_time
    )

    # 3. Enviar a Redis (usamos .model_dump_json() que es nativo de Pydantic)
    redis_client.lpush("inference_queue", task.model_dump_json())
    
    # 4. Construir la respuesta final validada
    return IngestResponse(
        event_id=event_id,
        queue_position=redis_client.llen("inference_queue"),
        timestamp=current_time
    )