import os
import sys

backend_dir = r"f:\0- Acompañar\Acompaniar-bf\backend-acompanar"
app_dir = os.path.join(backend_dir, "app")
sys.path.append(backend_dir)

# 1. Delete old files
files_to_delete = [
    os.path.join(app_dir, "models", "guia.py"),
    os.path.join(app_dir, "schemas", "guia.py"),
    os.path.join(app_dir, "crud", "crud_guia.py"),
    os.path.join(app_dir, "api", "routes_guias.py")
]

for file_path in files_to_delete:
    if os.path.exists(file_path):
        os.remove(file_path)
        print(f"Deleted {file_path}")

# 2. Modify app/models/__init__.py
init_path = os.path.join(app_dir, "models", "__init__.py")
if os.path.exists(init_path):
    with open(init_path, "r", encoding="utf-8") as f:
        content = f.read()
    if "from app.models.guia import Guia, ItemGuia" in content:
        content = content.replace("from app.models.guia import Guia, ItemGuia\n", "")
        with open(init_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Updated {init_path}")

# 3. Modify app/api/api.py
api_path = os.path.join(app_dir, "api", "api.py")
if os.path.exists(api_path):
    with open(api_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Remove import
    content = content.replace(" routes_guias,", "")
    content = content.replace("routes_guias,", "")
    
    # Remove router include
    router_str = """api_router.include_router(
    routes_guias.router,
    prefix="/guias", 
    tags=["guias"]
)"""
    if router_str in content:
        content = content.replace(router_str, "")
        with open(api_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Updated {api_path}")

# 4. Drop tables in DB
from app.db.session import engine
from sqlalchemy import text

try:
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS item_guia CASCADE;"))
        conn.execute(text("DROP TABLE IF EXISTS guias CASCADE;"))
    print("Tables 'item_guia' and 'guias' dropped successfully.")
except Exception as e:
    print(f"Error dropping tables: {e}")
