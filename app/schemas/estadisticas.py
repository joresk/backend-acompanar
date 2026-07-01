from pydantic import BaseModel, UUID4

class TopFaqResponse(BaseModel):
    faq_item_id: UUID4
    pregunta: str
    total_consultas: int

    class Config:
        orm_mode = True

class TopCentroResponse(BaseModel):
    centro_id: UUID4
    nombre: str
    total_consultas: int

    class Config:
        orm_mode = True
