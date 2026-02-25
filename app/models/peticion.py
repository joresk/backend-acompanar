from sqlalchemy import Column, String, ForeignKey, DateTime,Text, text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base

class Peticion(Base):
    __tablename__ = "peticiones"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))
    usuario_id = Column(UUID(as_uuid=True), ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False)
    contacto_id = Column(UUID(as_uuid=True), ForeignKey("contactos.id", ondelete="SET NULL"), nullable=True)
    ubicacion_id = Column(UUID(as_uuid=True), ForeignKey("ubicaciones.id", ondelete="CASCADE"), nullable=True)
    operador_id = Column(UUID(as_uuid=True), ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True)
    profesional_id = Column(UUID(as_uuid=True), ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True)
    estado_code = Column(String(20), ForeignKey("estados_peticiones.code"), nullable=False)
    creado_en = Column(DateTime, server_default=func.now(), nullable=False)
    mensaje = Column(Text, nullable=True) # Mensaje de texto opcional
    audio = Column(Text, nullable=True)   # URL o Base64 del audio

    # Relaciones
    usuario = relationship("User", foreign_keys=[usuario_id], back_populates="peticiones_creadas")
    operador = relationship("User", foreign_keys=[operador_id], back_populates="peticiones_despachadas")
    profesional = relationship("User", foreign_keys=[profesional_id], back_populates="peticiones_asignadas")
    contacto = relationship("Contact")
    ubicacion = relationship("Ubicacion")
    estado = relationship("EstadoPeticion")