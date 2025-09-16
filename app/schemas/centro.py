from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from app.schemas.contact import UbicacionCreate, UbicacionOut

# --- NUEVOS SCHEMAS PARA IMÁGENES ---
class ImagenBase(BaseModel):
    url_imagen: str

class ImagenCreate(ImagenBase):
    pass

class ImagenOut(ImagenBase):
    id: UUID
    
    class Config:
        from_attributes = True
# Schema para teléfonos
class TelefonoBase(BaseModel):
    telefono: str = Field(..., min_length=1, max_length=15)

class TelefonoCreate(TelefonoBase):
    pass

class TelefonoOut(TelefonoBase):
    id: UUID
    
    class Config:
        from_attributes = True

# Schema para ubicación (reutilizar o crear)
class UbicacionBase(BaseModel):
    direccion: str = Field(..., max_length=255)
    latitud: float = Field(..., ge=-90, le=90)
    longitud: float = Field(..., ge=-180, le=180)

class UbicacionCreate(UbicacionBase):
    pass

class UbicacionOut(UbicacionBase):
    id: UUID
    
    class Config:
        from_attributes = True

# Schema para categorías
class CategoriaOut(BaseModel):
    id: str
    descripcion: str
    
    class Config:
        from_attributes = True

# Schemas para Centro - AGREGAR ESTOS
class CentroBase(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=100)
    descripcion: str
    categoria_code: Optional[str] = None

class CentroCreate(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=100)
    descripcion: str
    categoria_code: Optional[str] = None
    ubicacion: UbicacionCreate
    telefonos: List[str] = Field(default_factory=list, max_items=5)
    # --- AÑADIR ESTA LÍNEA ---
    imagenes: List[str] = Field(default_factory=list) # Espera una lista de URLs

class CentroUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=1, max_length=100)
    descripcion: Optional[str] = None
    categoria_code: Optional[str] = None
    ubicacion: Optional[UbicacionCreate] = None
    telefonos: Optional[List[str]] = None
    # --- AÑADIR ESTA LÍNEA ---
    imagenes: Optional[List[str]] = None # Espera una lista de URLs

class CentroWithDetails(BaseModel):
    id: UUID
    nombre: str
    descripcion: str
    categoria_code: Optional[str]
    categoria: Optional[CategoriaOut]
    ubicacion: UbicacionOut
    telefonos: List[TelefonoOut]
    # --- AÑADIR ESTA LÍNEA ---
    imagenes: List[ImagenOut] # Devuelve una lista de objetos de imagen
    
    class Config:
        from_attributes = True
# Actualizar el CentroListResponse existente
class CentroListResponse(BaseModel):
    centros: List[CentroWithDetails]
    total: int
    page: int = 1
    per_page: int = 10