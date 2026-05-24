from typing import List, Optional
from pydantic import BaseModel
from uuid import UUID

class ItemGuiaSchema(BaseModel):
    id: UUID
    nombre: str
    descripcion: Optional[str] = None
    url_imagen: Optional[str] = None  # Campo nuevo

    class Config:
        from_attributes = True

class GuiaSchema(BaseModel):
    id: UUID
    nombre: str
    descripcion: Optional[str] = None
    items: List[ItemGuiaSchema] = [] # Lista anidada

    class Config:
        from_attributes = True

class ChatbotTriageRequest(BaseModel):
    mensaje: str
    id_sesion: str

class ChatbotTriageResponse(BaseModel):
    nivel_riesgo: str # Puede ser: 'emergencia', 'asesoramiento', 'boton_panico'
    intencion: str
    mensaje_anonimizado: str