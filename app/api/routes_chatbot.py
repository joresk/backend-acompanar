from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.db.session import get_db
from app.models.user import User
from uuid import UUID
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

class ChatbotEvaluarRequest(BaseModel):
    id_sesion: str
    nivel_riesgo: int  # 1 to 5
    tipo_violencia: str

@router.post("/evaluar")
def evaluar_test(payload: ChatbotEvaluarRequest, db: Session = Depends(get_db)):
    try:
        user_uuid = UUID(payload.id_sesion)
    except ValueError:
        raise HTTPException(status_code=400, detail="id_sesion no es un UUID válido")
        
    user = db.query(User).filter(User.id == user_uuid).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
    # Registrar en logs del sistema para auditoría de asistencia
    logger.info(
        f"AUDITORÍA CHATBOT TEST: Usuario {user.id} ({user.full_name}) completó el test de detección. "
        f"Nivel de Riesgo: {payload.nivel_riesgo}/5. Tipo de Violencia: {payload.tipo_violencia}."
    )
    
    # Actualizar automáticamente el perfil de seguridad
    from app.models.perfil_seguridad import PerfilSeguridad
    from datetime import datetime
    
    perfil = db.query(PerfilSeguridad).filter(PerfilSeguridad.usuario_id == user_uuid).first()
    if perfil:
        perfil.nivel_riesgo = payload.nivel_riesgo
        perfil.tipo_violencia = payload.tipo_violencia
        perfil.ultima_interaccion = datetime.utcnow()
    else:
        perfil = PerfilSeguridad(
            usuario_id=user_uuid,
            nivel_riesgo=payload.nivel_riesgo,
            tipo_violencia=payload.tipo_violencia,
            ultima_interaccion=datetime.utcnow()
        )
        db.add(perfil)
    db.commit()
    
    # Generar recomendaciones según nivel de riesgo
    recomendaciones = ""
    if payload.nivel_riesgo >= 4:
        recomendaciones = "Tu situación indica un nivel de riesgo crítico. Te sugerimos acudir a la Oficina de Violencia Doméstica (OVD) en Pasaje Vélez Sarsfield 450 (abierta 24hs) o llamar al 911 de inmediato. No estás sola."
    elif payload.nivel_riesgo >= 2:
        recomendaciones = "Tu situación indica un nivel de riesgo moderado. Te aconsejamos buscar asesoramiento y acompañamiento en la Secretaría de la Mujer o llamar a la Línea 144 (atención gratuita las 24hs)."
    else:
        recomendaciones = "Tu situación indica un nivel de riesgo bajo. Mantente informada y consulta nuestra guía de recursos de apoyo en cualquier momento."
        
    return {
        "success": True,
        "nivel_riesgo": payload.nivel_riesgo,
        "tipo_violencia": payload.tipo_violencia,
        "recomendaciones": recomendaciones
    }

class PerfilActualizarRequest(BaseModel):
    id_sesion: str
    notas_contexto: str
    nivel_riesgo: int
    tipo_violencia: str

@router.get("/perfil/{id_usuario}")
def obtener_perfil(id_usuario: str, db: Session = Depends(get_db)):
    from app.models.perfil_seguridad import PerfilSeguridad
    try:
        user_uuid = UUID(id_usuario)
    except ValueError:
        raise HTTPException(status_code=400, detail="id_usuario no es un UUID válido")
        
    perfil = db.query(PerfilSeguridad).filter(PerfilSeguridad.usuario_id == user_uuid).first()
    if not perfil:
        return {"notas_contexto": "Ninguno", "nivel_riesgo": 1, "tipo_violencia": "Ninguno"}
    return {
        "nivel_riesgo": perfil.nivel_riesgo,
        "notas_contexto": perfil.notas_contexto if perfil.notas_contexto else "Ninguno",
        "tipo_violencia": perfil.tipo_violencia if perfil.tipo_violencia else "Ninguno"
    }

