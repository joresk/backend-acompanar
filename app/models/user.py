from sqlalchemy import Column, String, Boolean, DateTime, text
from sqlalchemy.dialects.postgresql import UUID, INET, ENUM as PG_ENUM
from sqlalchemy.orm import relationship
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
    genero = Column(
        PG_ENUM(
            'Masculino', 'Femenino', 'Otro',
            name='genero_usuario',
            create_type=False  # Ya existe en BD
        ),
        default='Otro',
        nullable=False
    )
    ip_dispositivo = Column(INET, nullable=True)
    
    # Relaciones
    contactos = relationship("Contact", back_populates="usuario", cascade="all, delete-orphan", order_by="Contact.id") # CAMBIO: "usuarios" a "usuario"
    peticiones = relationship("Peticion", back_populates="usuario", cascade="all, delete-orphan") # CAMBIO: "usuarios" a "usuario"