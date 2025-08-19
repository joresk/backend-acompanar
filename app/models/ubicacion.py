from sqlalchemy import Column, String, Numeric, text
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base

class Ubicacion(Base):
    __tablename__ = "ubicaciones"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))
    direccion = Column(String(255), nullable=False)
    latitud = Column(Numeric(10, 6), nullable=False)  # Precisión de 6 decimales
    longitud = Column(Numeric(10, 6), nullable=False)

# app/models/estado_peticion.py
from sqlalchemy import Column, String
from app.db.base import Base

class EstadoPeticion(Base):
    __tablename__ = "estados_peticiones"
    
    code = Column(String(20), primary_key=True)
    descripcion = Column(String(100), nullable=False)