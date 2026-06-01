import sys
import os

backend_dir = r"f:\0- Acompañar\Acompaniar-bf\backend-acompanar"
sys.path.append(backend_dir)

routes_faq_path = os.path.join(backend_dir, "app", "api", "routes_faq.py")

with open(routes_faq_path, "r", encoding="utf-8") as f:
    content = f.read()

# Remove CDATA wrappers
content = content.replace("<![CDATA[", "")
content = content.replace("]]>", "")

with open(routes_faq_path, "w", encoding="utf-8") as f:
    f.write(content)

print("routes_faq.py updated.")

# Re-seed the DB
from app.db.session import engine, SessionLocal
from app.models.faq import FaqCategory, FaqItem
from sqlalchemy import text
from app.api.routes_faq import seed_faqs

db = SessionLocal()
try:
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM faq_items;"))
        conn.execute(text("DELETE FROM faq_categories;"))
    print("Old data cleared.")
    
    # Run seed
    result = seed_faqs(db)
    print("Re-seed result:", result)
except Exception as e:
    print("Error during re-seed:", e)
finally:
    db.close()
