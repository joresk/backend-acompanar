from pydantic import BaseModel, EmailStr, Field, IPvAnyAddress, validator
from typing import Optional
from datetime import datetime
from uuid import UUID
from enum import Enum

class GenderEnum(str, Enum):
    MASCULINO = "Masculino"
    FEMENINO = "Femenino"
    OTRO = "Otro"

class UserCreate(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    full_name: str
    phone: Optional[str] = None
    is_anonymous: bool = False
    genero: Optional[str] = "Otro"  # Cambiar a string
    ip_dispositivo: Optional[str] = None
    
    @validator('genero')
    def validate_gender(cls, v):
        """Valida y normaliza el género"""
        if not v:
            return GenderEnum.OTRO.value
        
        # Mapear diferentes formatos al enum correcto
        gender_map = {
            'masculino': GenderEnum.MASCULINO.value,
            'male': GenderEnum.MASCULINO.value,
            'hombre': GenderEnum.MASCULINO.value,
            'femenino': GenderEnum.FEMENINO.value,
            'female': GenderEnum.FEMENINO.value,
            'mujer': GenderEnum.FEMENINO.value,
            'otro': GenderEnum.OTRO.value,
            'other': GenderEnum.OTRO.value,
        }
        
        # Convertir a minúsculas para comparar
        v_lower = v.lower()
        
        # Si es un valor exacto del enum, devolverlo
        if v in [e.value for e in GenderEnum]:
            return v
        
        # Si no, intentar mapearlo
        return gender_map.get(v_lower, GenderEnum.OTRO.value)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    password: Optional[str] = Field(default=None, min_length=6)
    phone: Optional[str] = None
    is_active: Optional[bool] = None
    genero: Optional[GenderEnum] = None

# -------- Salida --------
class UserOut(BaseModel):
    id: UUID
    email: Optional[EmailStr] = None
    full_name: str
    phone: Optional[str] = None
    is_anonymous: bool
    is_active: bool
    created_at: datetime
    genero: GenderEnum

    class Config:
        from_attributes = True
        use_enum_values = True

# -------- Interno --------
class UserInDB(UserOut):
    hashed_password: Optional[str] = None
    ip_dispositivo: Optional[str] = None