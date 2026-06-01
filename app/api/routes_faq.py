from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.faq import FaqCategoryResponse, FaqCategoryCreate, FaqCategoryUpdate, FaqItemResponse, FaqItemCreate, FaqItemUpdate
from app.crud import crud_faq
from app.models.faq import FaqCategory, FaqItem

router = APIRouter()

@router.get("/", response_model=List[FaqCategoryResponse])
def get_faqs(db: Session = Depends(get_db)) -> Any:
    """Obtiene todas las categorías de FAQ y sus preguntas en orden."""
    return crud_faq.get_all_categories_with_faqs(db)

@router.post("/", response_model=FaqCategoryResponse)
def create_category(cat_in: FaqCategoryCreate, db: Session = Depends(get_db)) -> Any:
    return crud_faq.create_category(db, name=cat_in.name, order=cat_in.order)

@router.put("/{category_id}", response_model=FaqCategoryResponse)
def update_category(category_id: str, cat_in: FaqCategoryUpdate, db: Session = Depends(get_db)) -> Any:
    cat = crud_faq.update_category(db, category_id, cat_in.dict(exclude_unset=True))
    if not cat: raise HTTPException(status_code=404, detail="Categoría no encontrada")
    return cat

@router.delete("/{category_id}")
def delete_category(category_id: str, db: Session = Depends(get_db)) -> Any:
    success = crud_faq.delete_category(db, category_id)
    if not success: raise HTTPException(status_code=404, detail="Categoría no encontrada")
    return {"msg": "Categoría eliminada"}

@router.post("/{category_id}/items", response_model=FaqItemResponse)
def create_item(category_id: str, item_in: FaqItemCreate, db: Session = Depends(get_db)) -> Any:
    return crud_faq.create_item(db, category_id, item_in.question, item_in.answer, item_in.action_phone, item_in.order)

@router.put("/items/{item_id}", response_model=FaqItemResponse)
def update_item(item_id: str, item_in: FaqItemUpdate, db: Session = Depends(get_db)) -> Any:
    item = crud_faq.update_item(db, item_id, item_in.dict(exclude_unset=True))
    if not item: raise HTTPException(status_code=404, detail="Pregunta no encontrada")
    return item

@router.delete("/items/{item_id}")
def delete_item(item_id: str, db: Session = Depends(get_db)) -> Any:
    success = crud_faq.delete_item(db, item_id)
    if not success: raise HTTPException(status_code=404, detail="Pregunta no encontrada")
    return {"msg": "Pregunta eliminada"}

@router.post("/seed")
def seed_faqs(db: Session = Depends(get_db)):
    """Puebla la base de datos con los FAQs por defecto (Solo para desarrollo)."""
    existing = db.query(FaqCategory).first()
    if existing: return {"msg": "FAQs ya han sido poblados"}
    c1 = crud_faq.create_category(db, "Emergencias y Primeros Pasos", order=1)
    crud_faq.create_item(db, c1.id, "¿A dónde llamo si estoy en peligro ahora mismo?", "Llamá al <b>911</b> (Emergencias policiales). Es la única línea para intervención inmediata.", action_phone="911", order=1)
    crud_faq.create_item(db, c1.id, "¿Dónde me comunico para recibir asesoramiento gratuito?", "<b>Línea 144:</b> Atención telefónica y por WhatsApp las 24 hs, todo el año.<br/><br/><b>Línea 102:</b> Exclusiva para situaciones de violencia que involucran a niñas, niños y adolescentes.", action_phone="144", order=2)
    c2 = crud_faq.create_category(db, "Dónde Denunciar en Tucumán", order=2)
    crud_faq.create_item(db, c2.id, "¿Dónde puedo hacer una denuncia presencial?", "<b>Oficina de Violencia Doméstica (OVD):</b> Pje. Vélez Sarsfield 450 (Capital). Atiende las 24 hs. (Cuenta con sedes en Banda del Río Salí, Concepción, Monteros y Trancas).<br/><br/><b>División de Violencia de Género (Policía):</b> Don Bosco 1886. Atiende las 24 hs.<br/><br/>Cualquier comisaría cercana está obligada a tomar la denuncia.", action_phone=None, order=1)
    crud_faq.create_item(db, c2.id, "¿Qué necesito para denunciar?", "Es ideal llevar tu DNI, pero no es un requisito obligatorio para que te tomen la denuncia en una situación de emergencia.", action_phone=None, order=2)
    c3 = crud_faq.create_category(db, "Asesoramiento y Contención", order=3)
    crud_faq.create_item(db, c3.id, "¿Dónde encuentro apoyo psicológico y legal local?", "<b>Observatorio de la Mujer:</b> Av. Avellaneda 750 (Hospital Centro de Salud). Atiende de lunes a viernes, de 8 a 18 hs.<br/><br/><b>Centro de Atención y Orientación en Violencia Familiar:</b> Don Bosco 1886.", action_phone=None, order=1)
    c4 = crud_faq.create_category(db, "Identificación de la Violencia", order=4)
    crud_faq.create_item(db, c4.id, "¿Qué se considera violencia de género o familiar?", "Cualquier acción que afecte la integridad física, psicológica, económica o sexual. No hacen falta agresiones físicas para pedir ayuda; los insultos, el control del dinero y el aislamiento también son violencia.", action_phone=None, order=1)
    return {"msg": "FAQs poblados exitosamente"}
