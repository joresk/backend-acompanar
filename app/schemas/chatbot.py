from pydantic import BaseModel

class ChatbotTriageRequest(BaseModel):
    mensaje: str
    id_sesion: str

class ChatbotTriageResponse(BaseModel):
    nivel_riesgo: str # Puede ser: 'emergencia', 'asesoramiento', 'boton_panico'
    intencion: str
    mensaje_anonimizado: str