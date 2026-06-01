from sqlalchemy import Column, String, Numeric, text
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base

class Ubicacion(Base):
    __tablename__ = "ubicaciones"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))
    direccion = Column(String(255), nullable=False)
    latitud = Column(Numeric(10, 6), nullable=False)  # Precisión de 6 decimales
    longitud = Column(Numeric(10, 6), nullable=False)

