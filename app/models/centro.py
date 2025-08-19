from sqlalchemy import Column, String, text
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base

class Centro(Base):
    __tablename__ = "centros"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))
    nombre = Column(String(100), nullable=False)
    direccion = Column(String(255), nullable=True)
    telefono = Column(String(15), nullable=True)
    email = Column(String(100), nullable=True)
    horario_atencion = Column(String(255), nullable=True)