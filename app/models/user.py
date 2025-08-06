from sqlalchemy import Column, String, Boolean, DateTime, Enum, text
from sqlalchemy.dialects.postgresql import UUID, INET
from app.db.base import Base
from datetime import datetime
import enum

class GenderEnum(str, enum.Enum):
    MASCULINO = "Masculino"
    FEMENINO = "Femenino"
    OTRO = "Otro"

class User(Base):
    __tablename__ = "usuarios"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))
    full_name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=True)
    hashed_password = Column(String, nullable=True)
    phone = Column(String(15), nullable=True)
    is_anonymous = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    genero = Column(Enum(GenderEnum), default=GenderEnum.OTRO, nullable=False)
    ip_dispositivo = Column(INET, nullable=True)