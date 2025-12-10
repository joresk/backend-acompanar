from sqlalchemy import Column, String, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.db.base_class import Base

class Guia(Base):
    __tablename__ = "guias"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre = Column(String, unique=True, index=True, nullable=False)
    descripcion = Column(Text, nullable=True)

    items = relationship("ItemGuia", back_populates="guia", cascade="all, delete-orphan")

class ItemGuia(Base):
    __tablename__ = "item_guia"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    guia_id = Column(UUID(as_uuid=True), ForeignKey("guias.id"), nullable=False)
    nombre = Column(String, nullable=False)
    descripcion = Column(Text, nullable=True)
    
    # --- NUEVO CAMPO ---
    url_imagen = Column(Text, nullable=True) 
    # -------------------

    guia = relationship("Guia", back_populates="items")