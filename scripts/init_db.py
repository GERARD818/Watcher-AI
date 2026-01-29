import sys
import os

""""
Este script inicializa la base de datos creando las tablas necesarias
basadas en los modelos definidos en 'src/database/models.py'.
"""

# Esto añade la carpeta raíz al "camino" de Python para que encuentre 'src'
sys.path.append(os.getcwd())

from sqlmodel import SQLModel
from src.database.db import engine
from src.database.models import Camera, Detection

def init_db():
    print("Conectando a la base de datos...")
    
    # Esta línea es la magia:
    # Busca todas las clases que hereden de SQLModel y crea sus tablas en la DB
    SQLModel.metadata.create_all(engine)
    
    print("¡Tablas creadas con éxito! El sistema está listo.")

if __name__ == "__main__":
    init_db()