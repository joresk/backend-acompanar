from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.session import engine
from app.db.base import Base
from app.api import routes_auth, routes_users

# Importar modelos para crear tablas
from app.models import user

# Crear tablas si no existen
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Acompañar API",
    description="API para la aplicación de apoyo contra la violencia familiar",
    version="1.0.0"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar dominios permitidos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir routers
app.include_router(routes_auth.router, prefix="/auth", tags=["Autenticación"])
app.include_router(routes_users.router, prefix="/users", tags=["Usuarios"])

@app.get("/")
def read_root():
    return {
        "message": "Bienvenido a Acompañar API",
        "version": "1.0.0",
        "status": "active"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}