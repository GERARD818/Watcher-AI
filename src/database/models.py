from typing import Optional, List, Dict
from datetime import datetime
import uuid
from sqlmodel import SQLModel, Field, Relationship, Column, JSON

# ==========================================
# TABLA 1: CÁMARAS
# ==========================================
class Camera(SQLModel, table=True):
    # primary_key=True: Es el DNI único de la cámara
    id: Optional[int] = Field(default=None, primary_key=True)
    
    location: str          # Ej: "Entrada Norte"
    status: str = "active" # Ej: "active", "offline"
    
    # RELACIÓN:
    # Esto no crea una columna en la base de datos, es para Python.
    # Permite hacer: mi_camara.detections y ver todas sus alertas.
    detections: List["Detection"] = Relationship(back_populates="camera")


# ==========================================
# TABLA 2: DETECCIONES (La importante)
# ==========================================
class Detection(SQLModel, table=True):
    # Usamos UUID en lugar de 1, 2, 3... es más seguro para sistemas grandes
    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True)
    
    # index=True hace que las búsquedas por fecha sean rapidísimas
    timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)
    
    label: str = Field(index=True) # Ej: "helmet", "person"
    confidence: float              # Ej: 0.95 (95% seguro)
    
    # COLUMNA JSONB:
    # Aquí guardamos datos flexibles como las coordenadas [x, y, w, h]
    # sa_column=Column(JSON) le dice a Postgres que use formato JSON real
    metadata_json: Dict = Field(default={}, sa_column=Column(JSON))
    
    # FOREIGN KEY (El Vínculo):
    # Aquí guardamos el ID de la cámara que vio esto.
    camera_id: Optional[int] = Field(default=None, foreign_key="camera.id")
    
    # RELACIÓN INVERSA:
    # Permite hacer: mi_deteccion.camera y saber dónde ocurrió.
    camera: Optional[Camera] = Relationship(back_populates="detections")