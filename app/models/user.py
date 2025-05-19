from sqlalchemy import Column, Integer, String, Boolean
from app.db.base import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=True)
    full_name = Column(String)
    hashed_password = Column(String, nullable=True)    
    is_active = Column(Boolean, default=True)
    is_anonymous = Column(Boolean, default=False)

