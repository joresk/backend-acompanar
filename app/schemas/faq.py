from pydantic import BaseModel, UUID4
from typing import List, Optional

class FaqItemBase(BaseModel):
    question: str
    answer: str
    action_phone: Optional[str] = None
    order: int = 0

class FaqItemCreate(FaqItemBase):
    pass

class FaqItemUpdate(BaseModel):
    question: Optional[str] = None
    answer: Optional[str] = None
    action_phone: Optional[str] = None
    order: Optional[int] = None

class FaqItemResponse(FaqItemBase):
    id: UUID4
    category_id: UUID4

    class Config:
        from_attributes = True

class FaqCategoryBase(BaseModel):
    name: str
    order: int = 0

class FaqCategoryCreate(FaqCategoryBase):
    pass

class FaqCategoryUpdate(BaseModel):
    name: Optional[str] = None
    order: Optional[int] = None

class FaqCategoryResponse(FaqCategoryBase):
    id: UUID4
    faqs: List[FaqItemResponse] = []

    class Config:
        from_attributes = True
