from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from datetime import datetime
import uuid

app = FastAPI(title="Watcher AI - API Ingest")

@app.get("/health")
def health_check():
    return {"status": "online", "timestamp": datetime.now()}

@app.post("/v1/ingest/frame")
async def ingest_frame(
    camera_id: str = Form(...),
    image: UploadFile = File(...)
):
    # 1. Validar que es una imagen
    if not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="El archivo enviado no es una imagen")

    # 2. Generar un ID único para el evento
    event_id = str(uuid.uuid4())
    
    # 3. Leer el contenido (aquí es donde luego lo mandaríamos a Redis)
    # contenido = await image.read()

    # TODO: Enviar metadatos a PostgreSQL y la imagen a la cola de Redis
    
    return {
        "event_id": event_id,
        "camera_id": camera_id,
        "filename": image.filename,
        "status": "queued_for_inference"
    }