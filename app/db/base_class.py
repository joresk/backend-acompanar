from typing import Any
from sqlalchemy.orm import as_declarative, declared_attr

@as_declarative()
class Base:
    """Clase base declarativa para los modelos de SQLAlchemy."""
    id: Any
    __name__: str
    
    # Generar __tablename__ automáticamente a partir del nombre de la clase
    @declared_attr
    def __tablename__(cls) -> str:
        return cls.__name__.lower()