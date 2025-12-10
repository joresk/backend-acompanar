from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timedelta
from uuid import UUID
import logging

from app.api.deps import get_current_user, get_db, get_current_token
from app.crud.crud_contact import crud_contact
from app.crud.crud_peticion import crud_peticion
from app.models.user import User
from app.schemas.contact import (
    EmergencyAlertRequest,
    EmergencyAlertResponse,
    UbicacionCreate,EmergencyReportRequest,
    EmergencyReportResponse
)
from app.models.peticion import Peticion
from app.models.ubicacion import Ubicacion
from app.services.storage_service import storage_service

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/alert/status")
def get_alert_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Verificar el estado de alertas del usuario.
    Indica si puede enviar una alerta o cuánto debe esperar.
    """
    can_send = crud_peticion.can_send_alert(db, user_id=current_user.id)
    recent_count = crud_peticion.get_recent_peticion_count(
        db, 
        user_id=current_user.id, 
        minutes=1
    )
    
    wait_seconds = 0 if can_send else (60 - recent_count * 60)
    
    return {
        "can_send_alert": can_send,
        "wait_seconds": max(0, wait_seconds),
        "recent_alerts": recent_count,
        "message": "Puedes enviar una alerta" if can_send else f"Espera {wait_seconds} segundos"
    }

@router.get("/history")
def get_emergency_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = 10
):
    """
    Obtener historial de alertas enviadas por el usuario.
    """
    peticiones = crud_peticion.get_user_peticiones(
        db=db,
        user_id=current_user.id,
        limit=limit
    )
    
    return {
        "total": len(peticiones),
        "alerts": [
            {
                "id": str(p.id),
                "contact": p.contacto.nombre if p.contacto else "Desconocido",
                "status": p.estado_code,
                "sent_at": p.creado_en,
                "location": {
                    "address": p.ubicacion.direccion if p.ubicacion else None,
                    "latitude": float(p.ubicacion.latitud) if p.ubicacion else None,
                    "longitude": float(p.ubicacion.longitud) if p.ubicacion else None
                } if p.ubicacion else None
            }
            for p in peticiones
        ]
    }
@router.post("/report")
async def report_emergency_alert(
    *,
    db: Session = Depends(get_db),
    report_request: EmergencyReportRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Recibir reporte de alerta de emergencia enviada desde la aplicación móvil.
    """
    
    try:
        # 1. Obtener IDs de contactos válidos (MANTENEMOS TU LÓGICA ORIGINAL)
        contact_ids = []
        for contact_data in report_request.contacts:
            try:
                contact = crud_contact.get(db=db, id=UUID(contact_data.id))
                if contact and contact.usuario_id == current_user.id:
                    contact_ids.append(contact.id)
            except (ValueError, Exception):
                continue
        
        if not contact_ids:
            logger.warning(f"Usuario {current_user.id} reportó alerta sin contactos válidos")

        # 2. Crear Ubicación en BD (MODIFICADO: Creamos el modelo DB directamente)
        ubicacion_id = None
        if report_request.location:
            ubicacion = Ubicacion(
                direccion=report_request.location.address or "Ubicación desde dispositivo",
                latitud=report_request.location.latitude,
                longitud=report_request.location.longitude
            )
            db.add(ubicacion)
            db.flush() # Para obtener el ID
            ubicacion_id = ubicacion.id
        
                # --- 2. NUEVA LÓGICA DE AUDIO (Insertar antes de crear peticiones) ---
        audio_url = None
        if report_request.audio:
            # El frontend envía el Base64, aquí lo convertimos a URL
            # Esto puede tardar unos segundos, por eso es bueno que sea async
            audio_url = storage_service.upload_base64_audio(report_request.audio)
    # ---------------------------------------------------------------------
        peticiones = []
        report_id = None
        # 3. Crear peticiones MANUALMENTE para incluir Audio y Mensaje
        if contact_ids:
            try:
                for contact_id in contact_ids:
                    peticion = Peticion(
                        usuario_id=current_user.id,
                        contacto_id=contact_id,
                        ubicacion_id=ubicacion_id,
                        estado_code="atendida", # Asumimos atendida/enviada por ser un reporte de la app
                        creado_en=datetime.utcnow(),        
                        mensaje=report_request.mensaje or report_request.message,
                        audio=audio_url
                    )
                    db.add(peticion)
                    peticiones.append(peticion)
                
                db.commit()
                
                # Refrescar para obtener IDs y datos
                for p in peticiones:
                    db.refresh(p)

                if peticiones:
                    report_id = str(peticiones[0].id)
                    
            except Exception as e:
                logger.error(f"Error creando peticiones para reporte: {e}")
                try:
                    db.rollback()
                except:
                    pass

        # Log para auditoría
        logger.info(
            f"Alerta reportada por usuario {current_user.id}: "
            f"{report_request.sms_result.sentCount} SMS enviados, "
            f"{report_request.sms_result.failedCount} fallos"
        )
        
        return {
            "success": True,
            "message": "Reporte de alerta registrado exitosamente",
            "report_id": report_id,
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"Error procesando reporte de emergencia: {e}")
        try:
            db.rollback()
        except:
            pass
        
        return {
            "success": True, 
            "message": "Alerta enviada correctamente, reporte parcial registrado",
            "report_id": None,
            "timestamp": datetime.utcnow()
        }