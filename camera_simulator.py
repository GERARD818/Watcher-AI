import requests
import time
import os

# Configuración
API_URL = "http://localhost:8000/v1/ingest/frame"
CAMERA_ID = "CAM-NORTH-01"
IMAGE_PATH = "test_image.jpg"  # Asegúrate de tener una imagen aquí

def send_frame():
    if not os.path.exists(IMAGE_PATH):
        print(f"Error: No se encuentra la imagen {IMAGE_PATH}")
        return

    with open(IMAGE_PATH, "rb") as f:
        files = {"image": (IMAGE_PATH, f, "image/jpeg")}
        data = {"camera_id": CAMERA_ID}
        
        try:
            response = requests.post(API_URL, files=files, data=data)
            print(f"Status: {response.status_code} | Response: {response.json()}")
        except Exception as e:
            print(f"Error conectando con la API: {e}")

if __name__ == "__main__":
    print("Iniciando simulador de Watcher AI...")
    while True:
        send_frame()
        time.sleep(5)  # Envía un frame cada 5 segundos