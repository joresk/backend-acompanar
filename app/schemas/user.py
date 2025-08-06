from pydantic import BaseModel, EmailStr, Field, IPvAnyAddress
from typing import Optional
from datetime import datetime
from uuid import UUID
from enum import Enum

class GenderEnum(str, Enum):
    MASCULINO = "Masculino"
    FEMENINO = "Femenino"
    OTRO = "Otro"

# -------- Entrada --------
class UserCreate(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    full_name: str
    phone: Optional[str] = None
    is_anonymous: bool = False
    genero: Optional[GenderEnum] = GenderEnum.OTRO
    ip_dispositivo: Optional[str] = None

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