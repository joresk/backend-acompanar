import cloudinary
import cloudinary.uploader
from app.core.config import settings
import uuid

# Configuración inicial
if settings.CLOUDINARY_CLOUD_NAME:
    cloudinary.config(
        cloud_name=settings.CLOUDINARY_CLOUD_NAME,
        api_key=settings.CLOUDINARY_API_KEY,
        api_secret=settings.CLOUDINARY_API_SECRET,
        secure=True
    )

class StorageService:
    @staticmethod
    def upload_base64_audio(base64_string: str) -> str:
        """
        Sube un audio en Base64 a Cloudinary y retorna la URL segura.
        Retorna None si falla o si el input es vacío.
        """
        if not base64_string:
            return None
            
        try:
            # Generar un nombre único para el archivo
            file_id = f"alert_audio_{uuid.uuid4()}"
            
            # Preparar el string Base64 si no tiene el prefijo data URI
            # Cloudinary maneja bien los raw base64 si le indicamos el recurso
            upload_data = base64_string
            if not base64_string.startswith("data:"):
                # Asumimos formato m4a/mp4 que viene de Android
                upload_data = f"data:audio/mp4;base64,{base64_string}"

            # Subir a Cloudinary (resource_type="video" se usa para audios también)
            response = cloudinary.uploader.upload(
                upload_data, 
                public_id=file_id,
                resource_type="video", 
                folder="acompanar_alertas"
            )
            
            # Retornar la URL pública (https)
            return response.get("secure_url")
            
        except Exception as e:
            print(f"Error subiendo audio a Cloudinary: {str(e)}")
            return None # Fallback: guardará None en la BD en vez de explotar

storage_service = StorageService()