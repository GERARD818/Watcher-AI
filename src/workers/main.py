import json
import redis
import os
import sys
import time
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
    sys.exit(1)

print(f"[INFO] Cargando modelo YOLOv11 desde {MODEL_PATH}...")
try:
    model = YOLO(MODEL_PATH)
    print("[INFO] Modelo cargado y listo para inferencia.")
except Exception as e:
    print(f"[ERROR] Fallo cargando YOLO: {e}")
    sys.exit(1)

# Conexion a Redis con reintentos
r = None
while r is None:
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)
        r.ping() 
        print("[INFO] Conectado a Redis exitosamente.")
    except Exception as e:
        print(f"[WARN] Redis no listo, reintentando en 2s... ({e})")
        time.sleep(2)

def process_job():
    print(f"[INFO] Worker REAL (Modo Streaming) escuchando en '{QUEUE_NAME}'...")
    
    while True:
        try:
            # 1. Esperar mensaje de Redis (bloqueante)
            job = r.blpop(QUEUE_NAME, timeout=0) 
            
            if job:
                queue, data_str = job
                
                # --- BLOQUE DE SEGURIDAD JSON ---
                try:
                    data = json.loads(data_str)
                except json.JSONDecodeError as e:
                    print(f"[ERROR] JSON corrupto recibido e ignorado: {data_str}")
                    continue 
                # --------------------------------

                image_path = data.get("path")
                camera_id = data.get("camera_id")
                
                if not os.path.exists(image_path):
                    print(f"[WARN] Archivo no encontrado: {image_path}, saltando...")
                    continue

                print(f"[INFO] Procesando video/imagen: {image_path} (Cam {camera_id})")

                # 2. INFERENCIA REAL CON STREAM=TRUE
                # Esto devuelve un generador, no una lista. No ocupa RAM extra.
                results = model.track(image_path, persist=True, stream=True, verbose=False)

                detections_count = 0

                # 3. PROCESAR FRAME A FRAME
                # Al usar el bucle for sobre 'results' con stream=True, procesamos en tiempo real
                for frame_idx, result in enumerate(results):
                    detections_in_frame = []
                    
                    for box in result.boxes:
                        cls_id = int(box.cls[0])
                        label_name = model.names[cls_id] 
                        confidence_score = float(box.conf[0])
                        bbox = box.xywh[0].tolist()
                        track_id_val = int(box.id[0]) if box.id is not None else None

                        det = Detection(
                            label=label_name,
                            confidence=confidence_score,
                            metadata_json={"bbox": bbox, "frame": frame_idx}, # Agregamos el frame exacto
                            track_id=track_id_val,
                            camera_id=camera_id
                        )
                        detections_in_frame.append(det)

                    # 4. GUARDAR EN DB INMEDIATAMENTE (FRAME ACTUAL)
                    if detections_in_frame:
                        try:
                            with Session(engine) as session:
                                for d in detections_in_frame:
                                    session.add(d)
                                session.commit()
                            
                            detections_count += len(detections_in_frame)
                            # Feedback visual: imprime un punto cada 10 frames para saber que vive
                            if frame_idx % 10 == 0:
                                print(".", end="", flush=True)

                        except Exception as e_db:
                            print(f"\n[ERROR DB] Fallo guardando frame {frame_idx}: {e_db}")

                print(f"\n[SUCCESS] Finalizado. Total detectado: {detections_count} objetos.")

        except Exception as e:
            print(f"\n[ERROR CRITICO] Error inesperado en el bucle: {e}")
            time.sleep(1) 

if __name__ == "__main__":
    process_job()