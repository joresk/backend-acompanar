import sys
import os

backend_dir = r"f:\0- Acompañar\Acompaniar-bf\backend-acompanar"
sys.path.append(backend_dir)

from app.db.session import engine, SessionLocal
from app.db.base import Base
from app.api.routes_faq import seed_faqs

# 1. Crear las tablas si no existen en la base de datos PostgreSQL
Base.metadata.create_all(bind=engine)
print("Tables created/verified.")

# 2. Ejecutar la función seed
db = SessionLocal()
try:
    result = seed_faqs(db)
    print("Seed result:", result)
except Exception as e:
    print("Error during seed:", e)
finally:
    db.close()
