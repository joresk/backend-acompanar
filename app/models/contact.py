from sqlalchemy import Column, String, ForeignKey, Integer, text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base
from datetime import datetime

class Contact(Base):
    __tablename__ = "contactos"
    
    # Usar UUID como en tu BD
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))
    usuario_id = Column(UUID(as_uuid=True), ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False)
    nombre = Column(String(50), nullable=False)  # Tu BD usa varchar(50)
    telefono = Column(String(15), nullable=False)  # Tu BD usa varchar(15)
    
    # Relación con usuario
    usuario = relationship("User", back_populates="contactos")
    
    # Para tracking interno (no en BD original pero útil)
    _is_primary = None  # Lo calcularemos dinámicamente
    
    @property
    def is_primary(self):
        """El primer contacto de un usuario es el primario"""
        return self._is_primary if self._is_primary is not None else False