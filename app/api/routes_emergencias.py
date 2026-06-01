from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.db.session import get_db
from app.models.peticion import Peticion
from app.models.user import User
from app.models.ubicacion import Ubicacion
from uuid import UUID
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

class AlertaRequest(BaseModel):
    id_sesion: str
    tipo_alerta: str
    mensaje_original: str

@router.post("/alerta")
def registrar_alerta(payload: AlertaRequest, db: Session = Depends(get_db)):
    print("LOG: Entered registrar_alerta")
    try:
        print(f"LOG: id_sesion is {payload.id_sesion}")
        user_uuid = UUID(payload.id_sesion)
        print("LOG: Converted UUID")
        
        print("LOG: Querying user...")
        user = db.query(User).filter(User.id == user_uuid).first()
        print(f"LOG: Query user done. Found: {user is not None}")
        
        if not user:
            print("LOG: User not found, raising 404")
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
            
        # Obtener lat/lon del usuario o usar fallback
        lat = user.latitud_actual if user.latitud_actual is not None else -26.8241
        lon = user.longitud_actual if user.longitud_actual is not None else -65.2226
        
        print(f"LOG: Creating Ubicacion with coordinates: {lat}, {lon}")
        ubicacion = Ubicacion(
            direccion="Alerta de emergencia desde Chatbot",
            latitud=lat,
            longitud=lon
        )
        db.add(ubicacion)
        db.flush()  # Para obtener el ID de la ubicación
        print(f"LOG: Ubicacion created with ID: {ubicacion.id}")
        
        print("LOG: Creating Peticion object...")
        nueva_peticion = Peticion(
            usuario_id=user.id,
            ubicacion_id=ubicacion.id,
            estado_code="en_triaje",
            mensaje=f"[{payload.tipo_alerta.upper()}] {payload.mensaje_original}"
        )
        print("LOG: Adding Peticion...")
        db.add(nueva_peticion)
        print("LOG: Committing...")
        db.commit()
        print("LOG: Refreshing...")
        db.refresh(nueva_peticion)
        print("LOG: Done. Returning...")
        
        return {
            "success": True,
            "message": "Alerta de emergencia registrada exitosamente",
            "peticion_id": str(nueva_peticion.id)
        }
    except Exception as e:
        print(f"LOG: Exception caught: {e}")
        try:
            db.rollback()
        except:
            pass
        raise HTTPException(status_code=500, detail=str(e))
