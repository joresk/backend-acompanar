from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from app.models.consulta_faq import ConsultaFaq
from app.models.faq import FaqItem
from app.models.centro import ConsultaCentro, Centro

def get_top_faqs(db: Session, limit: int = 5):
    """
    Obtiene las guías (FAQs) más consultadas.
    Retorna una lista de diccionarios con faq_item_id, pregunta y total_consultas.
    """
    resultados = db.query(
        ConsultaFaq.faq_item_id,
        FaqItem.question.label("pregunta"),
        func.count(ConsultaFaq.id).label("total_consultas")
    ).join(
        FaqItem, ConsultaFaq.faq_item_id == FaqItem.id
    ).group_by(
        ConsultaFaq.faq_item_id, FaqItem.question
    ).order_by(
        desc("total_consultas")
    ).limit(limit).all()
    
    # Devolver como lista de diccionarios para que pydantic lo serialice bien
    return [{"faq_item_id": r.faq_item_id, "pregunta": r.pregunta, "total_consultas": r.total_consultas} for r in resultados]


def get_top_centros(db: Session, limit: int = 5):
    """
    Obtiene los centros más consultados.
    Retorna una lista de diccionarios con centro_id, nombre y total_consultas.
    """
    resultados = db.query(
        ConsultaCentro.centro_id,
        Centro.nombre.label("nombre"),
        func.count(ConsultaCentro.id).label("total_consultas")
    ).join(
        Centro, ConsultaCentro.centro_id == Centro.id
    ).group_by(
        ConsultaCentro.centro_id, Centro.nombre
    ).order_by(
        desc("total_consultas")
    ).limit(limit).all()
    
    # Devolver como lista de diccionarios
    return [{"centro_id": r.centro_id, "nombre": r.nombre, "total_consultas": r.total_consultas} for r in resultados]
