from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session, joinedload
from typing import Optional, List
from datetime import datetime, timedelta
from uuid import UUID
import logging
from pydantic import BaseModel
from app.models.informe_mision import InformeMision

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

# 1. Esquema temporal para recibir el ID del profesional desde la web
class DespachoRequest(BaseModel):
    profesional_id: str
class FinalizarMisionRequest(BaseModel):
    informe: str
    foto_base64: Optional[str] = None

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
# Endpoint para recibir alertas de emergencia desde la app móvil
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
        try:
            # A. Siempre creamos UNA petición principal para la Central Operativa (Radar)
            peticion_central = Peticion(
                usuario_id=current_user.id,
                contacto_id=None, # No pertenece a un contacto, va a la policía/operador
                ubicacion_id=ubicacion_id,
                estado_code="en_triaje", # <-- IMPORTANTE: Este estado lo hace aparecer en el mapa
                creado_en=datetime.utcnow(),        
                mensaje=report_request.mensaje or report_request.message,
                audio=audio_url
            )
            db.add(peticion_central)
            peticiones.append(peticion_central)

            # B. Si además hay contactos personales, les creamos su registro
            for contact_id in contact_ids:
                peticion_contacto = Peticion(
                    usuario_id=current_user.id,
                    contacto_id=contact_id,
                    ubicacion_id=ubicacion_id,
                    estado_code="en_triaje",
                    creado_en=datetime.utcnow(),        
                    mensaje=report_request.mensaje or report_request.message,
                    audio=audio_url
                )
                db.add(peticion_contacto)
                peticiones.append(peticion_contacto)
            
            db.commit()
            
            # Refrescar para obtener IDs y datos
            for p in peticiones:
                db.refresh(p)

            if peticiones:
                report_id = str(peticiones[0].id) # Guardamos el ID de la central
                
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
# 2. Endpoint para obtener alertas para el Radar Web
@router.get("/activas")
def get_alertas_activas(
    db: Session = Depends(get_db),
    token_data: dict = Depends(get_current_token)
):
    """Obtiene todas las emergencias que necesitan atención en la central"""
    
    # Validar que solo el operador vea esto (Opcional por ahora, recomendado a futuro)
    # if token_data.get("rol") != "Operador_Central": ...

    # Buscar peticiones en estado pendiente o en triaje
    # Usamos joinedload para traer la ubicación en la misma consulta
    peticiones = db.query(Peticion).options(joinedload(Peticion.ubicacion)).filter(
        Peticion.estado_code.in_(["pendiente", "en_triaje"])
    ).all()
    
    resultado = []
    for p in peticiones:
        # Extraemos coordenadas si la petición tiene ubicación registrada
        lat = p.ubicacion.latitud if p.ubicacion else None
        lng = p.ubicacion.longitud if p.ubicacion else None
        
        resultado.append({
            "id": str(p.id),
            "usuario_id": str(p.usuario_id),
            "estado": p.estado_code,
            "lat": lat,
            "lng": lng,
            # Si tienes un campo de fecha, envíalo (ej. p.fecha_creacion), sino envíamos "Ahora"
            "fecha": "Ahora" 
        })
    
    return resultado

# 3. Endpoint para que el Operador despache una unidad
@router.put("/{peticion_id}/despachar")
def despachar_alerta(
    peticion_id: str,
    payload: DespachoRequest,
    db: Session = Depends(get_db),
    token_data: dict = Depends(get_current_token)
):
    """Asigna un profesional a la alerta (Máximo 1 misión activa por profesional)"""
    
    # 1. Verificar si el profesional ya tiene una misión en curso
    mision_activa = db.query(Peticion).filter(
        Peticion.profesional_id == payload.profesional_id,
        Peticion.estado_code == "despachada"
    ).first()
    
    if mision_activa:
        raise HTTPException(status_code=400, detail="Este profesional ya tiene una misión en curso.")

    # 2. Despachar
    peticion = db.query(Peticion).filter(Peticion.id == peticion_id).first()
    if not peticion:
        raise HTTPException(status_code=404, detail="Emergencia no encontrada")
        
    peticion.estado_code = "despachada"
    peticion.profesional_id = payload.profesional_id
    peticion.operador_id = token_data.get("sub") 
    
    db.commit()
    return {"message": "Unidad despachada", "estado": peticion.estado_code}
# 4. Endpoint para obtener el historial completo de emergencias (para auditoría de tiempos)
@router.get("/historial")
def get_historial_alertas(
    db: Session = Depends(get_db),
    # token_data: dict = Depends(get_current_token) # Opcional: Proteger para admins
):
    """Obtiene el historial completo de emergencias para auditoría de tiempos"""
    # Obtenemos todas las peticiones ordenadas de la más reciente a la más antigua
    peticiones = db.query(Peticion).order_by(Peticion.creado_en.desc()).all()
    
    resultado = []
    for p in peticiones:
        resultado.append({
            "id": str(p.id)[:8], # Solo los primeros 8 caracteres para que la tabla sea legible
            "estado": p.estado_code,
            "fecha_creacion": p.creado_en.isoformat() if p.creado_en else None,
            "victima_id": str(p.usuario_id)[:8],
            "profesional_id": str(p.profesional_id)[:8] if p.profesional_id else "Sin asignar"
        })
    return resultado
# ----------- App Profesional: Consultar Misión Asignada -----------
@router.get("/mision")
def get_mision_actual(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    El celular del profesional consulta si tiene alguna víctima asignada.
    """
    # Buscamos la primera petición despachada a este profesional
    peticion = db.query(Peticion).options(joinedload(Peticion.ubicacion)).filter(
        Peticion.profesional_id == str(current_user.id),
        Peticion.estado_code == "despachada"
    ).first()

    if not peticion:
        return None # Devuelve null/None si está libre y patrullando
    
    # Si tiene misión, devolvemos las coordenadas de la víctima
    lat = peticion.ubicacion.latitud if peticion.ubicacion else None
    lng = peticion.ubicacion.longitud if peticion.ubicacion else None
        
    return {
        "mision_id": str(peticion.id),
        "victima_id": str(peticion.usuario_id),
        "lat": lat,
        "lng": lng,
        "mensaje": peticion.mensaje or "Emergencia (Botón de Pánico)",
        "estado": peticion.estado_code
    }
@router.put("/{peticion_id}/resolver")
def resolver_mision(
    peticion_id: str, 
    payload: FinalizarMisionRequest,
    db: Session = Depends(get_db)
):
    """Marca una emergencia como resuelta y guarda el informe en su tabla."""
    peticion = db.query(Peticion).filter(Peticion.id == peticion_id).first()
    
    if not peticion:
        raise HTTPException(status_code=404, detail="Misión no encontrada")
        
    foto_url = None
    if payload.foto_base64:
        try:
            # Usamos la nueva función dedicada a imágenes
            foto_url = storage_service.upload_base64_image(payload.foto_base64) 
        except Exception as e:
            print(f"Error subiendo foto a Cloudinary: {e}")

    # 1. Crear el registro en la nueva tabla normalizada
    nuevo_informe = InformeMision(
        peticion_id=peticion.id,
        detalle_resolucion=payload.informe,
        foto_url=foto_url
    )
    db.add(nuevo_informe)

    # 2. Actualizar el estado de la Petición
    peticion.estado_code = "resuelta"
    peticion.finalizado_en = datetime.utcnow()
    
    db.commit()
    
    return {"mensaje": "Misión finalizada con éxito y reporte guardado", "estado": "resuelta"}
