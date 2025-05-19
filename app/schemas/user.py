from pydantic import BaseModel, EmailStr, Field
from typing import Optional

# -------- Entrada --------

class UserCreate(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    full_name: Optional[str] = None
    is_anonymous: bool = True  # si no provee email/password => anónimo

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserAnonymousLogin(BaseModel):
    device_id: str  # identificador del dispositivo

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    password: Optional[str] = Field(default=None, min_length=6)
    is_active: Optional[bool] = None
    is_anonymous: Optional[bool] = None

# -------- Salida --------

class UserOut(BaseModel):
    id: int
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    is_anonymous: bool
    is_active: bool

    class Config:
        from_attributes = True  # reemplaza orm_mode en Pydantic v2

# -------- Interno --------

class UserInDB(UserOut):
    hashed_password: str

