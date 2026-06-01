from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(str(settings.DATABASE_URL))
with engine.connect() as conn:
    try:
        conn.execute(text("ALTER TABLE categorias_centros ADD COLUMN icono VARCHAR(20)"))
        conn.commit()
        print("Columna 'icono' agregada exitosamente")
    except Exception as e:
        print("Error (quizás ya existe):", e)
