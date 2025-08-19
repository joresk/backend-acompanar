from pydantic import PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, Any
import os

class Settings(BaseSettings):
    # Nombre del proyecto
    PROJECT_NAME: str = "Acompañar API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Base de datos PostgreSQL
    POSTGRES_SERVER: str = os.getenv("POSTGRES_SERVER", "localhost")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "postgres")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "acompaniar")
    # Es necesario definir el puerto para que Pydantic lo valide
    POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))
    DATABASE_URL: Optional[PostgresDsn] = None
    
    @field_validator("DATABASE_URL", mode='before')
    @classmethod
    def assemble_db_connection(cls, v: Optional[str], info: Any) -> Any:
        if isinstance(v, str):
            return v
        
        return PostgresDsn.build(
            scheme="postgresql",
            username=info.data.get("POSTGRES_USER"),
            password=info.data.get("POSTGRES_PASSWORD"),
            host=info.data.get("POSTGRES_SERVER"),
            port=info.data.get("POSTGRES_PORT"), # Ahora el puerto se valida como int
            path=f"/{info.data.get('POSTGRES_DB') or ''}",
        )
    
    # JWT
    SECRET_KEY: str = os.getenv(
        "SECRET_KEY", 
        "tu-clave-secreta-super-segura-cambiar-en-produccion"
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 días
    
    # Twilio SMS
    TWILIO_ACCOUNT_SID: Optional[str] = os.getenv("TWILIO_ACCOUNT_SID")
    TWILIO_AUTH_TOKEN: Optional[str] = os.getenv("TWILIO_AUTH_TOKEN")
    TWILIO_PHONE_NUMBER: Optional[str] = os.getenv("TWILIO_PHONE_NUMBER")
    
    # Rate Limiting
    EMERGENCY_RATE_LIMIT_SECONDS: int = 60
    MAX_CONTACTS_PER_USER: int = 3
    
    # CORS
    BACKEND_CORS_ORIGINS: list = [
        "http://localhost",
        "http://localhost:3000",
        "http://localhost:8080",
        "http://localhost:8000",
    ]
    
    # Argentina específico
    DEFAULT_COUNTRY_CODE: str = "+54"
    EMERGENCY_NUMBER: str = "911"
    DEFAULT_TIMEZONE: str = "America/Argentina/Tucuman"
    
    # Email (opcional)
    SMTP_TLS: bool = True
    SMTP_PORT: Optional[int] = 587
    SMTP_HOST: Optional[str] = os.getenv("SMTP_HOST")
    SMTP_USER: Optional[str] = os.getenv("SMTP_USER")
    SMTP_PASSWORD: Optional[str] = os.getenv("SMTP_PASSWORD")
    EMAILS_FROM_EMAIL: Optional[str] = os.getenv("EMAILS_FROM_EMAIL")
    EMAILS_FROM_NAME: Optional[str] = "Acompañar"
    
    # Seguridad
    BCRYPT_ROUNDS: int = 12
    
    # Configuración del modelo de Pydantic V2
    model_config = SettingsConfigDict(
        env_file=".env",
        extra='ignore' # Esto reemplaza a `class Config`
    )

settings = Settings()