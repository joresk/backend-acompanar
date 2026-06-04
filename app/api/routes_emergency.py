from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session, joinedload
import math, json, os, logging
from sqlalchemy import and_
from typing import Optional, List
from datetime import datetime, timedelta
from uuid import UUID
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
from app.schemas.chatbot import ChatbotTriageRequest, ChatbotTriageResponse
from app.models.peticion import Peticion
from app.models.ubicacion import Ubicacion
from app.services.storage_service import storage_service
from groq import Groq
from fastapi import WebSocket, WebSocketDisconnect
from app.api.websocket_manager import manager

logger = logging.getLogger(__name__)
router = APIRouter()
client = Groq()

# Interruptor global en memoria (Se reinicia si el servidor se apaga)
AUTO_DISPATCH_ENABLED = False
# Diccionario en memoria para bloqueos de operadores (Sincronización Sala de Control)
LOCKED_ALERTS = {} # formato: { peticion_id: {"operator_id": str, "operator_name": str, "expires_at": datetime} }

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
    background_tasks: BackgroundTasks,
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
            # ---> INICIO AUTO-DESPACHO AUTÓNOMO
            if AUTO_DISPATCH_ENABLED and ubicacion_id:
                # 1. Buscar profesionales activos
                profesionales = db.query(User).filter(
                    User.rol == "Profesional_Terreno",
                    User.latitud_actual.isnot(None),
                    User.longitud_actual.isnot(None)
                ).all()

                profesional_mas_cercano = None
                distancia_minima = float('inf')

                for prof in profesionales:
                    # Verificar que no tenga otra misión activa
                    mision_activa = db.query(Peticion).filter(
                        Peticion.profesional_id == prof.id,
                        Peticion.estado_code == "despachada"
                    ).first()

                    if not mision_activa:
                        # Calcular distancia
                        dist = calcular_distancia(
                            report_request.location.latitude, 
                            report_request.location.longitude,
                            float(prof.latitud_actual), 
                            float(prof.longitud_actual)
                        )
                        # Asignar si está a menos de 5 km (o tu límite de cobertura)
                        if dist < 5.0 and dist < distancia_minima:
                            distancia_minima = dist
                            profesional_mas_cercano = prof

                # Si encontramos a alguien, le asignamos la alerta central instantáneamente
                if profesional_mas_cercano:
                    peticion_central.estado_code = "despachada"
                    peticion_central.profesional_id = profesional_mas_cercano.id
            # ---> FIN AUTO-DESPACHO AUTÓNOMO
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
        
        # Notificar a la Sala de Control en tiempo real
        background_tasks.add_task(manager.broadcast_alerts_update)

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
    # Usamos joinedload para traer la ubicación y el usuario en la misma consulta
    peticiones = db.query(Peticion).options(
        joinedload(Peticion.ubicacion),
        joinedload(Peticion.usuario)
    ).filter(
        Peticion.estado_code.in_(["pendiente", "en_triaje"]), 
        Peticion.contacto_id == None
    ).all()
    
    resultado = []
    for p in peticiones:
        # Extraemos coordenadas si la petición tiene ubicación registrada
        lat = p.ubicacion.latitud if p.ubicacion else None
        lng = p.ubicacion.longitud if p.ubicacion else None
        direccion = p.ubicacion.direccion if p.ubicacion else "Ubicación desconocida"
        
        # Extraemos datos del usuario (víctima)
        is_anonymous = p.usuario.is_anonymous if p.usuario else False
        nombre_victima = "Usuario Anónimo" if is_anonymous else (p.usuario.full_name if p.usuario else "Desconocido")
        telefono = p.usuario.phone if p.usuario and not is_anonymous else None

        # Verificar bloqueo activo
        lock_info = LOCKED_ALERTS.get(str(p.id))
        locked_by = None
        if lock_info:
            if datetime.utcnow() > lock_info["expires_at"]:
                del LOCKED_ALERTS[str(p.id)] # Expiró el bloqueo
            else:
                locked_by = lock_info["operator_name"]

        resultado.append({
            "id": str(p.id),
            "usuario_id": str(p.usuario_id),
            "estado": p.estado_code,
            "lat": lat,
            "lng": lng,
            "direccion": direccion,
            "nombre_victima": nombre_victima,
            "telefono": telefono,
            "is_anonymous": is_anonymous,
            "fecha": p.creado_en.isoformat() if p.creado_en else None,
            "audio_url": p.audio,
            "locked_by": locked_by
        })
    
    return resultado

