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

def update_category(db: Session, category_id: str, obj_in: dict) -> FaqCategory:
    category = db.query(FaqCategory).filter(FaqCategory.id == category_id).first()
    if category:
        for field, value in obj_in.items():
            setattr(category, field, value)
        db.commit()
        db.refresh(category)
    return category

def delete_category(db: Session, category_id: str) -> bool:
    category = db.query(FaqCategory).filter(FaqCategory.id == category_id).first()
    if category:
        db.delete(category)
        db.commit()
        return True
    return False

def update_item(db: Session, item_id: str, obj_in: dict) -> FaqItem:
    item = db.query(FaqItem).filter(FaqItem.id == item_id).first()
    if item:
        for field, value in obj_in.items():
            setattr(item, field, value)
        db.commit()
        db.refresh(item)
    return item

def delete_item(db: Session, item_id: str) -> bool:
    item = db.query(FaqItem).filter(FaqItem.id == item_id).first()
    if item:
        db.delete(item)
        db.commit()
        return True
    return False
