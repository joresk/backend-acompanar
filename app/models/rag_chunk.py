from sqlalchemy import Column, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base

class RagChunk(Base):
    __tablename__ = "rag_chunks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))
    content = Column(Text, nullable=False)
    source = Column(String(255), nullable=True)
