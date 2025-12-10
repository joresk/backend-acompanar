from typing import List, Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.guia import GuiaSchema
from app.crud import crud_guia

router = APIRouter()

@router.get("/", response_model=List[GuiaSchema])
def read_guias(
    db: Session = Depends(get_db)
    # Opcional: current_user = Depends(deps.get_current_active_user)
) -> Any:
    """
    Obtiene todas las guías, sus items y las URLs de imágenes.
    """
    guias = crud_guia.get_all_guias_with_items(db)
    return guias