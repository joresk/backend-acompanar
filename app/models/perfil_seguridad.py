from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base

import uuid

class PerfilSeguridad(Base):
    __tablename__ = "perfiles_seguridad"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usuario_id = Column(UUID(as_uuid=True), ForeignKey("usuarios.id", ondelete="CASCADE"), unique=True, nullable=False)
    nivel_riesgo = Column(Integer, default=1)
    notas_contexto = Column(Text, nullable=True)
    tipo_violencia = Column(Text, nullable=True)
    ultima_interaccion = Column(DateTime, server_default=func.now())
    ultimo_checkin = Column(DateTime, nullable=True)

    # Relaciones
    usuario = relationship("User", back_populates="perfil_seguridad")
