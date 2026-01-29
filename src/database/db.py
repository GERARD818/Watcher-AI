import os
from sqlmodel import create_engine, Session

# 1. LA URL DE CONEXIÓN
# Estructura: postgresql://USUARIO:CONTRASEÑA@HOST:PUERTO/NOMBRE_DB
# Nota: Usamos 'localhost' porque estamos probando desde nuestra computadora hacia Docker. Si definimos la variable de entorno
# de la URL de la base de datos a la URL de otro revidor entonces se podría cambiar el host.
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://user:password@localhost:5432/watcher_db"
)

# 2. EL MOTOR
# echo=True muestra todo lo que va pasando en el terminal para depuración
engine = create_engine(DATABASE_URL, echo=True)

# 3. EL GENERADOR DE SESIONES
def get_session():
    """Esta función abre una conexión, te la presta y la cierra al terminar"""
    with Session(engine) as session:
        yield session   