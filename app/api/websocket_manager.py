from typing import List
from fastapi import WebSocket
import json
import logging

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Nuevo cliente WS conectado. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"Cliente WS desconectado. Total: {len(self.active_connections)}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error enviando mensaje WS: {e}")

    async def broadcast_alerts_update(self):
        """Notificar a todos los clientes que deben refrescar sus alertas"""
        message = json.dumps({
            "type": "alerts_update",
            "message": "Nuevas alertas o cambio de estado."
        })
        await self.broadcast(message)

    async def broadcast_professionals_update(self):
        """Notificar a todos los clientes que la ubicación de los móviles ha cambiado"""
        message = json.dumps({
            "type": "professionals_update",
            "message": "Actualización de ubicación de unidades."
        })
        await self.broadcast(message)

manager = ConnectionManager()
