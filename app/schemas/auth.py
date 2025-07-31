from pydantic import BaseModel, EmailStr
from typing import Literal, Optional

class Location(BaseModel):
    city: str
    country: str
    latitude: float
    longitude: float

class DeviceInfo(BaseModel):
    deviceId: str
    firstAccessDate: int
    ipAddress: str
    # Hacemos que la ubicación sea opcional para no romper clientes sin location
    location: Optional[Location] = None

class AnonymousLoginRequest(BaseModel):
    gender: Literal["MALE", "FEMALE", "OTHER"]
    device_info: DeviceInfo

class LoginWithDeviceRequest(BaseModel):
    email: EmailStr
    password: str
    device_info: DeviceInfo