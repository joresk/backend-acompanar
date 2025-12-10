from typing import Optional
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime

# Esquema para recibir la alerta desde el celular
class PeticionCreate(BaseModel):
    ubicacion_latitud: float
    ubicacion_longitud: float
    direccion: Optional[str] = None
    contacto_id: Optional[UUID] = None
    mensaje: Optional[str] = None
    audio: Optional[str] = None
    # ---------------------

class PeticionOut(BaseModel):
    id: UUID
    estado_code: str
    creado_en: datetime
    # ... otros campos de salida si necesitas
    class Config:
        from_attributes = True