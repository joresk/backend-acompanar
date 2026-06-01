from sqlalchemy.orm import Session
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
