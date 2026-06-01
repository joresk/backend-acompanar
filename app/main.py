from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.api import api_router
from app.api import routes_emergencias
import app.models
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Crear aplicación
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir routers
app.include_router(api_router, prefix=settings.API_V1_STR)
app.include_router(routes_emergencias.router, prefix="/api/emergencias")

# Root endpoint
@app.get("/")
def read_root():
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "active",
        "message": "Bienvenido a Acompañar API"
    }

# Health check
@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "acompaniar-api",
        "version": settings.VERSION
    }

# Startup event
@app.on_event("startup")
async def startup_event():
    logging.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION}")
    logging.info(f"Database: {settings.POSTGRES_DB}")
    logging.info(f"SMS Service: {'Enabled' if settings.TWILIO_ACCOUNT_SID else 'Disabled'}")
    
    # Crear extensión UUID y tabla RAG si no existen
    try:
        from app.db.session import engine
        from sqlalchemy import text
        with engine.begin() as connection:
            connection.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";'))
            connection.execute(text("""
                CREATE TABLE IF NOT EXISTS rag_chunks (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    content TEXT NOT NULL,
                    source VARCHAR(255)
                );
            """))
        logging.info("✅ Extensión UUID y tabla rag_chunks verificadas/creadas con éxito.")
    except Exception as e:
        logging.error(f"❌ Error al verificar/crear tabla rag_chunks: {e}")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    logging.info(f"Shutting down {settings.PROJECT_NAME}")