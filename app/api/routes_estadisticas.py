from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List

from app.api.deps import get_db, get_current_admin
from app.crud import crud_estadisticas
from app.schemas.estadisticas import TopFaqResponse, TopCentroResponse

router = APIRouter()

@router.get("/guias/top", response_model=List[TopFaqResponse])
def get_top_guias(
    limit: int = Query(5, ge=1, le=50),
    db: Session = Depends(get_db),
    # Descomentar la siguiente línea para restringir a administradores
    # current_user = Depends(get_current_admin)
):
    """
    Obtener las guías (FAQs) más consultadas.
    """
    return crud_estadisticas.get_top_faqs(db, limit=limit)

@router.get("/centros/top", response_model=List[TopCentroResponse])
def get_top_centros(
    limit: int = Query(5, ge=1, le=50),
    db: Session = Depends(get_db),
    # Descomentar la siguiente línea para restringir a administradores
    # current_user = Depends(get_current_active_admin)
):
    """
    Obtener los centros de ayuda más consultados.
    """
    return crud_estadisticas.get_top_centros(db, limit=limit)