@router.post("/perfil/actualizar")
def actualizar_perfil(payload: PerfilActualizarRequest, db: Session = Depends(get_db)):
    from app.models.perfil_seguridad import PerfilSeguridad
    from datetime import datetime
    try:
        user_uuid = UUID(payload.id_sesion)
    except ValueError:
        raise HTTPException(status_code=400, detail="id_sesion no es un UUID válido")
        
    perfil = db.query(PerfilSeguridad).filter(PerfilSeguridad.usuario_id == user_uuid).first()
    if perfil:
        perfil.nivel_riesgo = payload.nivel_riesgo
        perfil.tipo_violencia = payload.tipo_violencia
        perfil.ultima_interaccion = datetime.utcnow()
        if not perfil.notas_contexto or perfil.notas_contexto == 'Ninguno' or perfil.notas_contexto.strip() == '':
            perfil.notas_contexto = payload.notas_contexto
        else:
            perfil.notas_contexto = f"{perfil.notas_contexto}\n---\n{payload.notas_contexto}"
    else:
        perfil = PerfilSeguridad(
            usuario_id=user_uuid,
            nivel_riesgo=payload.nivel_riesgo,
            notas_contexto=payload.notas_contexto,
            tipo_violencia=payload.tipo_violencia,
            ultima_interaccion=datetime.utcnow()
        )
        db.add(perfil)
    db.commit()
    
    return {"success": True, "message": "Perfil de seguridad actualizado correctamente"}

class FastRiskRequest(BaseModel):
    mensaje: str

@router.post("/fast-risk")
def evaluar_fast_risk(payload: FastRiskRequest):
    from app.services.nlp_service import nlp_service
    try:
        resultado = nlp_service.evaluar_latencia_cero(payload.mensaje)
        return resultado
    except Exception as e:
        logger.error(f"Error NLP Fast Risk: {e}")
        # En caso de error, delegamos al triage normal devolviendo False
        return {"es_emergencia": False, "score": 0.0}

@router.post("/trigger-followup")
def trigger_followup(db: Session = Depends(get_db)):
    from app.models.perfil_seguridad import PerfilSeguridad
    from app.models.ubicacion import Ubicacion
    from app.models.peticion import Peticion
    from datetime import datetime, timedelta
    try:
        diez_mins_atras = datetime.utcnow() - timedelta(minutes=10)
        veinticuatro_hs_atras = datetime.utcnow() - timedelta(hours=24)
        
        candidatos = db.query(PerfilSeguridad).filter(
            PerfilSeguridad.nivel_riesgo >= 4,
            PerfilSeguridad.ultima_interaccion < diez_mins_atras,
            (PerfilSeguridad.ultimo_checkin == None) | (PerfilSeguridad.ultimo_checkin < veinticuatro_hs_atras)
        ).all()
        
        alertas_creadas = 0
        
        for perfil in candidatos:
            uid = perfil.usuario_id
            
            # Crear ubicación dummy ya que puede ser requerida por la base de datos
            ubicacion = Ubicacion(direccion='Desconocida (Follow-up automático)', latitud=0, longitud=0)
            db.add(ubicacion)
            db.flush() # para obtener el ID de ubicacion
            
            # Crear peticion (Alerta para el Operador)
            peticion = Peticion(
                usuario_id=uid,
                ubicacion_id=ubicacion.id,
                estado_code='pendiente',
                mensaje='Alerta Automática: Sesión de chatbot de alto riesgo abandonada sin resolución.',
                creado_en=datetime.utcnow()
            )
            db.add(peticion)
            
            # Actualizar ultimo_checkin
            perfil.ultimo_checkin = datetime.utcnow()
            
            alertas_creadas += 1
            
        db.commit()
        return {"success": True, "alertas_creadas": alertas_creadas}
    except Exception as e:
        db.rollback()
        logger.error(f"Error en trigger_followup: {e}")
        return {"success": False, "error": str(e)}
