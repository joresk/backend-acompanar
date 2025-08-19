from sqlalchemy import Column, String, ForeignKey, DateTime, text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base

class Peticion(Base):
    __tablename__ = "peticiones"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))
    usuario_id = Column(UUID(as_uuid=True), ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False)
    contacto_id = Column(UUID(as_uuid=True), ForeignKey("contactos.id", ondelete="RESTRICT"), nullable=False)
    ubicacion_id = Column(UUID(as_uuid=True), ForeignKey("ubicaciones.id", ondelete="CASCADE"), nullable=False)
    estado_code = Column(String(20), ForeignKey("estados_peticiones.code"), nullable=False)
    creado_en = Column(DateTime, server_default=func.now(), nullable=False)
    
    # Relaciones
    usuario = relationship("User", back_populates="peticiones")
    contacto = relationship("Contact")
    ubicacion = relationship("Ubicacion")
    estado = relationship("EstadoPeticion")