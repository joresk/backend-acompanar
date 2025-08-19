from typing import List, Dict, Optional
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
import os
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class SMSService:
    def __init__(self):
        # Configuración de Twilio desde variables de entorno
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.from_number = os.getenv("TWILIO_PHONE_NUMBER")
        
        # Inicializar cliente si hay credenciales
        self.client = None
        if self.account_sid and self.auth_token:
            try:
                self.client = Client(self.account_sid, self.auth_token)
                logger.info("Servicio SMS Twilio inicializado correctamente")
            except Exception as e:
                logger.error(f"Error inicializando Twilio: {e}")
        else:
            logger.warning("Credenciales de Twilio no configuradas - SMS deshabilitado")
    
    def send_emergency_sms(
        self,
        contacts: List[Dict],
        user_name: str,
        location: Optional[Dict] = None,
        custom_message: Optional[str] = None
    ) -> Dict:
        """
        Enviar SMS de emergencia a lista de contactos
        
        Args:
            contacts: Lista con 'nombre' y 'telefono'
            user_name: Nombre del usuario que envía la alerta
            location: Dict con 'latitude', 'longitude', 'address'
            custom_message: Mensaje personalizado opcional
        
        Returns:
            Dict con resultados del envío
        """
        if not self.client:
            logger.warning("Intentando enviar SMS sin servicio configurado")
            return {
                "success": False,
                "message": "Servicio SMS no configurado",
                "sent": 0,
                "failed": len(contacts),
                "details": []
            }
        
        # Construir mensaje
        message = self._build_emergency_message(user_name, location, custom_message)
        
        results = {
            "success": True,
            "sent": 0,
            "failed": 0,
            "details": [],
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Enviar a cada contacto
        for contact in contacts:
            try:
                # Formatear número para Argentina
                phone = self._format_phone_number(contact['telefono'])
                
                result = self._send_single_sms(
                    to_number=phone,
                    message=message,
                    contact_name=contact['nombre']
                )
                
                if result['success']:
                    results['sent'] += 1
                    logger.info(f"SMS enviado exitosamente a {contact['nombre']}")
                else:
                    results['failed'] += 1
                    logger.error(f"Fallo envío SMS a {contact['nombre']}: {result.get('error')}")
                
                results['details'].append(result)
                
            except Exception as e:
                logger.error(f"Error enviando SMS a {contact['nombre']}: {str(e)}")
                results['failed'] += 1
                results['details'].append({
                    "contact": contact['nombre'],
                    "success": False,
                    "error": str(e)
                })
        
        results['success'] = results['failed'] == 0
        return results
    
    def _format_phone_number(self, phone: str) -> str:
        """
        Formatear número de teléfono para Argentina
        Asegurar formato internacional +54
        """
        # Limpiar caracteres no numéricos excepto +
        phone = ''.join(c for c in phone if c.isdigit() or c == '+')
        
        # Si ya tiene formato internacional, retornar
        if phone.startswith('+'):
            return phone
        
        # Si empieza con 54, agregar +
        if phone.startswith('54'):
            return '+' + phone
        
        # Si es número local de Tucumán (381...)
        if phone.startswith('381'):
            return '+54' + phone
        
        # Si empieza con 0, quitarlo
        if phone.startswith('0'):
            phone = phone[1:]
        
        # Por defecto, asumir Argentina
        if not phone.startswith('+'):
            phone = '+54' + phone
        
        return phone
    
    def _send_single_sms(
        self, 
        to_number: str, 
        message: str,
        contact_name: str
    ) -> Dict:
        """Enviar un SMS individual"""
        try:
            # Enviar mensaje
            message_instance = self.client.messages.create(
                body=message,
                from_=self.from_number,
                to=to_number
            )
            
            return {
                "contact": contact_name,
                "phone": to_number,
                "success": True,
                "sid": message_instance.sid,
                "status": message_instance.status
            }
            
        except TwilioRestException as e:
            error_msg = str(e)
            if e.code == 21211:  # Número inválido
                error_msg = "Número de teléfono inválido"
            elif e.code == 21608:  # Número no verificado en trial
                error_msg = "Número no verificado en cuenta trial de Twilio"
            
            return {
                "contact": contact_name,
                "phone": to_number,
                "success": False,
                "error": error_msg,
                "code": e.code if hasattr(e, 'code') else None
            }
    
    def _build_emergency_message(
        self,
        user_name: str,
        location: Optional[Dict] = None,
        custom_message: Optional[str] = None
    ) -> str:
        """Construir mensaje de emergencia"""
        
        # Mensaje base
        message = f"🚨 ALERTA DE EMERGENCIA 🚨\n"
        message += f"{user_name} necesita ayuda URGENTE.\n"
        
        # Agregar mensaje personalizado si existe
        if custom_message:
            message += f"\n{custom_message}\n"
        
        # Agregar ubicación si está disponible
        if location:
            message += "\n📍 UBICACIÓN:\n"
            
            if location.get('address'):
                message += f"{location['address']}\n"
            
            if location.get('latitude') and location.get('longitude'):
                lat = location['latitude']
                lon = location['longitude']
                google_maps_url = f"https://maps.google.com/?q={lat},{lon}"
                message += f"Ver en mapa: {google_maps_url}\n"
        
        message += f"\n⏰ {datetime.now().strftime('%d/%m %H:%M')}hs"
        message += "\n\nApp Acompañar - Tucumán"
        
        # Limitar a 160 caracteres si es muy largo
        if len(message) > 320:  # Permitir 2 SMS concatenados
            message = message[:317] + "..."
        
        return message
    
    def send_test_sms(self, phone_number: str) -> Dict:
        """Enviar SMS de prueba para verificar configuración"""
        if not self.client:
            return {
                "success": False,
                "message": "Servicio SMS no configurado"
            }
        
        phone = self._format_phone_number(phone_number)
        
        test_message = (
            "📱 SMS de Prueba - App Acompañar\n"
            "Este mensaje confirma que los SMS de emergencia "
            "funcionan correctamente.\n"
            f"Hora: {datetime.now().strftime('%H:%M')}hs"
        )
        
        return self._send_single_sms(
            to_number=phone,
            message=test_message,
            contact_name="Test"
        )
    
    def validate_phone_number(self, phone_number: str) -> Dict:
        """Validar si un número de teléfono es válido usando Twilio Lookup"""
        if not self.client:
            # Sin servicio, asumir válido si cumple formato básico
            phone = self._format_phone_number(phone_number)
            is_valid = len(phone) >= 10 and len(phone) <= 15
            return {
                "valid": is_valid,
                "formatted": phone if is_valid else None,
                "message": "Formato válido" if is_valid else "Formato inválido"
            }
        
        try:
            phone = self._format_phone_number(phone_number)
            
            # Usar Twilio Lookup API
            phone_info = self.client.lookups.v2.phone_numbers(phone).fetch()
            
            return {
                "valid": phone_info.valid,
                "formatted": phone_info.phone_number,
                "country_code": phone_info.country_code,
                "carrier": phone_info.carrier.get('name') if phone_info.carrier else None
            }
        except Exception as e:
            logger.error(f"Error validando número: {e}")
            return {
                "valid": False,
                "error": str(e)
            }

# Instancia singleton del servicio
sms_service = SMSService()