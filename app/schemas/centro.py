from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID

class CentroOut(BaseModel):
    id: UUID
    nombre: str
    direccion: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
    horario_atencion: Optional[str] = None
    
    class Config:
        from_attributes = True

class CentroListResponse(BaseModel):
    centros: List[CentroOut]
    total: int