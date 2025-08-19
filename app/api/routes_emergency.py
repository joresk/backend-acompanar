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
    UbicacionCreate
)
from app.services.sms_service import sms_service

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/alert", response_model=EmergencyAlertResponse)
async def send_emergency_alert(
    *,
    db: Session = Depends(get_db),
    alert_request: EmergencyAlertRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """
    Enviar alerta de emergencia a los contactos configurados.
    
    - Limitado a 1 alerta por minuto para evitar spam
    - Envía SMS a todos los contactos o a los especificados
    - Crea registros en la tabla peticiones para auditoría
    """
    
    # Verificar rate limiting
    if not crud_peticion.can_send_alert(db, user_id=current_user.id):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Por seguridad, debes esperar 60 segundos antes de enviar otra alerta"
        )
    
    # Obtener contactos
    if alert_request.contacto_ids:
        # Verificar que los contactos pertenecen al usuario
        contacts = []
        for contact_id in alert_request.contacto_ids:
            contact = crud_contact.get(db=db, id=contact_id)
            if contact and contact.usuario_id == current_user.id:
                contacts.append(contact)
        
        if not contacts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se encontraron contactos válidos"
            )
    else:
        # Obtener todos los contactos del usuario
        contacts = crud_contact.get_by_user(db=db, user_id=current_user.id)
    
    if not contacts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No tienes contactos configurados. Agrega al menos un contacto de emergencia."
        )
    
    # Crear peticiones en BD para auditoría
    try:
        peticiones = crud_peticion.create_emergency_alert(
            db=db,
            user_id=current_user.id,
            contact_ids=[c.id for c in contacts],
            ubicacion_data=alert_request.ubicacion,
            mensaje=alert_request.mensaje
        )
    except Exception as e:
        logger.error(f"Error creando peticiones: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al registrar la alerta de emergencia"
        )
    
    # Preparar datos para SMS
    contacts_data = [
        {"nombre": c.nombre, "telefono": c.telefono} 
        for c in contacts
    ]
    
    location_data = None
    if alert_request.ubicacion:
        location_data = {
            "latitude": float(alert_request.ubicacion.latitud),
            "longitude": float(alert_request.ubicacion.longitud),
            "address": alert_request.ubicacion.direccion
        }
    
    # Enviar SMS
    sms_result = sms_service.send_emergency_sms(
        contacts=contacts_data,
        user_name=current_user.full_name,
        location=location_data,
        custom_message=alert_request.mensaje
    )
    
    # Actualizar estado de peticiones según resultado
    if sms_result['success']:
        peticion_ids = [p.id for p in peticiones]
        background_tasks.add_task(
            crud_peticion.mark_as_sent,
            db,
            peticion_ids=peticion_ids
        )
    
    return EmergencyAlertResponse(
        success=sms_result['success'],
        message="Alerta enviada exitosamente" if sms_result['success'] else "Error al enviar algunas alertas",
        peticiones_creadas=len(peticiones),
        sms_enviados=sms_result.get('sent', 0),
        timestamp=datetime.utcnow()
    )

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

@router.post("/test-sms")
def test_sms_to_contact(
    contact_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Enviar SMS de prueba a un contacto específico.
    Solo para contactos propios del usuario.
    """
    contact = crud_contact.get(db=db, id=contact_id)
    
    if not contact or contact.usuario_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo puedes enviar SMS de prueba a tus contactos registrados"
        )
    
    result = sms_service.send_test_sms(contact.telefono)
    
    return {
        "success": result['success'],
        "message": f"SMS de prueba enviado a {contact.nombre}" if result['success'] else "Error al enviar SMS",
        "contact": contact.nombre,
        "phone": contact.telefono
    }