from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class IngestResponse(BaseModel):
    """Modelo de respuesta para el cliente (Documentación Swagger)"""
    event_id: str
    status: str = Field(default="queued")
    queue_position: int
    timestamp: datetime

class RedisTask(BaseModel):
    """Modelo interno para la cola de Redis (Garantiza que el Worker reciba datos limpios)"""
    event_id: str
    camera_id: str
    file_path: str
    timestamp: datetime