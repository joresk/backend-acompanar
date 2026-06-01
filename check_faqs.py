import sys
import os

backend_dir = r"f:\0- Acompañar\Acompaniar-bf\backend-acompanar"
sys.path.append(backend_dir)

from app.db.session import SessionLocal
from app.models.faq import FaqCategory, FaqItem

db = SessionLocal()
try:
    cats = db.query(FaqCategory).count()
    items = db.query(FaqItem).count()
    print(f"Categories: {cats}")
    print(f"Items: {items}")
except Exception as e:
    print(f"Error checking db: {e}")
finally:
    db.close()
