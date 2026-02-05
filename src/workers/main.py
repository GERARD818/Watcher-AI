import json
import redis
import os
import sys
import time
# Importamos cv2 (OpenCV) para manejar el video
import cv2 
from ultralytics import YOLO
from sqlmodel import Session
from src.database.db import engine
from src.database.models import Detection

# --- CONFIGURACION ---
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
QUEUE_NAME = "image_queue"
MODEL_PATH = "models/best.pt"
# Definimos carpetas de entrada y salida
UPLOAD_DIR = "data/uploads"
PROCESSED_DIR = "data/processed"

# Asegurar que existen los directorios
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)

# Verificacion de seguridad del modelo
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
    print(f"[INFO] Worker REAL (Modo Streaming + Video Output) escuchando en '{QUEUE_NAME}'...")
    
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

                input_path = data.get("path")
                camera_id = data.get("camera_id")
                
                if not os.path.exists(input_path):
                    print(f"[WARN] Archivo no encontrado: {input_path}, saltando...")
                    continue

                # --- PREPARACION DEL VIDEO DE SALIDA ---
                # Definimos el nombre del archivo de salida (ej: video.mp4 -> video_labeled.mp4)
                filename = os.path.basename(input_path)
                name, ext = os.path.splitext(filename)
                output_filename = f"{name}_labeled.mp4"
                output_path = os.path.join(PROCESSED_DIR, output_filename)

                print(f"[INFO] Procesando: {input_path} (Cam {camera_id})")
                print(f"[INFO] Video resultante se guardará en: {output_path}")

                # Obtenemos propiedades del video original para crear el nuevo
                cap = cv2.VideoCapture(input_path)
                fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30 # Default a 30 si falla
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                cap.release() # Cerramos lectura

                # Configuramos el "escritor" de video
                # 'mp4v' es un códec estándar para .mp4
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                video_writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
                # ---------------------------------------


                # 2. INFERENCIA REAL CON STREAM=TRUE
                results = model.track(
                    input_path, 
                    persist=False, 
                    stream=True, 
                    verbose=False,
                    conf=0.1,  
                    iou=0.6,
                    max_det=100
                )

                detections_count = 0

                print(f"[INFO] Iniciando procesamiento frame a frame...")
                # 3. PROCESAR FRAME A FRAME
                for frame_idx, result in enumerate(results):
                    detections_in_frame = []
                    
                    # --- A. Procesar datos para DB ---
                    for box in result.boxes:
                        cls_id = int(box.cls[0])
                        label_name = model.names[cls_id] 
                        confidence_score = float(box.conf[0])
                        bbox = box.xywh[0].tolist()
                        track_id_val = int(box.id[0]) if box.id is not None else None

                        det = Detection(
                            label=label_name,
                            confidence=confidence_score,
                            metadata_json={"bbox": bbox, "frame": frame_idx},
                            track_id=track_id_val,
                            camera_id=camera_id
                        )
                        detections_in_frame.append(det)

                    # --- B. Guardar en DB ---
                    if detections_in_frame:
                        try:
                            with Session(engine) as session:
                                for d in detections_in_frame:
                                    session.add(d)
                                session.commit()
                            detections_count += len(detections_in_frame)
                        except Exception as e_db:
                            print(f"\n[ERROR DB] Fallo guardando frame {frame_idx}: {e_db}")

                    # --- C. Generar Frame de Video ---
                    # result.plot() devuelve una imagen de numpy con las cajas dibujadas
                    labeled_frame = result.plot()
                    # Escribimos esa imagen en nuestro archivo de video
                    video_writer.write(labeled_frame)

                    # Feedback visual en consola
                    if frame_idx % 15 == 0:
                        print(".", end="", flush=True)

                # IMPORTANTE: Cerrar el escritor de video al terminar para guardar el archivo
                video_writer.release()

                print(f"\n[SUCCESS] Finalizado. Total DB: {detections_count}. Video guardado: {output_path}")

        except Exception as e:
            print(f"\n[ERROR CRITICO] Error inesperado en el bucle: {e}")
            # Importante: Si falla algo, intentar cerrar el writer si quedó abierto
            try: video_writer.release()
            except: pass
            time.sleep(1) 

if __name__ == "__main__":
    process_job()