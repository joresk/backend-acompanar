from sqlalchemy import Column, String
from app.db.base_class import Base

class EstadoPeticion(Base):
    """
    Modelo para los estados de las peticiones de emergencia
    Tabla: estados_peticiones
    """
    __tablename__ = "estados_peticiones"
    
    code = Column(String(20), primary_key=True)
    descripcion = Column(String(100), nullable=False)
    
    def __repr__(self):
        return f"<EstadoPeticion {self.code}: {self.descripcion}>"
    
    @classmethod
    def get_default_estados(cls):
        """Retorna los estados por defecto del sistema"""
        return [
            ('pendiente', 'En espera de ser atendida'),
            ('atendida', 'Petición atendida'),
            ('en_proceso', 'La petición está siendo atendida por un centro de ayuda'),
            ('cancelada', 'Petición cancelada'),
            ('resuelta', 'La petición fue resuelta satisfactoriamente'),
            ('rechazada', 'La petición fue rechazada por falta de información'),
            ('error', 'Error al procesar la petición')
        ]