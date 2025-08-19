from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.api.deps import get_db, get_current_user_optional
from app.models.user import User
from app.schemas.centro import CentroOut, CentroListResponse
from app.crud.crud_centro import crud_centro

router = APIRouter()

@router.get("/", response_model=CentroListResponse)
def get_centros(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user_optional)
):
    """
    Obtener lista de centros de ayuda disponibles.
    """
    centros = crud_centro.get_multi(db, skip=skip, limit=limit)
    return CentroListResponse(
        centros=centros,
        total=len(centros)
    )

@router.get("/{centro_id}", response_model=CentroOut)
def get_centro(
    centro_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """
    Obtener información detallada de un centro de ayuda.
    """
    centro = crud_centro.get(db, id=centro_id)
    if not centro:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Centro de ayuda no encontrado"
        )
    return centro