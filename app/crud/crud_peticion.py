from typing import List, Optional
from sqlalchemy.orm import Session
from uuid import UUID
from datetime import datetime, timedelta

from app.models.peticion import Peticion
from app.models.ubicacion import Ubicacion
from app.models.contact import Contact
from app.schemas.contact import UbicacionCreate, PeticionCreate

class CRUDPeticion:
    
    def create_emergency_alert(
        self,
        db: Session,
        *,
        user_id: UUID,
        contact_ids: Optional[List[UUID]] = None,
        ubicacion_data: Optional[UbicacionCreate] = None,
        mensaje: Optional[str] = None
    ) -> List[Peticion]:
        """
        Crear peticiones de emergencia para uno o más contactos
        """
        # Si no se especifican contactos, obtener todos los del usuario
        if not contact_ids:
            contacts = db.query(Contact).filter(
                Contact.usuario_id == user_id
            ).all()
            contact_ids = [c.id for c in contacts]
        else:
            # Verificar que los contactos pertenecen al usuario
            contacts = db.query(Contact).filter(
                Contact.id.in_(contact_ids),
                Contact.usuario_id == user_id
            ).all()
            contact_ids = [c.id for c in contacts]
        
        if not contact_ids:
            raise ValueError("No hay contactos configurados")
        
        # Crear ubicación si se proporciona
        ubicacion = None
        if ubicacion_data:
            ubicacion = Ubicacion(
                direccion=ubicacion_data.direccion,
                latitud=ubicacion_data.latitud,
                longitud=ubicacion_data.longitud
            )
            db.add(ubicacion)
            db.flush()  # Para obtener el ID
        
        # Crear una petición por cada contacto
        peticiones = []
        for contact_id in contact_ids:
            peticion = Peticion(
                usuario_id=user_id,
                contacto_id=contact_id,
                ubicacion_id=ubicacion.id if ubicacion else None,
                estado_code='pendiente'  # Estado inicial
            )
            db.add(peticion)
            peticiones.append(peticion)
        
        db.commit()
        
        # Refrescar objetos
        for peticion in peticiones:
            db.refresh(peticion)
        
        return peticiones
    
    def get_user_peticiones(
        self,
        db: Session,
        *,
        user_id: UUID,
        limit: int = 10
    ) -> List[Peticion]:
        """Obtener las últimas peticiones de un usuario"""
        return db.query(Peticion).filter(
            Peticion.usuario_id == user_id
        ).order_by(
            Peticion.creado_en.desc()
        ).limit(limit).all()
    
    def get_recent_peticion_count(
        self,
        db: Session,
        *,
        user_id: UUID,
        minutes: int = 1
    ) -> int:
        """Contar peticiones recientes (para rate limiting)"""
        time_threshold = datetime.utcnow() - timedelta(minutes=minutes)
        
        return db.query(Peticion).filter(
            Peticion.usuario_id == user_id,
            Peticion.creado_en >= time_threshold
        ).count()
    
    def can_send_alert(
        self,
        db: Session,
        *,
        user_id: UUID,
        max_per_minute: int = 1
    ) -> bool:
        """Verificar si el usuario puede enviar una alerta (rate limiting)"""
        recent_count = self.get_recent_peticion_count(
            db, 
            user_id=user_id, 
            minutes=1
        )
        return recent_count < max_per_minute
    
    def update_peticion_estado(
        self,
        db: Session,
        *,
        peticion_id: UUID,
        estado_code: str
    ) -> Peticion:
        """Actualizar el estado de una petición"""
        peticion = db.query(Peticion).filter(
            Peticion.id == peticion_id
        ).first()
        
        if peticion:
            peticion.estado_code = estado_code
            db.commit()
            db.refresh(peticion)
        
        return peticion
    
    def mark_as_sent(
        self,
        db: Session,
        *,
        peticion_ids: List[UUID]
    ):
        """Marcar peticiones como enviadas"""
        db.query(Peticion).filter(
            Peticion.id.in_(peticion_ids)
        ).update(
            {"estado_code": "atendida"},
            synchronize_session=False
        )
        db.commit()

crud_peticion = CRUDPeticion()