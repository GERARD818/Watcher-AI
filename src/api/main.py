import os
import uuid
import redis
import json
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from datetime import datetime

app = FastAPI(title="Watcher AI - API Ingest")

# Conexión a Redis usando la URL de las variables de entorno de Docker
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

@app.post("/v1/ingest/frame")
async def ingest_frame(
    camera_id: str = Form(...),
    image: UploadFile = File(...)
):
    if not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="No es una imagen válida")

    event_id = str(uuid.uuid4())
    
    # 1. Guardar la imagen físicamente
    # Para que el Worker pueda leerla, la guardamos en una carpeta compartida
    file_path = f"/app/data/uploads/{event_id}.jpg"
    with open(file_path, "wb") as buffer:
        buffer.write(await image.read())

    # 2. Crear el mensaje para la cola
    task_data = {
        "event_id": event_id,
        "camera_id": camera_id,
        "file_path": file_path,
        "timestamp": datetime.now().isoformat()
    }

    # 3. Purgar a la cola de Redis (LPUSH actúa como una cola)
    redis_client.lpush("inference_queue", json.dumps(task_data))
    
    return {
        "event_id": event_id,
        "status": "queued",
        "queue_position": redis_client.llen("inference_queue")
    }