import os
import re

backend_dir = r"f:\0- Acompañar\Acompaniar-bf\backend-acompanar"
app_dir = os.path.join(backend_dir, "app")
models_dir = os.path.join(app_dir, "models")
schemas_dir = os.path.join(app_dir, "schemas")
crud_dir = os.path.join(app_dir, "crud")
api_dir = os.path.join(app_dir, "api")
db_dir = os.path.join(app_dir, "db")

# 1. Create app/models/faq.py
faq_model_code = """from sqlalchemy import Column, String, ForeignKey, Text, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from app.db.base import Base

class FaqCategory(Base):
    __tablename__ = "faq_categories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, unique=True, index=True, nullable=False)
    order = Column(Integer, default=0)

    faqs = relationship("FaqItem", back_populates="category", cascade="all, delete-orphan", order_by="FaqItem.order")


class FaqItem(Base):
    __tablename__ = "faq_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category_id = Column(UUID(as_uuid=True), ForeignKey("faq_categories.id"), nullable=False)
    question = Column(String, nullable=False)
    answer = Column(Text, nullable=False)
    action_phone = Column(String, nullable=True)
    order = Column(Integer, default=0)

    category = relationship("FaqCategory", back_populates="faqs")
"""
with open(os.path.join(models_dir, "faq.py"), "w", encoding="utf-8") as f:
    f.write(faq_model_code)

# 2. Add to models/__init__.py
init_path = os.path.join(models_dir, "__init__.py")
with open(init_path, "a", encoding="utf-8") as f:
    f.write("\nfrom app.models.faq import FaqCategory, FaqItem\n")

# 3. Create app/schemas/faq.py
faq_schema_code = """from pydantic import BaseModel, UUID4
from typing import List, Optional

class FaqItemBase(BaseModel):
    question: str
    answer: str
    action_phone: Optional[str] = None
    order: int = 0

class FaqItemResponse(FaqItemBase):
    id: UUID4
    category_id: UUID4

    class Config:
        orm_mode = True

class FaqCategoryBase(BaseModel):
    name: str
    order: int = 0

class FaqCategoryResponse(FaqCategoryBase):
    id: UUID4
    faqs: List[FaqItemResponse] = []

    class Config:
        orm_mode = True
"""
with open(os.path.join(schemas_dir, "faq.py"), "w", encoding="utf-8") as f:
    f.write(faq_schema_code)

# 4. Create app/crud/crud_faq.py
faq_crud_code = """from sqlalchemy.orm import Session
from sqlalchemy import asc
from app.models.faq import FaqCategory, FaqItem

def get_all_categories_with_faqs(db: Session):
    return db.query(FaqCategory).order_by(asc(FaqCategory.order)).all()

def create_category(db: Session, name: str, order: int = 0) -> FaqCategory:
    category = FaqCategory(name=name, order=order)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category

def create_item(db: Session, category_id, question: str, answer: str, action_phone: str = None, order: int = 0) -> FaqItem:
    item = FaqItem(
        category_id=category_id,
        question=question,
        answer=answer,
        action_phone=action_phone,
        order=order
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item
"""
with open(os.path.join(crud_dir, "crud_faq.py"), "w", encoding="utf-8") as f:
    f.write(faq_crud_code)

# 5. Create app/api/routes_faq.py
faq_routes_code = """from typing import List, Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.faq import FaqCategoryResponse
from app.crud import crud_faq
from app.models.faq import FaqCategory

router = APIRouter()

@router.get("/", response_model=List[FaqCategoryResponse])
def get_faqs(db: Session = Depends(get_db)) -> Any:
    \"\"\"
    Obtiene todas las categorías de FAQ y sus preguntas en orden.
    \"\"\"
    return crud_faq.get_all_categories_with_faqs(db)

@router.post("/seed")
def seed_faqs(db: Session = Depends(get_db)):
    \"\"\"
    Puebla la base de datos con los FAQs por defecto (Solo para desarrollo).
    \"\"\"
    existing = db.query(FaqCategory).first()
    if existing:
        return {"msg": "FAQs ya han sido poblados"}

    # Categoria 1
    c1 = crud_faq.create_category(db, "Emergencias y Primeros Pasos", order=1)
    crud_faq.create_item(db, c1.id, "¿A dónde llamo si estoy en peligro ahora mismo?", "<![CDATA[Llamá al <b>911</b> (Emergencias policiales). Es la única línea para intervención inmediata.]]>", action_phone="911", order=1)
    crud_faq.create_item(db, c1.id, "¿Dónde me comunico para recibir asesoramiento gratuito?", "<![CDATA[<b>Línea 144:</b> Atención telefónica y por WhatsApp las 24 hs, todo el año.<br/><br/><b>Línea 102:</b> Exclusiva para situaciones de violencia que involucran a niñas, niños y adolescentes.]]>", action_phone="144", order=2)

    # Categoria 2
    c2 = crud_faq.create_category(db, "Dónde Denunciar en Tucumán", order=2)
    crud_faq.create_item(db, c2.id, "¿Dónde puedo hacer una denuncia presencial?", "<![CDATA[<b>Oficina de Violencia Doméstica (OVD):</b> Pje. Vélez Sarsfield 450 (Capital). Atiende las 24 hs. (Cuenta con sedes en Banda del Río Salí, Concepción, Monteros y Trancas).<br/><br/><b>División de Violencia de Género (Policía):</b> Don Bosco 1886. Atiende las 24 hs.<br/><br/>Cualquier comisaría cercana está obligada a tomar la denuncia.]]>", action_phone=None, order=1)
    crud_faq.create_item(db, c2.id, "¿Qué necesito para denunciar?", "Es ideal llevar tu DNI, pero no es un requisito obligatorio para que te tomen la denuncia en una situación de emergencia.", action_phone=None, order=2)

    # Categoria 3
    c3 = crud_faq.create_category(db, "Asesoramiento y Contención", order=3)
    crud_faq.create_item(db, c3.id, "¿Dónde encuentro apoyo psicológico y legal local?", "<![CDATA[<b>Observatorio de la Mujer:</b> Av. Avellaneda 750 (Hospital Centro de Salud). Atiende de lunes a viernes, de 8 a 18 hs.<br/><br/><b>Centro de Atención y Orientación en Violencia Familiar:</b> Don Bosco 1886.]]>", action_phone=None, order=1)

    # Categoria 4
    c4 = crud_faq.create_category(db, "Identificación de la Violencia", order=4)
    crud_faq.create_item(db, c4.id, "¿Qué se considera violencia de género o familiar?", "Cualquier acción que afecte la integridad física, psicológica, económica o sexual. No hacen falta agresiones físicas para pedir ayuda; los insultos, el control del dinero y el aislamiento también son violencia.", action_phone=None, order=1)

    return {"msg": "FAQs poblados exitosamente"}
"""
with open(os.path.join(api_dir, "routes_faq.py"), "w", encoding="utf-8") as f:
    f.write(faq_routes_code)

# 6. Include router in api.py
api_py_path = os.path.join(api_dir, "api.py")
with open(api_py_path, "r", encoding="utf-8") as f:
    api_content = f.read()

if "routes_faq" not in api_content:
    api_content = api_content.replace(
        "    routes_centros, routes_guias, routes_chatbot, routes_rag",
        "    routes_centros, routes_guias, routes_chatbot, routes_rag, routes_faq"
    )
    api_content = api_content + """
api_router.include_router(
    routes_faq.router,
    prefix="/faqs",
    tags=["FAQs"]
)
"""
    with open(api_py_path, "w", encoding="utf-8") as f:
        f.write(api_content)

print("Backend for FAQ successfully configured.")
