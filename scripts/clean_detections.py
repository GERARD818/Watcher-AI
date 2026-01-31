import sys
import os

# Añadimos la ruta raíz al path para encontrar 'src'
sys.path.append(os.getcwd())

from sqlmodel import Session, text
from src.database.db import engine

def clean_detections():
    print("🧹 Limpiando tabla 'detection'...")
    try:
        with Session(engine) as session:
            # Usamos TRUNCATE porque es mucho más rápido que DELETE
            session.exec(text("TRUNCATE TABLE detection"))
            session.commit()
        print("✨ ¡Listo! La tabla de detecciones está vacía.")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    clean_detections()