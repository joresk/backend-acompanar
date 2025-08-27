from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from fastapi import HTTPException, status
from uuid import UUID

from app.models.contact import Contact
from app.models.user import User
from app.schemas.contact import ContactCreate, ContactUpdate

class CRUDContact:
    def create(
        self, 
        db: Session, 
        *, 
        obj_in: ContactCreate, 
        user_id: UUID
    ) -> Contact:
        """
        Crear un nuevo contacto para un usuario
        - Máximo 3 contactos por usuario
        - El primer contacto es automáticamente primario
        """
        # Verificar límite de contactos
        contact_count = db.query(func.count(Contact.id)).filter(
            Contact.usuario_id == user_id
        ).scalar()
        
        if contact_count >= 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Máximo 3 contactos permitidos por usuario"
            )
        
        # Crear contacto
        db_obj = Contact(
            usuario_id=user_id,
            nombre=obj_in.nombre,
            telefono=obj_in.telefono
        )
        
        # Si es el primer contacto, marcarlo como primario internamente
        if contact_count == 0:
            db_obj._is_primary = True
        
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        
        return db_obj
    
    def get(self, db: Session, id: UUID) -> Optional[Contact]:
        """Obtener un contacto por ID"""
        return db.query(Contact).filter(Contact.id == id).first()
    
    def get_by_user(
        self, 
        db: Session, 
        *, 
        user_id: UUID, 
        skip: int = 0, 
        limit: int = 3
    ) -> List[Contact]:
        """Obtener todos los contactos de un usuario"""
        contacts = db.query(Contact).filter(
            Contact.usuario_id == user_id
        ).order_by(
            Contact.id.asc()  # Ordenar por ID (el primero será primario)
        ).offset(skip).limit(limit).all()
        
        # Marcar el primero como primario
        if contacts:
            contacts[0]._is_primary = True
            for contact in contacts[1:]:
                contact._is_primary = False
        
        return contacts
    
    def get_primary_contact(
        self, 
        db: Session, 
        *, 
        user_id: UUID
    ) -> Optional[Contact]:
        """Obtener el contacto principal de un usuario (el primero creado)"""
        contact = db.query(Contact).filter(
            Contact.usuario_id == user_id
        ).order_by(Contact.id.asc()).first()
        
        if contact:
            contact._is_primary = True
        
        return contact
    
    def update(
        self,
        db: Session,
        *,
        db_obj: Contact,
        obj_in: ContactUpdate
    ) -> Contact:
        """Actualizar un contacto"""
        update_data = obj_in.dict(exclude_unset=True)
        
        for field in update_data:
            setattr(db_obj, field, update_data[field])
        
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def remove(self, db: Session, *, id: UUID, user_id: UUID) -> Contact:
        """Eliminar un contacto"""
        obj = db.query(Contact).filter(
            and_(
                Contact.id == id,
                Contact.usuario_id == user_id
            )
        ).first()
        
        if not obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Contacto no encontrado"
            )
        
        db.delete(obj)
        db.commit()
        
        return obj
    
    def remove_all(self, db: Session, *, user_id: UUID) -> int:
        """Eliminar todos los contactos de un usuario"""
        count = db.query(Contact).filter(
            Contact.usuario_id == user_id
        ).delete()
        db.commit()
        return count
    
    def sync_contacts(
        self,
        db: Session,
        *,
        user_id: UUID,
        contacts_data: List[ContactCreate]
    ) -> List[Contact]:
        """
        Sincronizar contactos desde la app
        - Elimina todos los contactos existentes
        - Crea los nuevos contactos
        """
        # Validar máximo 3 contactos
        if len(contacts_data) > 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Máximo 3 contactos permitidos"
            )
        
        # Eliminar contactos existentes
        self.remove_all(db, user_id=user_id)
        
        # Crear nuevos contactos
        new_contacts = []
        for idx, contact_data in enumerate(contacts_data):
            contact = Contact(
                usuario_id=user_id,
                nombre=contact_data.nombre,
                telefono=contact_data.telefono
            )
            contact._is_primary = (idx == 0)  # El primero es primario
            db.add(contact)
            new_contacts.append(contact)
        
        db.commit()
        
        # Refrescar todos los contactos
        for contact in new_contacts:
            db.refresh(contact)
        
        return new_contacts
    
    def count_by_user(self, db: Session, *, user_id: UUID) -> int:
        """Contar contactos de un usuario"""
        return db.query(func.count(Contact.id)).filter(
            Contact.usuario_id == user_id
        ).scalar() or 0
    
    def validate_ownership(
        self,
        db: Session,
        *,
        contact_id: UUID,
        user_id: UUID
    ) -> bool:
        """Verificar que un contacto pertenece a un usuario"""
        contact = db.query(Contact).filter(
            and_(
                Contact.id == contact_id,
                Contact.usuario_id == user_id
            )
        ).first()
        return contact is not None
    # NUEVO MÉTODO
    def set_as_primary(self, db: Session, *, contact_id: UUID, user_id: UUID) -> Contact:
        """Establece un contacto como primario moviéndolo al principio de la lista."""
        
        # 1. Obtener todos los contactos del usuario
        all_contacts = db.query(Contact).filter(Contact.usuario_id == user_id).order_by(Contact.id.asc()).all()
        
        # 2. Encontrar el contacto a mover
        contact_to_set_primary = None
        other_contacts = []
        for c in all_contacts:
            if c.id == contact_id:
                contact_to_set_primary = c
            else:
                other_contacts.append(c)

        if not contact_to_set_primary:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Contacto no encontrado")

        # 3. Reconstruir la lista
        new_ordered_list = [contact_to_set_primary] + other_contacts
        
        # 4. Eliminar todos los contactos existentes (usando tu método remove_all)
        self.remove_all(db, user_id=user_id)
        
        # 5. Volver a crearlos en el nuevo orden
        created_contacts = []
        for contact_data in new_ordered_list:
            new_contact = Contact(
                usuario_id=user_id,
                nombre=contact_data.nombre,
                telefono=contact_data.telefono
            )
            db.add(new_contact)
            created_contacts.append(new_contact)
            
        db.commit()

        # Refrescar para obtener los nuevos IDs
        for c in created_contacts:
            db.refresh(c)
            
        # Devolver el contacto que ahora es primario (el primero de la nueva lista)
        return created_contacts[0]
crud_contact = CRUDContact()