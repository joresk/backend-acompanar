from typing import List, Optional
from sqlalchemy.orm import Session
from uuid import UUID

from app.models.centro import Centro
from app.schemas.centro import CentroOut

class CRUDCentro:
    def get(self, db: Session, id: UUID) -> Optional[Centro]:
        """
        Obtener un centro por ID
        """
        return db.query(Centro).filter(Centro.id == id).first()
    
    def get_multi(self, db: Session, *, skip: int = 0, limit: int = 100) -> List[Centro]:
        """
        Obtener una lista de centros
        """
        return db.query(Centro).offset(skip).limit(limit).all()
    
crud_centro = CRUDCentro()