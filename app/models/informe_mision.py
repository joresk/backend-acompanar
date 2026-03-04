from sqlalchemy import Column, ForeignKey, DateTime, Text, text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base

class InformeMision(Base):
    __tablename__ = "informes_mision"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))
    peticion_id = Column(UUID(as_uuid=True), ForeignKey("peticiones.id", ondelete="CASCADE"), unique=True, nullable=False)
    detalle_resolucion = Column(Text, nullable=False)
    foto_url = Column(Text, nullable=True)
    creado_en = Column(DateTime, server_default=func.now(), nullable=False)

    # Relación inversa
    peticion = relationship("Peticion", back_populates="informe")