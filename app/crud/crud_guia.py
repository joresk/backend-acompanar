from typing import List
from sqlalchemy.orm import Session, joinedload
from app.models.guia import Guia

def get_all_guias_with_items(db: Session) -> List[Guia]:
    # joinedload optimiza la consulta trayendo items e imágenes en una sola query
    return db.query(Guia).options(joinedload(Guia.items)).all()