from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID # CAMBIO: Importar UUID

from app.api.deps import get_current_user, get_db, get_current_token
from app.crud.crud_contact import crud_contact
from app.models.user import User
from app.schemas.contact import (
    ContactCreate,
    ContactOut,
    ContactUpdate,
    ContactListResponse,
    ContactSyncRequest,
    ContactSyncResponse
)

router = APIRouter()

@router.post("/", response_model=ContactOut, status_code=status.HTTP_201_CREATED)
def create_contact(
    *,
    db: Session = Depends(get_db),
    contact_in: ContactCreate,
    current_user: User = Depends(get_current_user)
):
    """
    Crear un nuevo contacto de emergencia.
    - Máximo 3 contactos por usuario
    - El primer contacto es automáticamente el principal
    """
    try:
        contact = crud_contact.create(
            db=db,
            obj_in=contact_in,
            user_id=current_user.id
        )
        return contact
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear contacto: {str(e)}"
        )

@router.get("/", response_model=ContactListResponse)
def get_contacts(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 3,
    current_user: User = Depends(get_current_user)
):
    """
    Obtener todos los contactos del usuario actual.
    Ordenados por: primario primero, luego por fecha de creación.
    """
    contacts = crud_contact.get_by_user(
        db=db,
        user_id=current_user.id,
        skip=skip,
        limit=limit
    )
    
    return ContactListResponse(
        contacts=contacts,
        total=len(contacts)
    )

@router.get("/{contact_id}", response_model=ContactOut)
def get_contact(
    *,
    db: Session = Depends(get_db),
    contact_id: UUID, # CAMBIO: int a UUID
    current_user: User = Depends(get_current_user)
):
    """
    Obtener un contacto específico por ID.
    Solo si pertenece al usuario actual.
    """
    contact = crud_contact.get(db=db, id=contact_id)
    
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contacto no encontrado"
        )
    
    # CAMBIO: usuario_id es el nombre del campo en el modelo, no user_id
    if contact.usuario_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para ver este contacto"
        )
    
    return contact

@router.put("/{contact_id}", response_model=ContactOut)
def update_contact(
    *,
    db: Session = Depends(get_db),
    contact_id: UUID, # CAMBIO: int a UUID
    contact_in: ContactUpdate,
    current_user: User = Depends(get_current_user)
):
    """
    Actualizar un contacto existente.
    Solo el propietario puede actualizar.
    """
    contact = crud_contact.get(db=db, id=contact_id)
    
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contacto no encontrado"
        )
    
    # CAMBIO: usuario_id es el nombre del campo en el modelo, no user_id
    if contact.usuario_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para actualizar este contacto"
        )
    
    contact = crud_contact.update(
        db=db,
        db_obj=contact,
        obj_in=contact_in
    )
    return contact

@router.delete("/{contact_id}", response_model=ContactOut)
def delete_contact(
    *,
    db: Session = Depends(get_db),
    contact_id: UUID, # CAMBIO: int a UUID
    current_user: User = Depends(get_current_user)
):
    """
    Eliminar un contacto.
    Si era primario, el siguiente se vuelve primario automáticamente.
    """
    contact = crud_contact.get(db=db, id=contact_id)
    
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contacto no encontrado"
        )
    
    # CAMBIO: usuario_id es el nombre del campo en el modelo, no user_id
    if contact.usuario_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para eliminar este contacto"
        )
    
    contact = crud_contact.remove(db=db, id=contact_id)
    return contact

@router.post("/{contact_id}/set-primary", response_model=ContactOut)
def set_primary_contact(
    *,
    db: Session = Depends(get_db),
    contact_id: UUID, # CAMBIO: int a UUID
    current_user: User = Depends(get_current_user)
):
    """
    Establecer un contacto como primario.
    El contacto primario anterior dejará de serlo.
    """
    if not crud_contact.validate_ownership(
        db=db,
        contact_id=contact_id,
        user_id=current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para modificar este contacto"
        )
    
    contact = crud_contact.set_as_primary(
        db=db,
        contact_id=contact_id,
        user_id=current_user.id
    )
    return contact

@router.post("/sync", response_model=ContactSyncResponse)
def sync_contacts(
    *,
    db: Session = Depends(get_db),
    sync_request: ContactSyncRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Sincronizar contactos desde la app móvil.
    Reemplaza todos los contactos existentes con los nuevos.
    """
    try:
        contacts = crud_contact.sync_contacts(
            db=db,
            user_id=current_user.id,
            contacts_data=sync_request.contacts
        )
        
        return ContactSyncResponse(
            synced=True,
            contacts=contacts,
            message=f"Sincronizados {len(contacts)} contactos correctamente"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al sincronizar contactos: {str(e)}"
        )