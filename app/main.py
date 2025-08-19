from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.api import api_router
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

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    logging.info(f"Shutting down {settings.PROJECT_NAME}")