@router.post("/{peticion_id}/lock")
def lock_alerta(
    peticion_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """Bloquea temporalmente una alerta para que otro operador no la asuma"""
    LOCKED_ALERTS[peticion_id] = {
        "operator_id": str(current_user.id),
        "operator_name": current_user.full_name or "Operador",
        "expires_at": datetime.utcnow() + timedelta(seconds=60)
    }
    background_tasks.add_task(manager.broadcast_alerts_update)
    return {"success": True}

@router.post("/{peticion_id}/unlock")
def unlock_alerta(
    peticion_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """Libera el bloqueo de una alerta"""
    if peticion_id in LOCKED_ALERTS:
        if LOCKED_ALERTS[peticion_id]["operator_id"] == str(current_user.id):
            del LOCKED_ALERTS[peticion_id]
            background_tasks.add_task(manager.broadcast_alerts_update)
    return {"success": True}

@router.put("/{peticion_id}/despachar")
def despachar_alerta(
    peticion_id: str,
    payload: DespachoRequest,
    background_tasks: BackgroundTasks,
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
    
    # Liberar el bloqueo si existía
    if peticion_id in LOCKED_ALERTS:
        del LOCKED_ALERTS[peticion_id]
    
    db.commit()
    
    # Notificar a la Sala de Control web
    background_tasks.add_task(manager.broadcast_alerts_update)
    
    return {"message": "Unidad despachada", "estado": peticion.estado_code}

# 3.5. Endpoint WebSocket para el Radar en Tiempo Real
@router.websocket("/ws/radar")
async def websocket_radar_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Mantener conexión viva y escuchar mensajes si hubiera
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
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
        "nombre_victima": peticion.usuario.full_name if peticion.usuario else "Desconocido",
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

@router.get("/misiones/historial/me")
def get_historial_profesional(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtener el historial de misiones cerradas y métricas para el Dashboard del Profesional.
    Calcula automáticamente el SLA (Tiempo de respuesta).
    """
    # 1. Buscar misiones asignadas a este profesional que ya estén terminadas
    misiones = db.query(Peticion).options(
        joinedload(Peticion.ubicacion)
    ).filter(
        Peticion.profesional_id == str(current_user.id),
        Peticion.estado_code.in_(["resuelta", "derivada"]) # Ajustar si tienes otros estados finales
    ).order_by(Peticion.finalizado_en.desc()).all()

    total_misiones = len(misiones)
    tiempos_sla = []
    historial_response = []
    
    # 2. Procesar cada misión para la lista
    for p in misiones:
        # A. Cálculo de SLA individual
        sla_str = "--"
        if p.creado_en and p.finalizado_en:
            delta = p.finalizado_en - p.creado_en
            minutos = int(delta.total_seconds() // 60)
            segundos = int(delta.total_seconds() % 60)
            sla_str = f"{minutos}m {segundos}s"
            tiempos_sla.append(delta.total_seconds())

        # B. Formateo de fecha
        fecha_str = p.finalizado_en.strftime("%d %b %Y, %H:%M hs") if p.finalizado_en else "Desconocida"
        
        # C. Anonimizar Zona (Protección de la víctima)
        zona_texto = "Zona no registrada"
        if p.ubicacion and p.ubicacion.direccion:
            # Tomamos la primera parte de la dirección antes de una coma para no dar la calle exacta
            partes = p.ubicacion.direccion.split(',')
            zona_texto = partes[0].strip() if len(partes) > 1 else p.ubicacion.direccion
        
        # D. Lógica visual para Android (Verde o Naranja)
        is_success = (p.estado_code == "resuelta")
        
        historial_response.append({
            "id": str(p.id),
            "date": fecha_str,
            "status": p.estado_code.capitalize(),
            "zone": zona_texto,
            "sla": sla_str,
            "isSuccess": is_success
        })
        
    # 3. Calcular SLA Promedio Global
    avg_sla_str = "0m 0s"
    if tiempos_sla:
        avg_sec = sum(tiempos_sla) / len(tiempos_sla)
        avg_min = int(avg_sec // 60)
        avg_s = int(avg_sec % 60)
        avg_sla_str = f"{avg_min}m {avg_s}s"

    # Devolvemos la estructura exacta que Android necesita
    return {
        "totalMissions": str(total_misiones),
        "avgSla": avg_sla_str,
        "history": historial_response
    }
from pydantic import BaseModel

# Creamos un esquema rápido para recibir el Base64
class AudioUploadRequest(BaseModel):
    audio_base64: str

@router.patch("/{peticion_id}/audio")
def upload_deferred_audio(
    peticion_id: str,
    request: AudioUploadRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Sube y adjunta un archivo de audio a una emergencia que ya fue disparada previamente.
    (Arquitectura de Doble Impacto: Disparo instantáneo + Evidencia diferida).
    """
    # 1. Buscamos la petición principal
    peticion = db.query(Peticion).filter(Peticion.id == peticion_id).first()
    
    if not peticion:
        raise HTTPException(status_code=404, detail="Petición de emergencia no encontrada")

    # 2. Subimos el audio a Cloudinary (o el servicio que uses)
    try:
        audio_url = storage_service.upload_base64_audio(request.audio_base64)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error subiendo audio: {str(e)}")

    # 3. Actualizamos la petición principal con la URL
    peticion.audio = audio_url

    # 4. (Opcional) Si en tu lógica copiaste esta petición para los contactos, 
    # buscamos y actualizamos las copias vinculadas a este mismo origen
    #peticiones_vinculadas = db.query(Peticion).filter(
    #    Peticion.origen_peticion_id == peticion_id
    #).all()
    
    #for pv in peticiones_vinculadas:
    #    pv.audio_url = audio_url

    db.commit()

    return {"message": "Evidencia de audio adjuntada exitosamente", "audio_url": audio_url}

# Endpoint para que el Panel de Control (Streamlit/Web) encienda/apague el modo autónomo
@router.post("/toggle-auto-dispatch")
def toggle_auto_dispatch(estado: bool, background_tasks: BackgroundTasks, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    global AUTO_DISPATCH_ENABLED
    AUTO_DISPATCH_ENABLED = estado
    if AUTO_DISPATCH_ENABLED:
        run_auto_dispatch(db, background_tasks)
    return {"auto_dispatch": AUTO_DISPATCH_ENABLED}

def run_auto_dispatch(db: Session, background_tasks: BackgroundTasks):
    peticiones = db.query(Peticion).join(User, Peticion.usuario_id == User.id).options(
        joinedload(Peticion.ubicacion),
        joinedload(Peticion.usuario)
    ).filter(
        Peticion.estado_code.in_(["pendiente", "en_triaje"]),
        Peticion.contacto_id == None
    ).order_by(
        User.is_anonymous.asc(),
        Peticion.creado_en.asc()
    ).all()

    if not peticiones:
        return

    profesionales = db.query(User).filter(
        User.rol == "Profesional_Terreno",
        User.is_active == True,
        User.latitud_actual.isnot(None),
        User.longitud_actual.isnot(None)
    ).all()

    if not profesionales:
        return

    misiones_activas = db.query(Peticion.profesional_id).filter(
        Peticion.estado_code == "despachada",
        Peticion.profesional_id.isnot(None)
    ).all()
    profesionales_ocupados = set([m[0] for m in misiones_activas])

    cambios = False

    for peticion in peticiones:
        if not peticion.ubicacion:
            continue

        profesional_mas_cercano = None
        distancia_minima = float('inf')

        for prof in profesionales:
            if str(prof.id) in profesionales_ocupados:
                continue

            dist = calcular_distancia(
                float(peticion.ubicacion.latitud),
                float(peticion.ubicacion.longitud),
                float(prof.latitud_actual),
                float(prof.longitud_actual)
            )

            if dist < 5.0 and dist < distancia_minima:
                distancia_minima = dist
                profesional_mas_cercano = prof

        if profesional_mas_cercano:
            peticion.estado_code = "despachada"
            peticion.profesional_id = str(profesional_mas_cercano.id)
            profesionales_ocupados.add(str(profesional_mas_cercano.id))
            cambios = True

    if cambios:
        db.commit()
        background_tasks.add_task(manager.broadcast_alerts_update)


@router.get("/auto-dispatch-status")
def get_auto_dispatch_status():
    return {"auto_dispatch": AUTO_DISPATCH_ENABLED}

@router.get("/monitor-estadisticas")
def get_monitor_estadisticas(db: Session = Depends(get_db)):
    # Despachadas
    despachadas = db.query(Peticion).options(
        joinedload(Peticion.usuario), joinedload(Peticion.profesional)
    ).filter(Peticion.estado_code == "despachada").all()
    
    # Resueltas (últimas 10)
    resueltas = db.query(Peticion).options(
        joinedload(Peticion.usuario), joinedload(Peticion.profesional)
    ).filter(Peticion.estado_code == "resuelta").order_by(Peticion.finalizado_en.desc()).limit(10).all()
    
    return {
       "despachadas": {
           "total": len(despachadas),
           "anonimas": len([p for p in despachadas if p.usuario and p.usuario.is_anonymous]),
           "registradas": len([p for p in despachadas if p.usuario and not p.usuario.is_anonymous]),
           "lista": [{
               "id": str(p.id),
               "victima": p.usuario.full_name if p.usuario else "Desconocido", 
               "profesional": p.profesional.full_name if p.profesional else "Desconocido", 
               "is_anonymous": p.usuario.is_anonymous if p.usuario else False
           } for p in despachadas]
       },
       "resueltas": {
           "total": len(resueltas),
           "lista": [{
               "id": str(p.id),
               "victima": p.usuario.full_name if p.usuario else "Desconocido", 
               "profesional": p.profesional.full_name if p.profesional else "Desconocido"
           } for p in resueltas]
       }
    }

# Función Haversine para cálculo en memoria
def calcular_distancia(lat1, lon1, lat2, lon2):
    R = 6371.0 # Radio de la Tierra en km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c
# Endpoint para el análisis semántico de mensajes usando Groq (Triage Bot)
@router.post("/triage-bot", response_model=ChatbotTriageResponse)
def triage_mensaje_bot(payload: ChatbotTriageRequest):
    """
    Envía el mensaje a Groq para un análisis semántico de riesgo y anonimización.
    """
    
    # El System Prompt es clave: le da a la IA su rol y fuerza la estructura de salida.
    system_prompt = """
    Eres un sistema de triage experto y empático en violencia de género para Tucumán. 
    Tu única tarea es analizar el mensaje de la usuaria y clasificarlo.
    
    DEBES devolver ÚNICAMENTE un objeto JSON válido con las siguientes 3 claves:
    1. "nivel_riesgo": Asigna estrictamente uno de estos valores:
       - "emergencia" (peligro físico inminente, golpes, armas, auxilio).
       - "boton_panico" (si pide explícitamente "salir", "borrar chat", "cancelar", "me pillaron").
       - "asesoramiento" (preguntas sobre denuncias, lugares, apoyo psicológico, dudas legales).
    2. "intencion": Una frase muy corta de lo que busca (ej. "informacion_denuncia", "purga_chat").
    3. "mensaje_anonimizado": El mismo mensaje original, pero reemplazando nombres propios, direcciones exactas, DNIs o teléfonos con la palabra [CENSURADO].

    Ejemplo de salida: {"nivel_riesgo": "asesoramiento", "intencion": "ubicacion_centros", "mensaje_anonimizado": "hola, busco ayuda cerca de [CENSURADO]"}
    """
    
    try:
        # Llamada a la API de Groq
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": payload.mensaje}
            ],
            model="llama-3.1-8b-instant", # Modelo rapidísimo y gratuito
            response_format={"type": "json_object"}, # Fuerza a que la salida sea JSON
            temperature=0.0 # Temperatura 0 para que no sea creativo, sino preciso y analítico
        )

        # Extraemos y leemos el JSON que generó Groq
        respuesta_json = json.loads(chat_completion.choices[0].message.content)

        return ChatbotTriageResponse(
            nivel_riesgo=respuesta_json.get("nivel_riesgo", "asesoramiento"),
            intencion=respuesta_json.get("intencion", "desconocida"),
            mensaje_anonimizado=respuesta_json.get("mensaje_anonimizado", payload.mensaje),
            id_sesion=payload.id_sesion,
            mensaje_original=payload.mensaje
        )

    except Exception as e:
        # Fallback de seguridad vital: Si Groq se cae, el sistema no colapsa, 
        # asume riesgo medio (asesoramiento) para que n8n pueda seguir respondiendo.
        print(f"Error crítico en Triage Groq: {e}")
        return ChatbotTriageResponse(
            nivel_riesgo="asesoramiento", 
            intencion="error_api_fallback",
            mensaje_anonimizado=payload.mensaje
        )
    