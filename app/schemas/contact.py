from pydantic import BaseModel, Field, field_validator, UUID4
from typing import Optional, List
from datetime import datetime
import re

class ContactBase(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=50)
    telefono: str = Field(..., min_length=1, max_length=15)
    
    @field_validator('nombre', mode='before')
    @classmethod
    def validate_nombre(cls, v: str):
        if not v or not v.strip():
            raise ValueError('El nombre no puede estar vacío')
        if len(v.strip()) > 50:
            raise ValueError('El nombre no puede tener más de 50 caracteres')
        return v.strip()
    
    @field_validator('telefono', mode='before')
    @classmethod
    def validate_telefono(cls, v: str):
        # Limpiar espacios y caracteres especiales
        clean_phone = re.sub(r'[^0-9+]', '', v)
        
        # Validar que tenga entre 6 y 15 caracteres
        if len(clean_phone) < 6 or len(clean_phone) > 15:
            raise ValueError('Teléfono debe tener entre 6 y 15 dígitos')
        
        # Si no tiene código de país, agregar +54 para Argentina
        if not clean_phone.startswith('+'):
            if not clean_phone.startswith('54'):
                clean_phone = '54' + clean_phone.lstrip('0')
        
        return clean_phone[:15]  # Asegurar máximo 15 caracteres

class ContactCreate(ContactBase):
    pass

class ContactUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=1, max_length=50)
    telefono: Optional[str] = Field(None, min_length=6, max_length=15)

class ContactOut(BaseModel):
    id: UUID4
    nombre: str
    telefono: str
    is_primary: bool = False
    
    class Config:
        from_attributes = True

class ContactListResponse(BaseModel):
    contacts: List[ContactOut]
    total: int
    max_allowed: int = 3

# Schemas para Ubicación
class UbicacionCreate(BaseModel):
    direccion: str = Field(..., max_length=255)
    latitud: float = Field(..., ge=-90, le=90)
    longitud: float = Field(..., ge=-180, le=180)
    
    @field_validator('latitud', 'longitud', mode='before')
    @classmethod
    def round_coordinates(cls, v):
        # Redondear a 6 decimales como en la BD
        return round(v, 6)

class UbicacionOut(BaseModel):
    id: UUID4
    direccion: str
    latitud: float
    longitud: float
    
    class Config:
        from_attributes = True

# Schemas para Peticiones (Emergencias)
class PeticionCreate(BaseModel):
    contacto_ids: Optional[List[UUID4]] = None  # Si None, enviar a todos
    ubicacion: Optional[UbicacionCreate] = None
    mensaje: Optional[str] = Field(None, max_length=500)

class PeticionOut(BaseModel):
    id: UUID4
    usuario_id: UUID4
    contacto_id: UUID4
    ubicacion: UbicacionOut
    estado_code: str
    creado_en: datetime
    
    class Config:
        from_attributes = True

class EmergencyAlertRequest(BaseModel):
    ubicacion: Optional[UbicacionCreate] = None
    mensaje: Optional[str] = Field(None, max_length=160)
    contacto_ids: Optional[List[UUID4]] = None

class EmergencyAlertResponse(BaseModel):
    success: bool
    message: str
    peticiones_creadas: int
    sms_enviados: int
    timestamp: datetime

# Nuevas clases para sincronización de contactos
class ContactSyncRequest(BaseModel):
    contacts: List[ContactCreate]

class ContactSyncResponse(BaseModel):
    synced: bool
    contacts: List[ContactOut]
    message: str

# Schemas para Emergency Report (desde app móvil)
class ContactReportData(BaseModel):
    id: str
    nombre: str
    telefono: str
    isPrimary: bool = False

class LocationReportData(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    address: Optional[str] = None
    accuracy: Optional[float] = None
    timestamp: Optional[int] = None

class SmsContactResult(BaseModel):
    contactName: str
    phoneNumber: str
    success: bool
    error: Optional[str] = None

class SmsResultReport(BaseModel):
    success: bool
    sentCount: int
    failedCount: int
    details: List[SmsContactResult]

class EmergencyReportRequest(BaseModel):
    contacts: List[ContactReportData]
    location: Optional[LocationReportData] = None
    message: Optional[str] = Field(None, max_length=500)
    sms_result: SmsResultReport

# Simplificar la respuesta para evitar problemas de serialización
class EmergencyReportResponse(BaseModel):
    success: bool
    message: str
    report_id: Optional[str] = None
    timestamp: datetime