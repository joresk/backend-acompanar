from sqlalchemy import Column, String, ForeignKey, text, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base

class CategoriasCentros(Base):
    __tablename__ = "categorias_centros"
    
    id = Column(String(20), primary_key=True)
    descripcion = Column(String(100), nullable=False)
    
    # Relación
    centros = relationship("Centro", back_populates="categoria")

class Centro(Base):
    __tablename__ = "centros_ayuda"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))
    nombre = Column(String(100), nullable=False)
    descripcion = Column(Text, nullable=False)
    ubicacion_id = Column(UUID(as_uuid=True), ForeignKey("ubicaciones.id"), nullable=False)
    categoria_code = Column(String(20), ForeignKey("categorias_centros.id"), nullable=True)
    
    # Relaciones
    ubicacion = relationship("Ubicacion", backref="centros")
    categoria = relationship("CategoriasCentros", back_populates="centros")
    telefonos = relationship("CentroAyudaTelefono", back_populates="centro", cascade="all, delete-orphan")
    
    # --- NUEVA RELACIÓN ---
    # Se añade la relación con la tabla de imágenes.
    imagenes = relationship("CentroAyudaImagen", back_populates="centro", cascade="all, delete-orphan")

class CentroAyudaTelefono(Base):
    __tablename__ = "centros_ayuda_telefonos"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))
    centro_id = Column(UUID(as_uuid=True), ForeignKey("centros_ayuda.id", ondelete="CASCADE"), nullable=False)
    telefono = Column(String(15), nullable=False)
    
    # Relación
    centro = relationship("Centro", back_populates="telefonos")

# --- NUEVA CLASE PARA EL MODELO DE IMÁGENES ---
class CentroAyudaImagen(Base):
    __tablename__ = "centros_ayuda_imagenes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))
    centro_id = Column(UUID(as_uuid=True), ForeignKey("centros_ayuda.id", ondelete="CASCADE"), nullable=False)
    url_imagen = Column(Text, nullable=False)
    
    # Relación inversa para que cada imagen sepa a qué centro pertenece
    centro = relationship("Centro", back_populates="imagenes")