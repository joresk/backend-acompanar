from pydantic import BaseModel, EmailStr
from typing import Optional
from enum import Enum

class GenderEnum(str, Enum):
    MALE = "Masculino"
    FEMALE = "Femenino"
    OTHER = "Otro"

class Location(BaseModel):
    latitude: float
    longitude: float
    city: Optional[str] = None
    country: Optional[str] = None

class DeviceInfo(BaseModel):
    deviceId: str
    phoneNumber: Optional[str] = None
    ipAddress: Optional[str] = None
    location: Optional[Location] = None
    firstAccessDate: int  # timestamp

class AnonymousLoginRequest(BaseModel):
    gender: GenderEnum
    device_info: DeviceInfo

class LoginWithDeviceRequest(BaseModel):
    email: EmailStr
    password: str
    device_info: DeviceInfo

class RecoverPasswordRequest(BaseModel):
    email: EmailStr

class RecoverPasswordResponse(BaseModel):
    message: str
    success: bool