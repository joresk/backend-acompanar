from sqlalchemy import Column, String, ForeignKey, Text, Integer
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
