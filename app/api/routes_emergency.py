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

@router.post("/report")
async def report_emergency_alert(
    *,
    db: Session = Depends(get_db),
    report_request: EmergencyReportRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Recibir reporte de alerta de emergencia enviada desde la aplicación móvil.
    
    Este endpoint es llamado después de que la app móvil envía SMS localmente
    para registrar la alerta en el backend con fines de auditoría.
    """
    
    try:
        # Obtener IDs de contactos válidos para el usuario
        contact_ids = []
        for contact_data in report_request.contacts:
            try:
                # Verificar que el contacto pertenece al usuario
                contact = crud_contact.get(db=db, id=UUID(contact_data.id))
                if contact and contact.usuario_id == current_user.id:
                    contact_ids.append(contact.id)
            except (ValueError, Exception):
                # UUID inválido o error de BD, continuar con el siguiente
                continue
        
        if not contact_ids:
            logger.warning(f"Usuario {current_user.id} reportó alerta sin contactos válidos")
            # Continuar sin fallar para registrar el evento
        
        # Crear ubicación si se proporciona
        ubicacion_data = None
        if report_request.location:
            ubicacion_data = UbicacionCreate(
                direccion=report_request.location.address or "Ubicación desde dispositivo",
                latitud=report_request.location.latitude,
                longitud=report_request.location.longitude
            )
        
        # Crear peticiones en BD para auditoría solo si hay contactos válidos
        peticiones = []
        report_id = None
        
        if contact_ids:
            try:
                # Crear peticiones
                peticiones = crud_peticion.create_emergency_alert(
                    db=db,
                    user_id=current_user.id,
                    contact_ids=contact_ids,
                    ubicacion_data=ubicacion_data,
                    mensaje=report_request.message
                )
                
                # Marcar como atendidas inmediatamente ya que el SMS ya se envió
                if peticiones:
                    peticion_ids = [p.id for p in peticiones]
                    crud_peticion.mark_as_sent(
                        db=db,
                        peticion_ids=peticion_ids
                    )
                    report_id = str(peticiones[0].id)
                    
            except Exception as e:
                logger.error(f"Error creando peticiones para reporte: {e}")
                # Hacer rollback explícito y continuar
                try:
                    db.rollback()
                except:
                    pass
                # No fallar, el SMS ya se envió exitosamente
        
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
        # Rollback explícito
        try:
            db.rollback()
        except:
            pass
        
        # Retornar éxito parcial ya que el SMS ya se envió
        return {
            "success": True,  # ← TRUE porque el SMS sí se envió
            "message": "Alerta enviada correctamente, reporte parcial registrado",
            "report_id": None,
            "timestamp": datetime.utcnow()
        }