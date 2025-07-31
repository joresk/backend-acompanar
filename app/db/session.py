from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)
print("🔍 DATABASE_URL repr():", repr(DATABASE_URL))
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ✅ Esta función debe existir para que routes_auth.py la importe
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
