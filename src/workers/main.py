import json
import redis
import os
import sys
from ultralytics import YOLO
from sqlmodel import Session
from src.database.db import engine
from src.database.models import Detection

# --- CONFIGURACION ---
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
QUEUE_NAME = "image_queue"
MODEL_PATH = "models/best.pt"

# Verificacion de seguridad
if not os.path.exists(MODEL_PATH):
    print(f"[ERROR] No encuentro el modelo en {MODEL_PATH}")
    print("   -> Asegurate de descargar 'best.pt' y ponerlo en la carpeta 'models/'")
    sys.exit(1)

print(f"[INFO] Cargando modelo YOLOv11 desde {MODEL_PATH}...")
try:
    model = YOLO(MODEL_PATH)
    print("[INFO] Modelo cargado y listo para inferencia.")
except Exception as e:
    print(f"[ERROR] Fallo cargando YOLO: {e}")
    sys.exit(1)

# Conexion a Redis
try:
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)
except Exception as e:
    print(f"[ERROR] Fallo conectando a Redis: {e}")
    sys.exit(1)

def process_job():
    print(f"[INFO] Worker REAL escuchando en '{QUEUE_NAME}'...")
    
    while True:
        # 1. Esperar mensaje de Redis (bloqueante)
        job = r.blpop(QUEUE_NAME, timeout=0) 
        
        if job:
            queue, data_str = job
            # --- BLOQUE DE SEGURIDAD ---
            try:
                data = json.loads(data_str)
            except json.JSONDecodeError as e:
                print(f"[ERROR] JSON corrupto recibido: {data_str}")
                print(f"       -> Motivo: {e}")
                continue # Saltamos al siguiente mensaje sin crashear
            # ---------------------------            
            image_path = data.get("path")
            camera_id = data.get("camera_id")
            
            if not os.path.exists(image_path):
                print(f"[WARN] Archivo no encontrado: {image_path}, saltando...")
                continue

            print(f"[INFO] Procesando: {image_path} (Cam {camera_id})")

            # 2. INFERENCIA REAL CON YOLO
            # usamos 'track' para activar el rastreo y obtener IDs
            # persist=True ayuda a recordar objetos si es un video continuo
            results = model.track(image_path, persist=True, verbose=False)

            # 3. Guardar resultados en DB
            detections_to_save = []
            
            # YOLO puede devolver varios resultados, iteramos sobre cada objeto detectado
            for result in results:
                for box in result.boxes:
                    # Extraccion de datos
                    cls_id = int(box.cls[0])
                    label_name = model.names[cls_id] 
                    confidence_score = float(box.conf[0])
                    
                    # Coordenadas de la caja (bounding box)
                    bbox = box.xywh[0].tolist() # [x, y, ancho, alto]
                    
                    # ID del Tracking (Si YOLO lo ha perdido, devuelve None)
                    track_id_val = int(box.id[0]) if box.id is not None else None

                    # Creamos el objeto para la DB
                    det = Detection(
                        label=label_name,
                        confidence=confidence_score,
                        metadata_json={"bbox": bbox},
                        track_id=track_id_val,
                        camera_id=camera_id
                    )
                    detections_to_save.append(det)

            # 4. Commit a la base de datos
            if detections_to_save:
                try:
                    with Session(engine) as session:
                        for d in detections_to_save:
                            session.add(d)
                        session.commit()
                    print(f"[SUCCESS] Guardadas {len(detections_to_save)} detecciones en DB.")
                except Exception as e:
                    print(f"[ERROR] Fallo guardando en SQL: {e}")
            else:
                print("[INFO] Imagen limpia (YOLO no detecto nada).")

if __name__ == "__main__":
    process_job()