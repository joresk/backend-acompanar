from sqlalchemy import Column, DateTime, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base

class ConsultaFaq(Base):
    __tablename__ = "consultas_faq"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))
    usuario_id = Column(UUID(as_uuid=True), ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=True)
    faq_item_id = Column(UUID(as_uuid=True), ForeignKey("faq_items.id", ondelete="CASCADE"), nullable=False)
    consultado_en = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"), nullable=False)
    
    # Relaciones
    usuario = relationship("User")
    faq = relationship("FaqItem")
