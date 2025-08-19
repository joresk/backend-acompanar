from datetime import datetime, timedelta
from typing import Dict
import threading

class RateLimiter:
    """
    Rate limiter simple en memoria.
    En producción, usar Redis para persistencia y escalabilidad.
    """
    
    def __init__(self, max_requests: int = 1, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, list] = {}
        self.lock = threading.Lock()
    
    def is_allowed(self, key: str) -> bool:
        """
        Verificar si una solicitud está permitida para la clave dada.
        
        Args:
            key: Identificador único (e.g., user_id)
        
        Returns:
            True si la solicitud está permitida, False si excede el límite
        """
        with self.lock:
            now = datetime.utcnow()
            window_start = now - timedelta(seconds=self.window_seconds)
            
            # Obtener o crear lista de requests para esta clave
            if key not in self.requests:
                self.requests[key] = []
            
            # Filtrar requests fuera de la ventana de tiempo
            self.requests[key] = [
                req_time for req_time in self.requests[key]
                if req_time > window_start
            ]
            
            # Verificar si excede el límite
            if len(self.requests[key]) >= self.max_requests:
                return False
            
            # Agregar nueva request
            self.requests[key].append(now)
            return True
    
    def reset(self, key: str):
        """Resetear el contador para una clave específica"""
        with self.lock:
            if key in self.requests:
                del self.requests[key]
    
    def get_wait_time(self, key: str) -> int:
        """
        Obtener segundos de espera hasta poder hacer otra request.
        
        Returns:
            Segundos de espera, 0 si puede hacer request ahora
        """
        with self.lock:
            if key not in self.requests or not self.requests[key]:
                return 0
            
            oldest_request = min(self.requests[key])
            next_allowed = oldest_request + timedelta(seconds=self.window_seconds)
            wait_time = (next_allowed - datetime.utcnow()).total_seconds()
            
            return max(0, int(wait_time))